"""V4 release: regression tests for the four evidence-store defects that
were deferred during development and fixed before release.

1. Stale-lock double acquisition (store._break_stale_lock).
2. hop_key delimiter collision (eligibility.hop_key).
3. One record id in both collections (store._validate_all_records).
4. Unicode format characters in paths (paths.normalize).

Each test fails against the pre-release code; the lock and hop tests
reproduce the fail-open interleaving / collision deterministically.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
import unittest.mock

from .. import eligibility, invalidation, paths, schema, store


def _record(record_id="r1", path="a/Repository.cs"):
    return schema.new_rejection_record(
        record_id=record_id,
        category="BOLA/IDOR",
        suspicion_pattern="p",
        safety_pattern="s",
        reachability_path=[{"path": path, "qualifiedSymbol": "Repository.FindById"}],
        rejection_reason="reason",
        evidence={"path": path, "observation": "o"},
        scope="scope",
        trace_confidence="HIGH",
        last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
    )


def _miss(record_id="m1"):
    return schema.new_miss_record(
        record_id=record_id,
        layer="routing",
        observed_miss="SQL injection via a new endpoint",
        expected_finding="CONFIRMED HIGH SQL injection",
        prior_layers_passed=[],
        evidence={"path": "a/Controller.cs", "observation": "endpoint never routed to code-review domain"},
        remediation="fix classification table for this endpoint shape",
        scope="this endpoint shape only",
        human_confirmed_by="example-reviewer",
        created_at="2026-09-23T00:00:00Z",
    )


def _make_stale(lock_path):
    with open(lock_path, "w", encoding="utf-8") as fh:
        fh.write("dead-writer")
    old = time.time() - (store.LOCK_STALE_SECONDS + 5)
    os.utime(lock_path, (old, old))


class StaleLockDoubleAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "feedback.json")
        self.lock = store._lock_path_for(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_second_waiter_does_not_delete_a_lock_reacquired_after_its_stale_observation(self):
        """Waiter B stats the stale lock; before B acts, waiter A breaks it and
        acquires a fresh lock. B must leave A's lock alone and time out. The
        pre-release code removed A's fresh lock and acquired as well."""
        _make_stale(self.lock)
        real_getmtime = os.path.getmtime
        calls = {"n": 0}

        def _getmtime(p):
            calls["n"] += 1
            if p == self.lock and calls["n"] == 1:
                stale_value = real_getmtime(p)        # B's observation: stale
                os.remove(p)                          # A breaks the stale lock ...
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write("owner-A")               # ... and acquires a fresh one
                return stale_value
            return real_getmtime(p)

        with unittest.mock.patch("os.path.getmtime", side_effect=_getmtime):
            with self.assertRaises(store.LockTimeoutError):
                store._acquire_lock(self.path, timeout=0.3)
        with open(self.lock, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "owner-A")
        self.assertFalse(os.path.exists(store._breaker_path_for(self.lock)))

    def test_leftover_breaker_marker_fails_closed_with_a_manual_removal_message(self):
        _make_stale(self.lock)
        open(store._breaker_path_for(self.lock), "w").close()   # left by a crashed breaker
        started = time.monotonic()
        with self.assertRaises(store.LockTimeoutError) as ctx:
            store._acquire_lock(self.path, timeout=0.3)
        self.assertLess(time.monotonic() - started, 3.0)
        self.assertIn("could not be removed", str(ctx.exception))
        self.assertIn(".break", str(ctx.exception))
        self.assertTrue(os.path.exists(self.lock), "the stale lock must not be removed while the marker is held")

    def test_stale_lock_alone_is_still_removed_and_the_marker_cleaned_up(self):
        _make_stale(self.lock)
        got = store._acquire_lock(self.path, timeout=2.0)
        self.assertEqual(got, self.lock)
        self.assertFalse(os.path.exists(store._breaker_path_for(self.lock)))
        store._release_lock(got)

    def test_concurrent_writers_starting_from_a_stale_lock_lose_no_record(self):
        repo = self._tmp.name
        path = os.path.join(repo, ".security", "feedback.json")
        store.write(path, store.empty_store(), repo_root=repo, expected_on_disk_hash=None, git_commit=None)
        _make_stale(store._lock_path_for(path))
        ids = [f"w{i}" for i in range(6)]
        barrier = threading.Barrier(len(ids))
        errors = []

        def _writer(rid):
            barrier.wait()
            for _ in range(200):
                loaded = store.load(path, repo_root=repo)
                s = loaded.store
                store.append_rejection_record(s, _record(rid))
                try:
                    store.write(path, s, repo_root=repo, expected_on_disk_hash=loaded.on_disk_hash, git_commit=None)
                    return
                except (store.ConcurrentModificationError, store.LockTimeoutError):
                    time.sleep(0.01)
            errors.append(rid)

        threads = [threading.Thread(target=_writer, args=(rid,)) for rid in ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        final = store.load(path, repo_root=repo)
        self.assertTrue(final.ok)
        self.assertEqual(sorted(final.store["rejectionRecords"]), sorted(ids))


class HopKeyCollisionTests(unittest.TestCase):
    def test_colon_in_path_and_symbol_no_longer_collide(self):
        self.assertNotEqual(eligibility.hop_key("src/a::b", "c.d"), eligibility.hop_key("src/a", "b::c.d"))

    def test_confirming_one_hop_does_not_satisfy_check_d_for_the_other(self):
        confirmed = {eligibility.hop_key("src/a", "b::c.d"): True}
        reason = eligibility._check_d_hop_controls([{"path": "src/a::b", "qualifiedSymbol": "c.d"}], confirmed)
        self.assertEqual(reason, eligibility.REASON_HOP_CONTROL_NOT_CONFIRMED)
        self.assertIsNone(eligibility._check_d_hop_controls([{"path": "src/a", "qualifiedSymbol": "b::c.d"}], confirmed))

    def test_case_and_normalization_forms_still_share_a_key(self):
        self.assertEqual(eligibility.hop_key("Src/R.cs", "N.R.Get(int)"), eligibility.hop_key("src/r.cs", "N.R.Get(int)"))
        self.assertEqual(eligibility.hop_key("src/caf\u00e9.cs", "x.y"), eligibility.hop_key("src/cafe\u0301.cs", "x.y"))

    def test_quotes_pipes_and_backslashes_do_not_collide(self):
        pairs = [('a"b', 'c.d'), ('a', '"b".c'), ('a|b', 'c.d'), ('a', 'b|c.d'), ('a b', 'c.d'), ('a', 'b\\c.d'),
                 ('a', 'b".c.d'), ('a", "b', 'c.d')]
        keys = [eligibility.hop_key(p, s) for p, s in pairs]
        self.assertEqual(len(set(keys)), len(keys))
        for (p, s), k in zip(pairs, keys):
            self.assertEqual(json.loads(k), [paths.canonical(p), s])


class DuplicateRecordIdAcrossCollectionsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        self.path = os.path.join(self.repo, ".security", "feedback.json")

    def tearDown(self):
        self._tmp.cleanup()

    def _store_with_shared_id(self):
        s = store.empty_store()
        store.append_rejection_record(s, _record("same"))
        s["missRecords"]["same"] = dict(_miss("same"))
        return s

    def test_load_of_a_file_with_one_id_in_both_collections_degrades(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self._store_with_shared_id(), fh)
        result = store.load(self.path, repo_root=self.repo)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)
        self.assertIn("both", result.reason)

    def test_write_refuses_and_leaves_the_file_unchanged(self):
        h = store.write(self.path, store.empty_store(), repo_root=self.repo, expected_on_disk_hash=None, git_commit=None)
        with open(self.path, "rb") as fh:
            before = fh.read()
        with self.assertRaises(store.StoreError):
            store.write(self.path, self._store_with_shared_id(), repo_root=self.repo, expected_on_disk_hash=h, git_commit=None)
        with open(self.path, "rb") as fh:
            self.assertEqual(fh.read(), before)


class FormatCharacterPathPolicyTests(unittest.TestCase):
    REJECTED = {
        "zero-width space segment": "src/\u200b/R.cs",
        "zero-width joiner inside a name": "src/R\u200d.cs",
        "right-to-left override": "src/invoice\u202egpj.cs",
        "byte-order mark prefix": "\ufeffsrc/R.cs",
        "isolate control": "src/\u2066R.cs",
    }

    def test_every_format_character_is_rejected_by_normalize_validate_and_canonical(self):
        for label, raw in self.REJECTED.items():
            for fn in (paths.normalize, paths.validate, paths.canonical):
                with self.subTest(case=label, fn=fn.__name__):
                    with self.assertRaises(paths.InvalidPathError):
                        fn(raw)

    def test_the_error_message_escapes_the_character(self):
        with self.assertRaises(paths.InvalidPathError) as ctx:
            paths.validate("src/invoice\u202egpj.cs")
        self.assertIn("\\u202e", str(ctx.exception))
        self.assertNotIn("\u202e", str(ctx.exception))

    def test_legitimate_non_ascii_names_are_still_accepted(self):
        for raw in ("src/caf\u00e9.cs", "src/cafe\u0301.cs", "src/\u5831\u544a.cs", "docs/r\u00e9sum\u00e9 v2.md"):
            with self.subTest(raw=raw):
                self.assertEqual(paths.validate(raw), raw)

    def test_record_creation_is_refused(self):
        with self.assertRaises(schema.SchemaError):
            _record(path="src/R\u200b.cs")

    def test_a_stored_record_with_such_a_path_degrades_the_whole_store(self):
        with tempfile.TemporaryDirectory() as repo:
            path = os.path.join(repo, ".security", "feedback.json")
            s = store.empty_store()
            store.append_rejection_record(s, _record("good"))
            bad = _record("bad")
            bad["evidence"]["path"] = "a/Repository\u200b.cs"
            bad["candidateShape"]["reachabilityPath"][0]["path"] = "a/Repository\u200b.cs"
            s["rejectionRecords"]["bad"] = bad
            os.makedirs(os.path.dirname(path))
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(s, fh)
            result = store.load(path, repo_root=repo)
            self.assertFalse(result.ok)
            self.assertTrue(result.degraded)

    def test_changed_files_with_such_a_path_fail_loudly_never_as_unchanged(self):
        with self.assertRaises(paths.InvalidPathError):
            eligibility._check_c_dependencies(["a/Repository.cs"], ["a/Repository\u200b.cs"])
        with self.assertRaises(paths.InvalidPathError):
            invalidation.find_directly_stale({"r1": _record("r1")}, ["a/Repository\u200b.cs"])


if __name__ == "__main__":
    unittest.main()
