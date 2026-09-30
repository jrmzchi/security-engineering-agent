"""Tests for the Round 5 close-out, per explicit instruction:

1. Unicode-normalized path canonicalization (NFC), shared by identity,
   eligibility, direct and central invalidation.
2. `load()` never lets a parser `ValueError` (e.g. Python 3.11+'s
   integer-string-length limit) escape.
3. Mutators are atomic: copy -> mutate -> validate -> commit; a failed
   mutation leaves the store deep-equal to what it was.
4. Strict miss-record validation at builder, append, write and load.
5. `lastValidation.commit` is `non-empty string | null` (Option A).
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unicodedata
import unittest

from .. import eligibility, identity, invalidation, paths, schema, store

NFC = unicodedata.normalize("NFC", "src/café/Report.cs")
NFD = unicodedata.normalize("NFD", NFC)
assert NFC != NFD  # the two spellings really are different code-point sequences


def _rec(record_id="r1", path=NFC, **overrides):
    kwargs = dict(
        record_id=record_id,
        category="BOLA/IDOR",
        suspicion_pattern="p",
        safety_pattern="s",
        reachability_path=[{"path": path, "qualifiedSymbol": "MyApp.Report.Get(int)"}],
        rejection_reason="r",
        evidence={"path": path, "observation": "o"},
        scope="scope",
        trace_confidence="HIGH",
        last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
    )
    kwargs.update(overrides)
    return schema.new_rejection_record(**kwargs)


def _miss(**overrides):
    kwargs = dict(
        record_id="m1", layer="routing", observed_miss="missed IDOR on export endpoint",
        expected_finding="CONFIRMED HIGH BOLA/IDOR", prior_layers_passed=[],
        evidence={"path": "src/C.cs", "observation": "endpoint never routed to authorization domain"},
        remediation="fix the routing table", scope="this endpoint shape", human_confirmed_by="reviewer",
        created_at="2026-09-23T00:00:00Z",
    )
    kwargs.update(overrides)
    return schema.new_miss_record(**kwargs)


def _decide(record, candidate_path, changed):
    return eligibility.decide_reuse(
        record=record, candidate_category="BOLA/IDOR", candidate_evidence_path=candidate_path,
        candidate_reachability_path=[{"path": candidate_path, "qualifiedSymbol": "MyApp.Report.Get(int)"}],
        candidate_trace_confidence="HIGH", pattern_and_scope_match=True, known_condition_states={},
        changed_files=changed,
        hop_controls_confirmed={eligibility.hop_key(candidate_path, "MyApp.Report.Get(int)"): True},
    )


class TempRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo_root = self._tmp.name
        os.makedirs(os.path.join(self.repo_root, ".security"))
        self.path = os.path.join(self.repo_root, ".security", "feedback.json")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_raw(self, text):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(text)


# ---------------------------------------------------------------- 1. Unicode


class UnicodeCanonicalizationTests(unittest.TestCase):
    def test_canonical_order_is_validate_then_nfc_then_casefold(self):
        self.assertEqual(paths.canonical(NFD), paths.canonical(NFC))
        self.assertEqual(paths.canonical(NFD.upper()), paths.canonical(NFC))
        self.assertEqual(paths.canonical(NFD), unicodedata.normalize("NFC", NFD).casefold())
        with self.assertRaises(paths.InvalidPathError):
            paths.canonical("/" + NFD)  # validate() still runs first

    def test_same_path_both_directions(self):
        self.assertTrue(paths.same_path(NFC, NFD))
        self.assertTrue(paths.same_path(NFD, NFC))

    def test_existing_cases_preserved(self):
        self.assertTrue(paths.same_path("Src/File.cs", "src/file.cs"))
        self.assertTrue(paths.same_path("a/b/c.cs", "a\\b\\c.cs"))
        self.assertTrue(paths.same_path("a//b/./c.cs", "a/b/c.cs"))
        self.assertFalse(paths.same_path("a/b.cs", "a/c.cs"))

    def test_casefold_merges_more_than_case_and_that_is_documented(self):
        self.assertTrue(paths.same_path("src/Straße.cs", "src/STRASSE.cs"))
        self.assertIn("ß", paths.canonical.__doc__)
        self.assertIn("NFC", paths.canonical.__doc__)

    def test_direct_invalidation_nfc_record_vs_nfd_diff_and_reverse(self):
        rec_nfc = _rec("nfc", path=NFC)
        rec_nfd = _rec("nfd", path=NFD)
        self.assertEqual([f.record_id for f in invalidation.find_directly_stale({"nfc": rec_nfc}, [NFD])], ["nfc"])
        self.assertEqual([f.record_id for f in invalidation.find_directly_stale({"nfd": rec_nfd}, [NFC])], ["nfd"])
        self.assertEqual(invalidation.find_directly_stale({"nfc": rec_nfc}, ["src/other.cs"]), [])

    def test_central_invalidation_nfc_vs_nfd_prefix_and_reverse(self):
        prefix_nfc = unicodedata.normalize("NFC", "src/café")
        prefix_nfd = unicodedata.normalize("NFD", prefix_nfc)
        rec_nfc = _rec("nfc", path=NFC)
        rec_nfd = _rec("nfd", path=NFD)
        self.assertEqual(
            [f.record_id for f in invalidation.find_central_component_stale({"nfc": rec_nfc}, central_component_file="x", affected_path_prefixes=[prefix_nfd])],
            ["nfc"],
        )
        self.assertEqual(
            [f.record_id for f in invalidation.find_central_component_stale({"nfd": rec_nfd}, central_component_file="x", affected_path_prefixes=[prefix_nfc])],
            ["nfd"],
        )

    def test_decide_reuse_does_not_reuse_across_unicode_forms_when_sink_changed(self):
        # record NFC, diff NFD -> check (c) must see the sink changed
        d = _decide(_rec(path=NFC), candidate_path=NFD, changed=[NFD])
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_DEPENDENCY_CHANGED, d.reasons)
        # reverse
        d = _decide(_rec(path=NFD), candidate_path=NFC, changed=[NFC])
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_DEPENDENCY_CHANGED, d.reasons)
        # and with nothing changed, the two forms are the same occurrence (control)
        d = _decide(_rec(path=NFC), candidate_path=NFD, changed=[])
        self.assertTrue(d.reusable, d.reasons)

    def test_identity_and_hop_key_agree_across_forms(self):
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR", candidate_evidence_path=NFD,
            candidate_reachability_path=[{"path": NFD, "qualifiedSymbol": "MyApp.Report.Get(int)"}],
            candidate_trace_confidence="HIGH", record=_rec(path=NFC),
        )
        self.assertTrue(r.same_occurrence)
        self.assertEqual(eligibility.hop_key(NFC, "x.y"), eligibility.hop_key(NFD, "x.y"))


# ---------------------------------------------------------------- 2. ValueError


class LoadParserValueErrorTests(TempRepo):
    def test_huge_integer_literal_degrades_not_raises(self):
        import sys
        limit = sys.get_int_max_str_digits() if hasattr(sys, "get_int_max_str_digits") else 4300
        self._write_raw('{"schemaVersion": 2, "rejectionRecords": {}, "missRecords": {}, "junk": ' + "9" * (limit + 700) + "}")
        result = store.load(self.path, repo_root=self.repo_root)  # must not raise
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)
        self.assertTrue(result.reason)

    def test_invalid_json_and_deep_nesting_still_degrade(self):
        self._write_raw("{not json")
        r = store.load(self.path, repo_root=self.repo_root)
        self.assertFalse(r.ok)
        self.assertIn("invalid JSON", r.reason)
        depth = 200000
        self._write_raw("[" * depth + "]" * depth)
        r = store.load(self.path, repo_root=self.repo_root)
        self.assertFalse(r.ok)
        self.assertIn("deep", r.reason)

    def test_except_order_has_no_unreachable_branch(self):
        # JSONDecodeError is a ValueError subclass: the specific branch
        # must come first or it could never fire. Prove both fire.
        self._write_raw("{")
        self.assertIn("invalid JSON", store.load(self.path, repo_root=self.repo_root).reason)
        self._write_raw("[" + "1" * 6000 + "]")
        self.assertIn("could not be parsed safely", store.load(self.path, repo_root=self.repo_root).reason)


# ---------------------------------------------------------------- 3. Mutators


class AtomicMutatorTests(TempRepo):
    def _store_with(self, *records):
        s = store.empty_store()
        for r in records:
            store.append_rejection_record(s, r)
        return s

    def test_mark_stale_bad_reason_leaves_store_deep_equal(self):
        s = self._store_with(_rec())
        before = copy.deepcopy(s)
        for bad in ("", "   ", None, 5, 'client_secret="Zx9Qw8Er7Ty6Ui5Op4"'):
            with self.subTest(reason=bad):
                with self.assertRaises(schema.SchemaError):
                    store.mark_stale(s, "r1", reason=bad)
                self.assertEqual(s, before)
                self.assertNotIn("status", s["rejectionRecords"]["r1"])
                self.assertNotIn("staleReason", s["rejectionRecords"]["r1"])

    def test_mark_stale_good_reason_commits_and_is_writable(self):
        s = self._store_with(_rec())
        store.mark_stale(s, "r1", reason="dependency changed")
        self.assertEqual(s["rejectionRecords"]["r1"]["status"], schema.STATUS_STALE)
        store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        self.assertTrue(store.load(self.path, repo_root=self.repo_root).ok)

    def test_increment_rejects_bool_missing_and_negative_without_mutating(self):
        for bad in (True, False, -1, "0", None, 1.0):
            with self.subTest(value=bad):
                s = self._store_with(_rec())
                s["rejectionRecords"]["r1"]["reuseCount"] = bad  # corrupt in place
                before = copy.deepcopy(s)
                with self.assertRaises(schema.SchemaError):
                    store.increment_reuse_count(s, "r1")
                self.assertEqual(s, before)
        s = self._store_with(_rec())
        del s["rejectionRecords"]["r1"]["reuseCount"]
        before = copy.deepcopy(s)
        with self.assertRaises(schema.SchemaError):
            store.increment_reuse_count(s, "r1")
        self.assertEqual(s, before)

    def test_increment_happy_path_still_works(self):
        s = self._store_with(_rec())
        self.assertEqual(store.increment_reuse_count(s, "r1"), 1)
        self.assertEqual(store.increment_reuse_count(s, "r1"), 2)
        self.assertEqual(s["rejectionRecords"]["r1"]["reuseCount"], 2)

    def test_mutators_validate_the_whole_candidate_not_just_the_touched_field(self):
        # A record corrupted elsewhere must not be silently re-committed
        # by an unrelated mutation.
        s = self._store_with(_rec())
        s["rejectionRecords"]["r1"]["dependencies"] = None
        before = copy.deepcopy(s)
        with self.assertRaises(schema.SchemaError):
            store.mark_stale(s, "r1", reason="x")
        self.assertEqual(s, before)

    def test_legacy_record_mark_stale_uses_audit_validator_and_stays_non_reusable(self):
        legacy = {
            "recordType": schema.RECORD_TYPE_REJECTION, "recordId": "L",
            "candidateShape": {"category": "BOLA/IDOR", "reachabilityPath": [{"path": "a/x.cs", "symbol": "Get"}]},
            "rejectionReason": "r", "evidence": {"path": "a/x.cs", "observation": "o"}, "scope": "s",
        }
        s = store.empty_store()
        s["rejectionRecords"]["L"] = legacy  # can only get in via load(); simulate
        store.mark_stale(s, "L", reason="audit note")  # lenient validator, not strict
        self.assertEqual(s["rejectionRecords"]["L"]["status"], schema.STATUS_STALE)
        with self.assertRaises(store.StoreError):
            store.increment_reuse_count(s, "L")
        d = eligibility.decide_reuse(
            record=s["rejectionRecords"]["L"], candidate_category="BOLA/IDOR", candidate_evidence_path="a/x.cs",
            candidate_reachability_path=[{"path": "a/x.cs", "qualifiedSymbol": "N.T.Get"}], candidate_trace_confidence="HIGH",
            pattern_and_scope_match=True, known_condition_states={}, changed_files=[], hop_controls_confirmed={},
        )
        self.assertFalse(d.reusable)
        self.assertEqual(d.reasons, [eligibility.REASON_RECORD_LEGACY_SCHEMA])

    def test_append_commits_a_copy_so_caller_cannot_corrupt_the_store_afterwards(self):
        s = store.empty_store()
        rec = _rec()
        store.append_rejection_record(s, rec)
        rec["dependencies"] = None  # caller keeps mutating its own dict
        schema.validate_rejection_record(s["rejectionRecords"]["r1"])  # store copy unaffected
        store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)

    def test_mark_revalidated_non_mapping_is_a_schema_error(self):
        s = self._store_with(_rec())
        before = copy.deepcopy(s)
        with self.assertRaises(schema.SchemaError):
            store.mark_revalidated(s, "r1", None)
        self.assertEqual(s, before)

    def test_mark_revalidated_can_replace_a_legacy_record_with_a_fresh_current_one(self):
        legacy = {
            "recordType": schema.RECORD_TYPE_REJECTION, "recordId": "r1",
            "candidateShape": {"category": "BOLA/IDOR", "reachabilityPath": [{"path": NFC, "symbol": "Get"}]},
            "rejectionReason": "r", "evidence": {"path": NFC, "observation": "o"}, "scope": "s",
        }
        s = store.empty_store()
        s["rejectionRecords"]["r1"] = legacy
        store.mark_revalidated(s, "r1", _rec("r1"))
        self.assertFalse(schema.is_legacy_shaped(s["rejectionRecords"]["r1"]))


class BuilderSelfValidationTests(unittest.TestCase):
    def test_builders_validate_their_own_output(self):
        # Mutate the validator to always fail; the builder must now fail too.
        original = schema.validate_rejection_record
        try:
            def _always_fail(record):
                raise schema.SchemaError("mutated")
            schema.validate_rejection_record = _always_fail
            with self.assertRaises(schema.SchemaError):
                _rec()
        finally:
            schema.validate_rejection_record = original
        original_m = schema.validate_miss_record
        try:
            def _always_fail_m(record):
                raise schema.SchemaError("mutated")
            schema.validate_miss_record = _always_fail_m
            with self.assertRaises(schema.SchemaError):
                _miss()
        finally:
            schema.validate_miss_record = original_m
        # and they still succeed with the real validators
        _rec()
        _miss()


# ---------------------------------------------------------------- 4. Miss records


class MissRecordStrictValidationTests(TempRepo):
    def _raw_miss(self, **overrides):
        rec = _miss()
        rec.update(overrides)
        return rec

    def test_builder_and_validator_agree_on_every_rejection(self):
        cases = {
            "empty_observed": dict(observed_miss=""),
            "none_scope": dict(scope=None),
            "int_remediation": dict(remediation=5),
            "bad_layer": dict(layer="nope"),
            "layer_in_prior": dict(layer="reasoning", prior_layers_passed=["reasoning"]),
            "prior_not_list": dict(prior_layers_passed="routing"),
            "evidence_none": dict(evidence=None),
            "evidence_str": dict(evidence="just text"),
            "evidence_empty_list": dict(evidence=[]),
            "evidence_no_observation": dict(evidence={"path": "src/C.cs"}),
            "evidence_bad_path": dict(evidence={"path": "/abs/C.cs", "observation": "o"}),
            "secret_in_text": dict(observed_miss="password=ABCDEFGHIJKLMNOP"),
            "secret_in_evidence": dict(evidence={"observation": "api_key: sk_live_abcdefghijklmnop"}),
            "api_key_nested_list": dict(evidence=[{"observation": "fine"}, {"observation": "AKIAABCDEFGHIJKLMNOP"}]),
        }
        for name, override in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(schema.SchemaError):
                    _miss(**override)

    def test_append_write_load_reject_what_the_builder_rejects(self):
        good = _miss()
        broken_variants = [
            dict(good, observedMiss=""),
            dict(good, scope=None),
            dict(good, evidence=None),
            dict(good, evidence="text"),
            dict(good, remediation=["a"]),
            dict(good, priorLayersPassed="routing"),
            dict(good, layer=True),
            dict(good, observedMiss="password=ABCDEFGHIJKLMNOP"),
        ]
        for broken in broken_variants:
            with self.subTest(broken={k: v for k, v in broken.items() if good.get(k) != v}):
                s = store.empty_store()
                with self.assertRaises(schema.SchemaError):
                    store.append_miss_record(s, broken)
                self.assertEqual(s["missRecords"], {})
                # forced into a store in memory: write refuses
                s["missRecords"]["m1"] = broken
                with self.assertRaises(store.StoreError):
                    store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
                self.assertFalse(os.path.exists(self.path))
                # forced onto disk: load degrades
                self._write_raw(json.dumps(s))
                result = store.load(self.path, repo_root=self.repo_root)
                self.assertFalse(result.ok)
                os.remove(self.path)

    def test_one_broken_miss_record_never_reaches_a_valid_store(self):
        s = store.empty_store()
        store.append_rejection_record(s, _rec())
        store.append_miss_record(s, _miss())
        with self.assertRaises(schema.SchemaError):
            store.append_miss_record(s, dict(_miss(record_id="m2"), evidence=None))
        store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        loaded = store.load(self.path, repo_root=self.repo_root)
        self.assertTrue(loaded.ok)
        self.assertEqual(set(loaded.store["missRecords"]), {"m1"})

    def test_bool_never_impersonates_a_string(self):
        for field in ("observedMiss", "scope", "createdAt"):
            with self.subTest(field=field):
                with self.assertRaises(schema.SchemaError):
                    schema.validate_miss_record(self._raw_miss(**{field: True}))

    def test_valid_miss_record_round_trips(self):
        s = store.empty_store()
        store.append_miss_record(s, _miss(evidence=[{"path": "src/C.cs", "observation": "a"}, {"observation": "b"}]))
        store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        self.assertTrue(store.load(self.path, repo_root=self.repo_root).ok)


# ---------------------------------------------------------------- 5. commit nullable


class LastValidationCommitNullableTests(TempRepo):
    def test_null_commit_accepted_everywhere(self):
        rec = _rec(last_validation={"timestamp": "t", "commit": None, "validatedBy": "human"})
        schema.validate_rejection_record(rec)
        s = store.empty_store()
        store.append_rejection_record(s, rec)
        store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        loaded = store.load(self.path, repo_root=self.repo_root)
        self.assertTrue(loaded.ok)
        self.assertIsNone(loaded.store["rejectionRecords"]["r1"]["lastValidation"]["commit"])
        self.assertTrue(_decide(loaded.store["rejectionRecords"]["r1"], NFC, []).reusable)

    def test_empty_or_non_string_commit_rejected(self):
        for bad in ("", "  ", 5, False, []):
            with self.subTest(value=bad):
                with self.assertRaises(schema.SchemaError):
                    _rec(last_validation={"timestamp": "t", "commit": bad, "validatedBy": "human"})
        rec = _rec()
        rec["lastValidation"]["commit"] = ""
        with self.assertRaises(schema.SchemaError):
            schema.validate_rejection_record(rec)

    def test_timestamp_still_required_non_empty(self):
        for bad in (None, "", 5):
            with self.subTest(value=bad):
                with self.assertRaises(schema.SchemaError):
                    _rec(last_validation={"timestamp": bad, "commit": "c", "validatedBy": "human"})
        with self.assertRaises(schema.SchemaError):
            _rec(last_validation={"commit": "c", "validatedBy": "human"})


if __name__ == "__main__":
    unittest.main()
