"""V4 release: a REJECTED record contradicted by a fresh validation must never stay reusable because the ordinary
store call failed (store.invalidate_contradicted / recover_quarantine). Failure-injection tests for the persistence
path and for what a later reuse attempt sees."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import unittest.mock

from .. import eligibility, schema, store

PATH = [{"path": "src/Controllers/ReportsController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportsController.Get(int)"},
        {"path": "src/Repositories/ReportRepository.cs", "qualifiedSymbol": "MyApp.Repositories.ReportRepository.Find(int)"}]


def _record(rid):
    return schema.new_rejection_record(
        record_id=rid, category="BOLA/IDOR", suspicion_pattern="caller-supplied id", safety_pattern="owner check upstream",
        reachability_path=PATH, rejection_reason="ownership enforced", evidence={"path": PATH[1]["path"], "observation": "o"},
        scope="this chain", trace_confidence="HIGH", dependencies=[p["path"] for p in PATH],
        last_validation={"timestamp": "2026-09-25T00:00:00Z", "commit": "abc1234", "validatedBy": "human"})


def _reusable(rec):
    d = eligibility.decide_reuse(
        record=rec, candidate_category="BOLA/IDOR", candidate_evidence_path=PATH[1]["path"], candidate_reachability_path=PATH,
        candidate_trace_confidence="HIGH", pattern_and_scope_match=True, known_condition_states={}, changed_files=[],
        hop_controls_confirmed={eligibility.hop_key(p["path"], p["qualifiedSymbol"]): True for p in PATH})
    return d.reusable, d.reasons


class _Repo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        self.path = os.path.join(self.repo, ".security", "feedback.json")
        s = store.empty_store()
        store.append_rejection_record(s, _record("rec-a"))
        store.append_rejection_record(s, _record("rec-b"))
        store.write(self.path, s, repo_root=self.repo, expected_on_disk_hash=None, git_commit="abc1234")

    def tearDown(self):
        self._tmp.cleanup()

    def store_lock_fails(self):
        """Make only the STORE's lock time out; the quarantine marker keeps its own working lock."""
        real = store._acquire_lock

        def acquire(path, *a, **k):
            if path == self.path:
                raise store.LockTimeoutError("simulated")
            return real(path, *a, **k)

        return unittest.mock.patch.object(store, "_acquire_lock", side_effect=acquire)

    def bytes_on_disk(self):
        with open(self.path, "rb") as fh:
            return fh.read()

    def later_reuse(self, rid="rec-a"):
        """What a later review sees: None if the store cannot be used at all, else (reusable, reasons)."""
        lr = store.load(self.path, repo_root=self.repo)
        if not lr.ok:
            return None, lr
        return _reusable(lr.store["rejectionRecords"][rid]), lr


class DurableInvalidationTests(_Repo):
    def test_contradicted_record_is_stale_on_disk_and_never_reused(self):
        res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit="def5678")
        self.assertTrue(res.durable)
        self.assertEqual(res.marked, ["rec-a"])
        self.assertFalse(res.quarantined)
        (reusable, reasons), lr = self.later_reuse()
        self.assertFalse(reusable)
        self.assertIn(eligibility.REASON_RECORD_STALE, reasons)
        self.assertEqual(lr.store["rejectionRecords"]["rec-a"]["staleReason"], store.CONTRADICTED_REASON)
        (other, _), _ = self.later_reuse("rec-b")
        self.assertTrue(other, "an uncontradicted record is untouched")

    def test_already_stale_and_missing_ids_need_no_write(self):
        store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        before = self.bytes_on_disk()
        res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a", "gone"], git_commit=None)
        self.assertTrue(res.durable)
        self.assertEqual((res.marked, res.already_stale, res.missing), ([], ["rec-a"], ["gone"]))
        self.assertEqual(self.bytes_on_disk(), before)

    def test_a_concurrent_change_is_reread_and_retried(self):
        real_write = store.write
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise store.ConcurrentModificationError("simulated concurrent writer")
            return real_write(*a, **k)

        with unittest.mock.patch.object(store, "write", side_effect=flaky):
            res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        self.assertTrue(res.durable)
        self.assertEqual(calls["n"], 2)
        (reusable, _), _ = self.later_reuse()
        self.assertFalse(reusable)

    def test_bad_arguments_raise_instead_of_doing_nothing(self):
        for bad in ("rec-a", [], [""], [None]):
            with self.subTest(bad=bad), self.assertRaises(TypeError):
                store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=bad, git_commit=None)


class QuarantineOnFailureTests(_Repo):
    def assert_quarantined_and_unchanged(self, res, before):
        self.assertFalse(res.durable)
        self.assertTrue(res.quarantined)
        self.assertEqual(self.bytes_on_disk(), before, "the store file itself is never partially rewritten")
        (verdict, lr) = self.later_reuse()
        self.assertIsNone(verdict, "no record can be reused from a quarantined store")
        self.assertTrue(lr.degraded)
        self.assertTrue(lr.quarantined)
        self.assertIn("quarantined", lr.reason)

    def test_lock_timeout_quarantines(self):
        before = self.bytes_on_disk()
        with self.store_lock_fails():
            res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        self.assert_quarantined_and_unchanged(res, before)

    def test_replace_failure_quarantines_and_leaves_no_temp_file(self):
        before = self.bytes_on_disk()
        # fail only the store's own replace, not the quarantine marker's
        real_replace = store._replace_with_retry

        def fail_store_only(tmp, dest):
            if dest == self.path:
                raise store.StoreError("simulated disk failure")
            return real_replace(tmp, dest)

        with unittest.mock.patch.object(store, "_replace_with_retry", side_effect=fail_store_only):
            res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        self.assert_quarantined_and_unchanged(res, before)
        leftovers = [n for n in os.listdir(os.path.dirname(self.path)) if n.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_repeated_concurrent_change_quarantines(self):
        before = self.bytes_on_disk()
        with unittest.mock.patch.object(store, "write", side_effect=store.ConcurrentModificationError("always")):
            res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        self.assert_quarantined_and_unchanged(res, before)

    def test_unreadable_store_is_quarantined_not_rewritten(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        before = self.bytes_on_disk()
        res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        self.assertFalse(res.durable)
        self.assertTrue(res.quarantined)
        self.assertEqual(self.bytes_on_disk(), before)

    def test_an_unusable_reason_quarantines(self):
        before = self.bytes_on_disk()
        res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None,
                                            reason='client_secret="Zx9Qw8Er7Ty6Ui5Op4"')
        self.assert_quarantined_and_unchanged(res, before)

    def test_quarantine_failure_raises_and_is_never_reported_as_done(self):
        with self.store_lock_fails(), \
             unittest.mock.patch.object(store, "_write_quarantine", side_effect=OSError("simulated: read-only volume")):
            with self.assertRaises(store.StoreError) as ctx:
                store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        self.assertIn("unusable for Evidence Reuse", str(ctx.exception))

    def test_an_existing_unreadable_quarantine_is_kept_still_blocks_and_the_new_ids_are_raised(self):
        q = store._quarantine_path_for(self.path)
        with open(q, "w", encoding="utf-8") as fh:
            fh.write("garbage")
        with self.store_lock_fails():
            with self.assertRaises(store.StoreError) as ctx:
                store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        self.assertIn("rec-a", str(ctx.exception), "the ids that could not be recorded are named, not dropped")
        with open(q, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "garbage")
        self.assertTrue(store.load(self.path, repo_root=self.repo).quarantined)
        with self.assertRaises(store.StoreError):
            store.recover_quarantine(self.path, repo_root=self.repo)

    def test_quarantines_accumulate_record_ids(self):
        with self.store_lock_fails():
            store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
            store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-b"], git_commit=None)
        with open(store._quarantine_path_for(self.path), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["recordIds"], ["rec-a", "rec-b"])


class AdversarialOrderingTests(_Repo):
    """Cases chosen with Jev (release cycle 2)."""

    def test_an_ordinary_write_does_not_lift_or_bypass_a_quarantine(self):
        with self.store_lock_fails():
            store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        raw = store._load_unchecked(self.path, repo_root=self.repo)
        store.increment_reuse_count(raw.store, "rec-a")
        store.write(self.path, raw.store, repo_root=self.repo, expected_on_disk_hash=raw.on_disk_hash, git_commit=None)
        verdict, lr = self.later_reuse()
        self.assertIsNone(verdict)
        self.assertTrue(lr.quarantined)

    def test_a_stop_right_after_the_durable_write_still_leaves_the_record_stale(self):
        with unittest.mock.patch.object(store, "InvalidationResult", side_effect=SystemExit("simulated process stop")):
            with self.assertRaises(SystemExit):
                store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        (reusable, reasons), lr = self.later_reuse()
        self.assertTrue(lr.ok)
        self.assertFalse(reusable)
        self.assertIn(eligibility.REASON_RECORD_STALE, reasons)


class QuarantineConcurrencyTests(_Repo):
    """Races the cycle-2 review reproduced (marker read-merge-replace and recover verify-then-remove were unlocked)."""

    def test_concurrent_failed_invalidations_keep_every_id(self):
        import threading
        ids = [f"rec-{i}" for i in range(8)]
        barrier = threading.Barrier(len(ids))

        def fail(rid):
            barrier.wait()
            store._write_quarantine(self.path, repo_root=self.repo, record_ids=[rid], detail="simulated")

        threads = [threading.Thread(target=fail, args=(rid,)) for rid in ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        with open(store._quarantine_path_for(self.path), encoding="utf-8") as fh:
            self.assertEqual(sorted(json.load(fh)["recordIds"]), sorted(ids))

    def test_an_id_added_during_recovery_is_not_lost(self):
        import threading
        with self.store_lock_fails():
            store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)  # durable now
        real_load = store._load_unchecked
        started = {}

        def load_during_recovery(*a, **k):
            # another run's failed invalidation of rec-b arrives while recovery is verifying
            t = threading.Thread(target=store._write_quarantine, args=(self.path,),
                                 kwargs={"repo_root": self.repo, "record_ids": ["rec-b"], "detail": "simulated"})
            t.start()
            t.join(timeout=0.5)
            started["thread"] = t
            return real_load(*a, **k)

        with unittest.mock.patch.object(store, "_load_unchecked", side_effect=load_during_recovery):
            self.assertEqual(store.recover_quarantine(self.path, repo_root=self.repo), ["rec-a"])
        started["thread"].join(timeout=10)
        lr = store.load(self.path, repo_root=self.repo)
        self.assertTrue(lr.quarantined, "rec-b's quarantine must survive the recovery of rec-a")
        with open(store._quarantine_path_for(self.path), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["recordIds"], ["rec-b"])

    def test_recovery_waits_for_the_marker_lock_and_never_removes_under_it(self):
        with self.store_lock_fails():
            store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        held = store._acquire_lock(store._quarantine_path_for(self.path))
        try:
            real = store._acquire_lock
            with unittest.mock.patch.object(store, "_acquire_lock", side_effect=lambda p, *a, **k: real(p, timeout=0.3)):
                with self.assertRaises(store.LockTimeoutError):
                    store.recover_quarantine(self.path, repo_root=self.repo)
        finally:
            store._release_lock(held)
        self.assertTrue(store.load(self.path, repo_root=self.repo).quarantined)


class LoadForInvalidationTests(_Repo):
    def test_a_quarantined_store_can_still_be_read_to_find_contradicted_ids_but_not_for_reuse(self):
        with self.store_lock_fails():
            store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        self.assertIsNone(store.load(self.path, repo_root=self.repo).store)
        lr = store.load_for_invalidation(self.path, repo_root=self.repo)
        self.assertTrue(lr.ok)
        self.assertIn("rec-b", lr.store["rejectionRecords"])
        res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-b"], git_commit=None)
        self.assertTrue(res.durable)
        self.assertTrue(store.load(self.path, repo_root=self.repo).quarantined)


class RecoveryTests(_Repo):
    def quarantine(self, ids):
        with self.store_lock_fails():
            return store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=ids, git_commit=None)

    def test_recovery_refuses_while_a_listed_record_is_still_reusable(self):
        self.quarantine(["rec-a"])
        with self.assertRaises(store.StoreError):
            store.recover_quarantine(self.path, repo_root=self.repo)
        self.assertTrue(store.load(self.path, repo_root=self.repo).quarantined)

    def test_recovery_after_a_durable_retry_lifts_the_quarantine_and_the_record_stays_stale(self):
        self.quarantine(["rec-a"])
        res = store.invalidate_contradicted(self.path, repo_root=self.repo, record_ids=["rec-a"], git_commit=None)
        self.assertTrue(res.durable)
        self.assertTrue(res.quarantined, "the quarantine is only lifted by recover_quarantine")
        self.assertTrue(store.load(self.path, repo_root=self.repo).quarantined)
        self.assertEqual(store.recover_quarantine(self.path, repo_root=self.repo), ["rec-a"])
        (reusable, reasons), lr = self.later_reuse()
        self.assertTrue(lr.ok)
        self.assertFalse(reusable)
        self.assertIn(eligibility.REASON_RECORD_STALE, reasons)
        (other, _), _ = self.later_reuse("rec-b")
        self.assertTrue(other)

    def test_recovery_without_a_quarantine_is_a_no_op(self):
        self.assertEqual(store.recover_quarantine(self.path, repo_root=self.repo), [])

    def test_recovery_refuses_while_the_store_is_unreadable(self):
        self.quarantine(["rec-a"])
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        with self.assertRaises(store.StoreError):
            store.recover_quarantine(self.path, repo_root=self.repo)


if __name__ == "__main__":
    unittest.main()
