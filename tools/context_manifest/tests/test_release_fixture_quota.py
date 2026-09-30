"""RV-28 quota race: the regression input (v4_release/file_upload_authenticated_safe.py) exceeds its per-user quota
under a forced interleaving; the replacement (v4_release/file_upload_authenticated_quota_atomic_safe.py) does not,
across threads and across processes, and releases its slot when writing fails.

The fixtures import Flask, which is not a dependency of this kit, so a minimal stand-in `flask` module (thread-local
request and session, `abort` raising an exception, a no-op `route`) is installed for the fixture's own code to run
against. Interleavings are forced with barriers, never with sleeps; barrier timeouts only stop a hung test.
"""

from __future__ import annotations

import importlib.util
import multiprocessing
import os
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FIX = os.path.join(REPO, "tests", "fixtures", "v4_release")
VULNERABLE = os.path.join(FIX, "file_upload_authenticated_safe.py")
ATOMIC = os.path.join(FIX, "file_upload_authenticated_quota_atomic_safe.py")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
HANG_GUARD_S = 60


class Aborted(Exception):
    def __init__(self, code, message=None):
        super().__init__(code, message)
        self.code = code


_local = threading.local()


class _Request:
    @property
    def files(self):
        return _local.files


class _Session:
    def get(self, key, default=None):
        return _local.session.get(key, default)

    def __getitem__(self, key):
        return _local.session[key]


def install_flask_stub():
    if isinstance(sys.modules.get("flask"), types.ModuleType) and getattr(sys.modules["flask"], "_is_stub", False):
        return
    flask = types.ModuleType("flask")
    flask._is_stub = True

    class Flask:
        def __init__(self, name):
            self.config = {}

        def route(self, *args, **kwargs):
            return lambda view: view

    def abort(code, message=None):
        raise Aborted(code, message)

    flask.Flask, flask.abort, flask.request, flask.session = Flask, abort, _Request(), _Session()
    sys.modules["flask"] = flask


def load_fixture(path, root, max_files):
    install_flask_stub()
    with mock.patch.dict(os.environ, {"UPLOAD_APP_SECRET_KEY": "k" * 32}):
        name = f"_fixture_{os.path.basename(path)[:-3]}_{id(root)}"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    module.UPLOAD_ROOT = root
    module.MAX_FILES_PER_USER = max_files
    return module


class _Upload:
    def read(self):
        return PNG


def call_upload(module, user_id=7):
    _local.files = {"file": _Upload()}
    _local.session = {"user_id": user_id}
    try:
        return module.upload()
    except Aborted as exc:
        return exc.code


def stored_files(user_dir):
    return sorted(f for f in os.listdir(user_dir) if not f.startswith("."))


class _OsWithBarrier:
    """The `os` module, except that one function waits on a barrier (first call per thread only)."""

    def __init__(self, name, barrier):
        self._name, self._barrier, self._seen = name, barrier, threading.local()

    def __getattr__(self, attr):
        real = getattr(os, attr)
        if attr != self._name:
            return real

        def wrapped(*args, **kwargs):
            if not getattr(self._seen, "done", False):
                self._seen.done = True
                if attr == "listdir":            # check first, then wait: every request has passed the count
                    result = real(*args, **kwargs)
                    self._barrier.wait()
                    return result
                self._barrier.wait()             # wait first, then act: every request reserves at the same time
            return real(*args, **kwargs)
        return wrapped


def run_concurrently(module, n):
    results = [None] * n

    def worker(i):
        results[i] = call_upload(module)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(HANG_GUARD_S)
        if t.is_alive():
            raise AssertionError("a worker hung")
    return results


def _process_worker(path, root, max_files, barrier, queue):
    module = load_fixture(path, root, max_files)
    user_dir = os.path.join(root, "7")
    os.makedirs(user_dir, exist_ok=True)
    barrier.wait(HANG_GUARD_S)
    try:
        queue.put(("ok", module.store_upload(user_dir, PNG, "png")))
    except BaseException as exc:  # noqa: BLE001
        queue.put(("error", repr(exc)))


class QuotaRaceTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)
        self.user_dir = os.path.join(self.root, "7")

    def _cleanup(self):
        for dirpath, dirs, files in os.walk(self.root, topdown=False):
            for f in files:
                os.unlink(os.path.join(dirpath, f))
            for d in dirs:
                os.rmdir(os.path.join(dirpath, d))
        os.rmdir(self.root)

    def test_the_regression_input_exceeds_its_quota_when_requests_interleave(self):
        old = load_fixture(VULNERABLE, self.root, max_files=1)
        n = 4
        old.os = _OsWithBarrier("listdir", threading.Barrier(n, timeout=HANG_GUARD_S))
        results = run_concurrently(old, n)
        self.assertEqual([r["status"] for r in results], ["uploaded"] * n)
        self.assertEqual(len(stored_files(self.user_dir)), n)          # 4 files under a quota of 1

    def test_the_regression_input_holds_its_quota_sequentially(self):
        old = load_fixture(VULNERABLE, self.root, max_files=2)
        results = [call_upload(old) for _ in range(4)]
        self.assertEqual([r if isinstance(r, int) else "ok" for r in results], ["ok", "ok", 429, 429])

    def test_the_atomic_version_holds_its_quota_when_requests_interleave(self):
        for max_files, n in ((1, 4), (3, 8)):
            with self.subTest(max_files=max_files, n=n):
                self._cleanup()
                os.mkdir(self.root)
                new = load_fixture(ATOMIC, self.root, max_files=max_files)
                new.os = _OsWithBarrier("open", threading.Barrier(n, timeout=HANG_GUARD_S))
                results = run_concurrently(new, n)
                self.assertEqual(sum(1 for r in results if isinstance(r, dict)), max_files)
                self.assertEqual(sum(1 for r in results if r == 429), n - max_files)
                self.assertEqual(len(stored_files(self.user_dir)), max_files)
                self.assertEqual(len(os.listdir(os.path.join(self.user_dir, ".slots"))), max_files)

    def test_the_atomic_version_holds_its_quota_across_processes(self):
        ctx = multiprocessing.get_context("spawn")
        n, max_files = 6, 2
        barrier, queue = ctx.Barrier(n), ctx.Queue()
        procs = [ctx.Process(target=_process_worker, args=(ATOMIC, self.root, max_files, barrier, queue)) for _ in range(n)]
        for p in procs:
            p.start()
        outcomes = [queue.get(timeout=HANG_GUARD_S) for _ in range(n)]
        for p in procs:
            p.join(HANG_GUARD_S)
        self.assertEqual([o[0] for o in outcomes], ["ok"] * n, outcomes)
        self.assertEqual(sum(1 for o in outcomes if o[1] is not None), max_files)
        self.assertEqual(len(stored_files(self.user_dir)), max_files)

    def test_a_failed_write_releases_the_slot_and_removes_only_its_own_file(self):
        new = load_fixture(ATOMIC, self.root, max_files=1)
        os.makedirs(self.user_dir)

        class Broken:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def write(self, data):
                raise OSError("disk full")

        real_open = open

        def opener(path, mode="r", *a, **k):
            if mode == "xb":
                real_open(path, mode).close()     # the file is created, then the write fails
                return Broken()
            return real_open(path, mode, *a, **k)

        with mock.patch.object(new, "open", opener, create=True):
            with self.assertRaises(OSError):
                new.store_upload(self.user_dir, PNG, "png")
        self.assertEqual(stored_files(self.user_dir), [])
        self.assertEqual(os.listdir(os.path.join(self.user_dir, ".slots")), [])
        self.assertIsNotNone(new.store_upload(self.user_dir, PNG, "png"))   # the released slot is usable again

    def test_a_name_collision_keeps_the_existing_file_and_releases_the_slot(self):
        new = load_fixture(ATOMIC, self.root, max_files=2)
        os.makedirs(self.user_dir)
        fixed = types.SimpleNamespace(hex="0" * 32)
        existing = os.path.join(self.user_dir, "0" * 32 + ".png")
        with open(existing, "wb") as fh:
            fh.write(b"someone else's file")
        with mock.patch.object(new.uuid, "uuid4", return_value=fixed):
            with self.assertRaises(FileExistsError):
                new.store_upload(self.user_dir, PNG, "png")
        with open(existing, "rb") as fh:
            self.assertEqual(fh.read(), b"someone else's file")
        self.assertEqual(os.listdir(os.path.join(self.user_dir, ".slots")), [])

    def test_the_view_goes_through_the_reservation(self):
        with open(ATOMIC, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("os.O_CREAT | os.O_EXCL", src)
        self.assertNotIn("os.listdir", src)
        self.assertIn("generated_name = store_upload(user_dir, data, ext)", src)
        with open(VULNERABLE, encoding="utf-8") as fh:
            self.assertIn("if len(os.listdir(user_dir)) >= MAX_FILES_PER_USER:", fh.read())


if __name__ == "__main__":
    unittest.main()
