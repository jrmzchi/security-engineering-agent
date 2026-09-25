from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
import unittest.mock

from .. import identity, paths, schema, store


def _sample_record(record_id="r1"):
    return schema.new_rejection_record(
        record_id=record_id,
        category="BOLA/IDOR",
        suspicion_pattern="p",
        safety_pattern="s",
        reachability_path=[{"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"}],
        rejection_reason="reason",
        evidence={"path": "a/Repository.cs", "observation": "o"},
        scope="scope",
        trace_confidence="HIGH",
        last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
    )


class TempRepoTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo_root = self._tmp.name
        self.security_dir = os.path.join(self.repo_root, ".security")
        os.makedirs(self.security_dir, exist_ok=True)
        self.feedback_path = os.path.join(self.security_dir, "feedback.json")

    def tearDown(self):
        self._tmp.cleanup()


class FirstWriteCreatesDirectoryTests(unittest.TestCase):
    """[ADDED, per a round-2 independent review Major]: write() moved
    the lock-file acquisition before directory creation, so the FIRST
    write to a repo that has no `.security/` yet raised a raw
    FileNotFoundError instead of succeeding -- a real regression from
    the round-1 lock fix, masked in every other test by `setUp()`
    always pre-creating the directory."""

    def test_first_write_to_a_brand_new_repo_succeeds(self):
        with tempfile.TemporaryDirectory() as repo_root:
            feedback_path = os.path.join(repo_root, ".security", "feedback.json")
            self.assertFalse(os.path.exists(os.path.dirname(feedback_path)))
            h = store.write(feedback_path, store.empty_store(), repo_root=repo_root, expected_on_disk_hash=None, git_commit=None)
            self.assertTrue(os.path.exists(feedback_path))
            result = store.load(feedback_path, repo_root=repo_root)
            self.assertTrue(result.ok)
            self.assertEqual(result.on_disk_hash, h)


class LoadMissingAndEmptyTests(TempRepoTestCase):
    def test_missing_file_is_not_an_error(self):
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(result.ok)
        self.assertFalse(result.degraded)
        self.assertEqual(result.store["rejectionRecords"], {})
        self.assertIsNone(result.on_disk_hash)

    def test_empty_store_round_trips(self):
        empty = store.empty_store()
        h = store.write(self.feedback_path, empty, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(result.ok)
        self.assertEqual(result.store["rejectionRecords"], {})
        self.assertEqual(result.on_disk_hash, h)

    def test_valid_store_with_a_record_round_trips(self):
        s = store.empty_store()
        store.append_rejection_record(s, _sample_record())
        store.write(self.feedback_path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit="abc")
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(result.ok)
        self.assertIn("r1", result.store["rejectionRecords"])
        self.assertEqual(result.store["gitCommit"], "abc")


class CorruptionTests(TempRepoTestCase):
    def test_invalid_json_is_degraded_not_partially_trusted(self):
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)
        self.assertIsNone(result.store)
        self.assertIn("invalid JSON", result.reason)

    def test_not_utf8_is_degraded(self):
        with open(self.feedback_path, "wb") as f:
            f.write(b"\xff\xfe\x00\x01")
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)

    def test_top_level_not_an_object_is_degraded(self):
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump([1, 2, 3], f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)

    def test_unknown_schema_version_is_degraded_never_guessed(self):
        s = store.empty_store()
        s["schemaVersion"] = 999
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)
        self.assertIn("schemaVersion", result.reason)

    def test_missing_required_field_degrades_whole_store(self):
        s = store.empty_store()
        rec = _sample_record()
        del rec["dependencies"]
        s["rejectionRecords"]["r1"] = rec
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)

    def test_one_bad_record_degrades_the_whole_store_not_just_that_record(self):
        # "不得部分相信可解析的片段" -- a valid record alongside one bad
        # record must NOT come back as "the good one is usable."
        s = store.empty_store()
        good = _sample_record("good")
        bad = _sample_record("bad")
        del bad["evidence"]
        s["rejectionRecords"]["good"] = good
        s["rejectionRecords"]["bad"] = bad
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)
        self.assertIsNone(result.store)

    def test_non_dict_record_entry_degrades_not_crashes(self):
        """[ADDED, per a round-1 independent review Minor]: a bare
        string (or any non-mapping) record entry used to raise
        AttributeError, escaping load()'s own "never raises" guarantee."""
        s = store.empty_store()
        s["rejectionRecords"]["r1"] = "garbage"
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)  # must not raise
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)

    def test_bool_schema_version_is_rejected_not_treated_as_1(self):
        """[ADDED, per a round-1 independent review Minor]: `True == 1`
        in Python, so `"schemaVersion": true` was silently accepted."""
        s = store.empty_store()
        s["schemaVersion"] = True
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)

    def test_float_schema_version_is_rejected_not_treated_as_1(self):
        """[ADDED, per a round-1 independent review Minor]: `1.0 == 1`
        in Python, so `"schemaVersion": 1.0` was silently accepted."""
        s = store.empty_store()
        s["schemaVersion"] = 1.0
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)

    def test_lowercase_stale_status_is_rejected(self):
        """[ADDED, per a round-1 independent review Minor]: a
        hand-edited `"status": "stale"` (wrong case) previously loaded
        successfully and would then be silently treated as fresh by
        eligibility.py (which only checks the exact string `"STALE"`)."""
        s = store.empty_store()
        rec = _sample_record()
        rec["status"] = "stale"
        s["rejectionRecords"]["r1"] = rec
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)

    def test_non_int_reuse_count_is_rejected(self):
        """[ADDED, per a round-1 independent review Minor]: a
        hand-edited `"reuseCount": "x"` previously loaded successfully
        and only broke later, inside eligibility.py's `>=` comparison."""
        s = store.empty_store()
        rec = _sample_record()
        rec["reuseCount"] = "x"
        s["rejectionRecords"]["r1"] = rec
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)

    def test_sink_not_matching_reachability_path_last_entry_is_rejected(self):
        """[ADDED, per a round-1 independent review Minor]: without
        this, evidence.path could point somewhere OUTSIDE
        reachabilityPath, so dependencies (derived from
        reachabilityPath) would never include the sink -- check (c)
        could then miss a sink-local regression entirely."""
        with self.assertRaises(schema.SchemaError):
            schema.new_rejection_record(
                record_id="r1", category="BOLA/IDOR",
                suspicion_pattern="p", safety_pattern="s",
                reachability_path=[
                    {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"},
                    {"path": "a/Service.cs", "qualifiedSymbol": "Service.Get"},
                ],
                rejection_reason="r",
                evidence={"path": "a/SomeOtherFile.cs", "observation": "o"},  # not the path's last entry
                scope="scope", trace_confidence="HIGH",
                last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
            )

    def test_key_recordid_mismatch_is_rejected(self):
        s = store.empty_store()
        rec = _sample_record("r1")
        s["rejectionRecords"]["different_key"] = rec
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)


def _legacy_record(record_id="legacy1"):
    """A hand-built record shaped exactly as a genuine schema-version-1
    store would have produced -- bare `symbol` hops, none of the
    version-2-only required fields (`dependencies`, `traceConfidence`,
    `lastValidation`, ...). Built by hand (not via
    `schema.new_rejection_record`, which now refuses this shape) to
    simulate a real pre-existing store."""
    return {
        "recordType": schema.RECORD_TYPE_REJECTION,
        "recordId": record_id,
        "candidateShape": {
            "category": "BOLA/IDOR",
            "reachabilityPath": [
                {"path": "a/Controller.cs", "symbol": "Get"},
                {"path": "a/Repository.cs", "symbol": "FindById"},
            ],
        },
        "rejectionReason": "ownership check present",
        "evidence": {"path": "a/Repository.cs", "observation": "o"},
        "scope": "this path only",
    }


class LegacySchemaVersionTests(TempRepoTestCase):
    """[ADDED, per explicit instruction for the schema-version-2
    migration]: a store whose top-level `schemaVersion` is
    `schema.LEGACY_SCHEMA_VERSION` (1) must load successfully
    (audit-only, `legacy=True`), not be treated as "unsupported" the
    way an unrecognized version number is."""

    def test_legacy_schema_version_loads_successfully_as_audit_only(self):
        s = store.empty_store()
        s["schemaVersion"] = schema.LEGACY_SCHEMA_VERSION
        s["rejectionRecords"]["legacy1"] = _legacy_record()
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(result.ok)
        self.assertFalse(result.degraded)
        self.assertTrue(result.legacy)
        self.assertTrue(result.has_legacy_records)
        self.assertIn("legacy1", result.store["rejectionRecords"])

    def test_legacy_record_still_refuses_to_identity_match_after_loading(self):
        # The record loaded fine (audit-only) -- but it must still be
        # useless for reuse, per identity.py's own guard.
        s = store.empty_store()
        s["schemaVersion"] = schema.LEGACY_SCHEMA_VERSION
        s["rejectionRecords"]["legacy1"] = _legacy_record()
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(result.ok)
        loaded = result.store["rejectionRecords"]["legacy1"]
        id_result = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=[
                {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"},
                {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
            ],
            candidate_trace_confidence="HIGH",
            record=loaded,
        )
        self.assertFalse(id_result.same_occurrence)
        self.assertEqual(id_result.reasons, [identity.LEGACY_RECORD_SCHEMA])

    def test_write_after_loading_a_legacy_store_does_not_silently_upgrade_records(self):
        """[REGRESSION TEST for a genuine defect found and fixed in this
        same phase]: `write()` always stamps the top-level
        `schemaVersion` tag with the CURRENT `schema.SCHEMA_VERSION` --
        true of the FILE FORMAT the writer produces, but this used to
        also make the very next `load()` apply the STRICT v2 validator
        to every record, including the still-legacy-shaped ones that
        write() left untouched. That degraded the WHOLE store (both the
        legacy record and anything else in it) on the very next load,
        after nothing more than one ordinary write. Reproduced directly
        against the pre-fix code (confirmed to fail before the fix in
        `store.py`'s `load()`/`_record_is_legacy_shaped` change); this
        test guards against that regression recurring.
        """
        s = store.empty_store()
        s["schemaVersion"] = schema.LEGACY_SCHEMA_VERSION
        s["rejectionRecords"]["legacy1"] = _legacy_record()
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)

        loaded = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(loaded.ok)

        store.write(
            self.feedback_path, loaded.store, repo_root=self.repo_root,
            expected_on_disk_hash=loaded.on_disk_hash, git_commit="c2",
        )
        reloaded = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(reloaded.ok, reloaded.reason)
        self.assertFalse(reloaded.degraded)
        # The store's own top-level tag is now 2 (the writer is
        # version-2-capable) -- but the still-legacy record inside it
        # must still be recognized as legacy, not silently "upgraded."
        self.assertFalse(reloaded.legacy)
        self.assertTrue(reloaded.has_legacy_records)
        self.assertIn("legacy1", reloaded.store["rejectionRecords"])

    def test_mixed_store_with_legacy_and_v2_records_both_survive_a_write(self):
        """"a mixed-version store (some records revalidated to v2,
        others still legacy) remains safe" -- per explicit instruction."""
        s = store.empty_store()
        s["schemaVersion"] = schema.LEGACY_SCHEMA_VERSION
        s["rejectionRecords"]["legacy1"] = _legacy_record()
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        loaded = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(loaded.ok)

        fresh_v2_record = _sample_record("v2rec")
        store.append_rejection_record(loaded.store, fresh_v2_record)
        store.write(
            self.feedback_path, loaded.store, repo_root=self.repo_root,
            expected_on_disk_hash=loaded.on_disk_hash, git_commit="c2",
        )

        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(result.ok, result.reason)
        self.assertFalse(result.legacy)  # top-level tag is now 2
        self.assertTrue(result.has_legacy_records)  # but legacy1 is still inside
        self.assertIn("legacy1", result.store["rejectionRecords"])
        self.assertIn("v2rec", result.store["rejectionRecords"])
        # And the fresh v2 record is fully usable for identity matching
        # (it has real qualifiedSymbol hops) while legacy1 still is not.
        v2_loaded = result.store["rejectionRecords"]["v2rec"]
        id_result = identity.check_occurrence_identity(
            candidate_category=v2_loaded["candidateShape"]["category"],
            candidate_evidence_path=v2_loaded["evidence"]["path"],
            candidate_reachability_path=v2_loaded["candidateShape"]["reachabilityPath"],
            candidate_trace_confidence="HIGH",
            record=v2_loaded,
        )
        self.assertTrue(id_result.same_occurrence)


class TopLevelTagNeverForcesLenientValidationTests(TempRepoTestCase):
    """[ADDED, per a Round 3 independent review Major]: the reviewer's
    own reproduction -- a store whose top-level `schemaVersion` is 1
    (legacy) but whose ONE record already has `qualifiedSymbol` on
    every hop (i.e. is fully v2-shaped) used to be validated with the
    LENIENT legacy validator anyway, purely because of the store's own
    tag (`if is_legacy or _record_is_legacy_shaped(record):`). That
    validator never checks `dependencies`/`lastValidation`/`status`'s
    enum/`reuseCount`'s bounds at all, so a record missing every one of
    those, with a wrong-case `"stale"` status, loaded successfully and
    was then judged REUSABLE despite its own dependencies having
    changed -- completely defeating this store's central safety
    property. Which validator applies must depend ONLY on the record's
    own shape, never on the store's tag."""

    def _v2_shaped_but_otherwise_incomplete_record(self, status=None):
        record = {
            "recordType": schema.RECORD_TYPE_REJECTION,
            "recordId": "F",
            "candidateShape": {
                "category": "BOLA/IDOR",
                "reachabilityPath": [
                    {"path": "src/C.cs", "qualifiedSymbol": "MyApp.C.Get"},
                    {"path": "src/R.cs", "qualifiedSymbol": "MyApp.R.FindById"},
                ],
            },
            "rejectionReason": "x",
            "evidence": {"path": "src/R.cs", "observation": "o"},
            "scope": "s",
            # Deliberately missing: dependencies, traceConfidence,
            # lastValidation, reuseCount -- everything the strict
            # validator requires and the lenient one does not.
        }
        if status is not None:
            record["status"] = status
        return record

    def test_v2_shaped_record_in_a_legacy_tagged_store_is_still_strictly_validated(self):
        s = store.empty_store()
        s["schemaVersion"] = schema.LEGACY_SCHEMA_VERSION
        s["rejectionRecords"]["F"] = self._v2_shaped_but_otherwise_incomplete_record(status="stale")
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)

        result = store.load(self.feedback_path, repo_root=self.repo_root)
        # Must be REFUSED (missing dependencies etc.), not silently
        # accepted via the lenient legacy validator just because the
        # store's own tag says 1.
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)
        self.assertIn("dependencies", result.reason)

    def test_legacy_tagged_store_with_zero_records_reports_no_legacy_records(self):
        # A store tagged 1 but with no records at all has nothing that
        # is actually legacy-shaped -- has_legacy_records must reflect
        # the ACTUAL records loaded, never just echo the tag.
        s = store.empty_store()
        s["schemaVersion"] = schema.LEGACY_SCHEMA_VERSION
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(s, f)
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertTrue(result.ok)
        self.assertTrue(result.legacy)  # the tag itself is still 1
        self.assertFalse(result.has_legacy_records)  # but there is nothing legacy-shaped inside


class NullQualifiedSymbolNeverMatchesTests(unittest.TestCase):
    """[ADDED, per a Round 3 independent review Major]: the reviewer's
    second variant of the same finding -- a record hop with
    `"qualifiedSymbol": None` (key PRESENT, value not a real string)
    combined with a candidate hop that OMITS the key entirely used to
    both resolve to `None` via `.get()` and compare equal to each
    other. Every layer that decides "is this legacy-shaped / does this
    match" must require an actual non-empty STRING value, not just key
    presence, independently at each layer."""

    def test_none_valued_hop_is_a_broken_current_record_not_legacy(self):
        """[REVISED, per explicit instruction closing a Round 4
        independent review Minor]: Round 3 made a present-but-invalid
        `qualifiedSymbol` count as "legacy", which routed a corrupted
        CURRENT record to the lenient validator. Legacy means the key is
        genuinely ABSENT; a `None` value is a broken current record that
        must fail STRICT validation instead."""
        record = {
            "candidateShape": {
                "category": "BOLA/IDOR",
                "reachabilityPath": [{"path": "a/C.cs", "qualifiedSymbol": None}],
            },
        }
        self.assertFalse(schema.is_legacy_shaped(record))
        self.assertFalse(identity._is_legacy_schema_record(record))
        with self.assertRaises(schema.SchemaError):
            schema.validate_rejection_record(record)

    def test_candidate_omitting_key_never_matches_record_with_none_value(self):
        record = {
            "candidateShape": {
                "category": "BOLA/IDOR",
                "reachabilityPath": [{"path": "a/C.cs", "qualifiedSymbol": None}],
            },
            "evidence": {"path": "a/C.cs", "observation": "o"},
        }
        candidate_omitting_key = [{"path": "a/C.cs"}]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/C.cs",
            candidate_reachability_path=candidate_omitting_key,
            candidate_trace_confidence="HIGH",
            record=record,
        )
        self.assertFalse(r.same_occurrence)
        # Not "legacy" any more -- a broken current record; refused
        # because two non-string qualifiedSymbols never compare equal.
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, r.reasons)

    def test_paths_module_itself_never_matches_two_none_valued_hops(self):
        # Even bypassing identity.py's own legacy guard entirely and
        # calling paths.same_reachability_path directly (as a defense-
        # in-depth check, not relying on any one layer alone).
        a = [{"path": "a/C.cs", "qualifiedSymbol": None}]
        b = [{"path": "a/C.cs", "qualifiedSymbol": None}]
        self.assertFalse(paths.same_reachability_path(a, b))

    def test_paths_module_never_matches_two_empty_string_hops(self):
        a = [{"path": "a/C.cs", "qualifiedSymbol": ""}]
        b = [{"path": "a/C.cs", "qualifiedSymbol": ""}]
        self.assertFalse(paths.same_reachability_path(a, b))


class DuplicateIdTests(unittest.TestCase):
    def test_append_rejects_duplicate_id(self):
        s = store.empty_store()
        store.append_rejection_record(s, _sample_record("r1"))
        with self.assertRaises(store.DuplicateRecordIdError):
            store.append_rejection_record(s, _sample_record("r1"))

    def test_rejection_and_miss_ids_share_one_namespace(self):
        s = store.empty_store()
        store.append_rejection_record(s, _sample_record("shared"))
        miss = schema.new_miss_record(
            record_id="shared", layer="routing", observed_miss="x", expected_finding="y",
            prior_layers_passed=[], evidence={"path": "a", "observation": "b"},
            remediation="r", scope="s", human_confirmed_by="h", created_at="t",
        )
        with self.assertRaises(store.DuplicateRecordIdError):
            store.append_miss_record(s, miss)


class AtomicWriteAndConcurrencyTests(TempRepoTestCase):
    def test_write_is_all_or_nothing_no_truncated_file_on_success(self):
        s = store.empty_store()
        store.append_rejection_record(s, _sample_record())
        store.write(self.feedback_path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        with open(self.feedback_path, encoding="utf-8") as f:
            content = f.read()
        # Must be complete, parseable JSON -- not left mid-write.
        json.loads(content)
        # No leftover temp files in the directory.
        leftover = [f for f in os.listdir(self.security_dir) if f != "feedback.json"]
        self.assertEqual(leftover, [])

    def test_concurrent_modification_detected_not_silently_overwritten(self):
        s = store.empty_store()
        h1 = store.write(self.feedback_path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        # Simulate a second writer.
        other = store.empty_store()
        store.append_rejection_record(other, _sample_record("other"))
        store.write(self.feedback_path, other, repo_root=self.repo_root, expected_on_disk_hash=h1, git_commit=None)

        # Original loader's h1 is now stale -- writing again with it
        # must be detected and refused (a lost update, not silently
        # applied).
        s2 = store.empty_store()
        store.append_rejection_record(s2, _sample_record("mine"))
        with self.assertRaises(store.ConcurrentModificationError):
            store.write(self.feedback_path, s2, repo_root=self.repo_root, expected_on_disk_hash=h1, git_commit=None)

        # The second writer's data must still be intact.
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertIn("other", result.store["rejectionRecords"])
        self.assertNotIn("mine", result.store["rejectionRecords"])

    def test_truly_concurrent_writers_do_not_lose_an_update(self):
        """[ADDED, per a round-1 independent review Major]: the
        previous hash-check-then-replace sequence had a real TOCTOU
        window -- the reviewer reproduced ~80% silent lost-updates
        under genuinely simultaneous writes (not just sequential
        overwrites). This test drives real concurrent threads (not a
        hand-simulated sequential interleaving) at the SAME starting
        hash and confirms exactly one wins and the other is detected,
        never both silently "succeeding" with one's data vanishing.
        """
        import threading

        h0 = store.write(self.feedback_path, store.empty_store(), repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)

        results = []
        barrier = threading.Barrier(2)

        def _writer(record_id):
            s = store.empty_store()
            store.append_rejection_record(s, _sample_record(record_id))
            barrier.wait()  # maximize the chance both threads race for the lock at the same instant
            try:
                store.write(self.feedback_path, s, repo_root=self.repo_root, expected_on_disk_hash=h0, git_commit=None)
                results.append((record_id, "ok"))
            except store.ConcurrentModificationError:
                results.append((record_id, "detected"))

        threads = [threading.Thread(target=_writer, args=(rid,)) for rid in ("A", "B")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        outcomes = sorted(r[1] for r in results)
        # Exactly one writer must succeed and the other must be
        # detected/refused -- "both silently ok" (a lost update) must
        # never happen.
        self.assertEqual(outcomes, ["detected", "ok"])

        winner = next(rid for rid, outcome in results if outcome == "ok")
        result = store.load(self.feedback_path, repo_root=self.repo_root)
        self.assertIn(winner, result.store["rejectionRecords"])
        self.assertEqual(len(result.store["rejectionRecords"]), 1)

    def test_stale_lock_is_removed_automatically(self):
        """[ADDED, per a round-2 independent review Minor]: a lockfile
        left behind by a crashed writer must not block every future
        write forever."""
        lock_path = store._lock_path_for(self.feedback_path)
        os.makedirs(self.security_dir, exist_ok=True)
        with open(lock_path, "w", encoding="utf-8"):
            pass
        stale_time = time.time() - (store.LOCK_STALE_SECONDS + 5)
        os.utime(lock_path, (stale_time, stale_time))
        # Must succeed promptly (well under the fresh-lock timeout),
        # not merely eventually after a full LOCK_TIMEOUT_SECONDS wait.
        started = time.monotonic()
        store.write(self.feedback_path, store.empty_store(), repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, store.LOCK_TIMEOUT_SECONDS)
        self.assertFalse(os.path.exists(lock_path))

    def test_fresh_lock_is_not_removed_and_times_out(self):
        """A lock that is NOT stale must still be respected -- confirms
        the staleness check has a real floor, not just "always remove
        on contention." Uses store._acquire_lock() directly with a
        short timeout so this test does not have to wait out the real
        (5s) default."""
        lock_path = store._lock_path_for(self.feedback_path)
        os.makedirs(self.security_dir, exist_ok=True)
        with open(lock_path, "w", encoding="utf-8"):
            pass  # freshly created -- not stale
        with self.assertRaises(store.LockTimeoutError):
            store._acquire_lock(self.feedback_path, timeout=0.2)
        os.remove(lock_path)

    def test_unremovable_stale_lock_still_respects_timeout(self):
        """[ADDED, per a Round 3 independent review Minor]: the stale-
        lock-removal branch used to `continue` unconditionally after
        attempting `os.remove`, NEVER checking `deadline` -- if removal
        kept failing (e.g. genuinely forbidden by permissions, or
        another process keeps recreating the lock), this looped
        forever, completely ignoring `timeout` and contradicting this
        function's own documented "fails closed... rather than
        proceeding unprotected" contract. Reproduced here by forcing
        every `os.remove` to fail."""
        lock_path = store._lock_path_for(self.feedback_path)
        os.makedirs(self.security_dir, exist_ok=True)
        with open(lock_path, "w", encoding="utf-8"):
            pass
        stale_time = time.time() - (store.LOCK_STALE_SECONDS + 5)
        os.utime(lock_path, (stale_time, stale_time))

        with unittest.mock.patch("os.remove", side_effect=OSError("simulated: permission denied")):
            started = time.monotonic()
            with self.assertRaises(store.LockTimeoutError):
                store._acquire_lock(self.feedback_path, timeout=0.3)
            elapsed = time.monotonic() - started
        # Must actually respect the timeout -- not hang, not loop for
        # far longer than requested.
        self.assertLess(elapsed, 3.0)
        os.remove(lock_path)

    def test_windows_permission_error_on_lock_creation_is_retried_not_raised(self):
        """[ADDED, per a Round 3 independent review Minor]: on Windows,
        `os.open(..., O_CREAT|O_EXCL)` can raise `PermissionError`
        (WinError 5) instead of `FileExistsError` when another process
        just deleted the same lockfile and it is briefly in a
        "delete pending" state (the reviewer reproduced this directly
        under an 8-thread stress test: 2 occurrences out of 320
        attempts). This must be treated as contention, retried like
        `FileExistsError`, not escape uncaught to a caller that may only
        be prepared to catch `StoreError`."""
        real_open = os.open
        call_count = {"n": 0}

        def _flaky_open(path, flags, *args, **kwargs):
            if path == store._lock_path_for(self.feedback_path) and call_count["n"] < 2:
                call_count["n"] += 1
                raise PermissionError("simulated: WinError 5 sharing violation")
            return real_open(path, flags, *args, **kwargs)

        os.makedirs(self.security_dir, exist_ok=True)
        with unittest.mock.patch("os.open", side_effect=_flaky_open):
            lock_path = store._acquire_lock(self.feedback_path, timeout=2.0)
        self.assertEqual(call_count["n"], 2)  # actually exercised the retry path
        self.assertTrue(os.path.exists(lock_path))
        os.remove(lock_path)

    def test_deterministic_serialization_no_diff_from_key_order_alone(self):
        s1 = {"b": 1, "a": 2}
        s1 = dict(store.empty_store(), **s1)
        s2 = {"a": 2, "b": 1}
        s2 = dict(store.empty_store(), **s2)
        path1 = os.path.join(self.security_dir, "f1.json")
        path2 = os.path.join(self.security_dir, "f2.json")
        store.write(path1, s1, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        store.write(path2, s2, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        with open(path1, encoding="utf-8") as f:
            c1 = f.read()
        with open(path2, encoding="utf-8") as f:
            c2 = f.read()
        self.assertEqual(c1, c2)


class SymlinkSafetyTests(TempRepoTestCase):
    def test_symlink_escaping_repo_root_is_refused(self):
        outside = tempfile.TemporaryDirectory()
        try:
            target = os.path.join(outside.name, "escaped.json")
            with open(target, "w", encoding="utf-8") as f:
                json.dump(store.empty_store(), f)
            link_path = os.path.join(self.security_dir, "feedback.json")
            try:
                os.symlink(target, link_path)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks not supported/permitted in this environment")
            with self.assertRaises(store.UnsafeStorePathError):
                store.load(link_path, repo_root=self.repo_root)
        finally:
            outside.cleanup()

    def test_symlinked_directory_with_no_file_inside_yet_is_refused(self):
        """[ADDED, per a round-1 independent review Minor]: the
        previous `_resolve_safe` only checked containment when the leaf
        file already existed -- a `.security` directory that is ITSELF
        a symlink/junction pointing outside the repo, with no
        `feedback.json` inside it yet, passed uncaught (the reasoning
        was "nothing there yet to have redirected anything," which
        missed that `os.path.realpath` still resolves symlinks in
        existing ANCESTOR directories even when the leaf is absent).
        """
        outside = tempfile.TemporaryDirectory()
        try:
            escaped_security_dir = os.path.join(outside.name, "escaped-security")
            os.makedirs(escaped_security_dir, exist_ok=True)
            linked_security_dir = os.path.join(self.repo_root, "linked-security")
            try:
                os.symlink(escaped_security_dir, linked_security_dir, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks not supported/permitted in this environment")
            not_yet_created_path = os.path.join(linked_security_dir, "feedback.json")
            self.assertFalse(os.path.exists(not_yet_created_path))
            with self.assertRaises(store.UnsafeStorePathError):
                store.load(not_yet_created_path, repo_root=self.repo_root)
            with self.assertRaises(store.UnsafeStorePathError):
                store.write(not_yet_created_path, store.empty_store(), repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        finally:
            outside.cleanup()


class ReuseCountTests(unittest.TestCase):
    """[ADDED, per a round-1 independent review Major]: increment_reuse_count()
    now exists; confirm it actually moves the counter and actually
    trips eligibility.decide_reuse()'s threshold after enough calls."""

    def test_increment_reuse_count_advances_the_counter(self):
        s = store.empty_store()
        store.append_rejection_record(s, _sample_record())
        self.assertEqual(store.increment_reuse_count(s, "r1"), 1)
        self.assertEqual(store.increment_reuse_count(s, "r1"), 2)
        self.assertEqual(s["rejectionRecords"]["r1"]["reuseCount"], 2)

    def test_increment_reuse_count_missing_record_raises(self):
        s = store.empty_store()
        with self.assertRaises(store.StoreError):
            store.increment_reuse_count(s, "does-not-exist")

    def test_repeated_reuse_eventually_trips_the_threshold(self):
        from .. import eligibility
        s = store.empty_store()
        store.append_rejection_record(s, _sample_record())
        for _ in range(eligibility.REUSE_COUNT_THRESHOLD - 1):
            store.increment_reuse_count(s, "r1")
        # [UPDATED after Round 5]: mutators now commit a validated COPY
        # (copy -> mutate -> validate -> commit), so a reference taken
        # before the increments is stale -- always read the record back
        # from the store, as a real caller would after any mutation.
        record = s["rejectionRecords"]["r1"]
        decision = eligibility.decide_reuse(
            record=record,
            candidate_category=record["candidateShape"]["category"],
            candidate_evidence_path=record["evidence"]["path"],
            candidate_reachability_path=record["candidateShape"]["reachabilityPath"],
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=True,
            known_condition_states={},
            changed_files=[],
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in record["candidateShape"]["reachabilityPath"]},
        )
        self.assertTrue(decision.reusable)  # one call short of the threshold
        store.increment_reuse_count(s, "r1")  # the Nth actual reuse
        record = s["rejectionRecords"]["r1"]
        decision = eligibility.decide_reuse(
            record=record,
            candidate_category=record["candidateShape"]["category"],
            candidate_evidence_path=record["evidence"]["path"],
            candidate_reachability_path=record["candidateShape"]["reachabilityPath"],
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=True,
            known_condition_states={},
            changed_files=[],
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in record["candidateShape"]["reachabilityPath"]},
        )
        self.assertFalse(decision.reusable)
        self.assertIn(eligibility.REASON_REUSE_COUNT_THRESHOLD_HIT, decision.reasons)


class RevalidationTests(unittest.TestCase):
    def test_mark_stale_then_mark_revalidated(self):
        s = store.empty_store()
        store.append_rejection_record(s, _sample_record())
        store.mark_stale(s, "r1", reason="dependency changed")
        self.assertEqual(s["rejectionRecords"]["r1"]["status"], "STALE")

        fresh = _sample_record()
        fresh["lastValidation"] = {"timestamp": "t2", "commit": "c2", "validatedBy": "human"}
        store.mark_revalidated(s, "r1", fresh)
        self.assertNotIn("status", s["rejectionRecords"]["r1"])
        self.assertEqual(s["rejectionRecords"]["r1"]["lastValidation"]["timestamp"], "t2")

    def test_mark_revalidated_refuses_a_still_stale_replacement(self):
        s = store.empty_store()
        store.append_rejection_record(s, _sample_record())
        still_stale = _sample_record()
        still_stale["status"] = "STALE"
        with self.assertRaises(store.StoreError):
            store.mark_revalidated(s, "r1", still_stale)


if __name__ == "__main__":
    unittest.main()
