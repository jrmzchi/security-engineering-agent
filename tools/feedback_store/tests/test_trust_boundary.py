"""The record trust boundary -- added per explicit instruction closing
the Round 4 independent review (its "decide_reuse accepts unvalidated
in-memory records" finding, promoted to Major by the user because the
append/replace APIs were themselves unvalidated inputs, so the path
was reachable in real use, not only by a test bypassing `load()`).

One rule, applied at EVERY public entry point -- `store.load`,
`store.write`, `store.append_rejection_record`,
`store.replace_rejection_record`, and `eligibility.decide_reuse` itself:

* "legacy" means the `qualifiedSymbol` KEY is genuinely absent on some
  hop (`schema.is_legacy_shaped`, the single definition). Such a
  record is audit-only: loadable, writable back unchanged, never
  appendable, never reusable.
* everything else is a CURRENT record and must pass
  `schema.validate_rejection_record` in full -- a present-but-invalid
  value is a BROKEN current record, never reclassified as legacy.
* `decide_reuse` never raises for a bad record and never reuses it: it
  returns NOT_REUSABLE with `RECORD_SCHEMA_INVALID` (and the diagnostic
  in `detail`) or the legacy reason.
* no field that feeds identity / reuse / invalidation / status is ever
  defaulted; `status` is an explicit allowlist.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import unittest.mock

from .. import eligibility, identity, invalidation, paths, schema, store


def _valid_record(record_id="r1", **overrides):
    kwargs = dict(
        record_id=record_id,
        category="BOLA/IDOR",
        suspicion_pattern="object reference from caller-supplied ID",
        safety_pattern="ownership check enforced",
        reachability_path=[
            {"path": "src/Controllers/ReportsController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportsController.Get(int)"},
            {"path": "src/Repositories/ReportRepository.cs", "qualifiedSymbol": "MyApp.Repositories.ReportRepository.FindById(int)"},
        ],
        rejection_reason="ownership check present",
        evidence={"path": "src/Repositories/ReportRepository.cs", "observation": "enforced upstream"},
        scope="this path only",
        trace_confidence="HIGH",
        last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
    )
    kwargs.update(overrides)
    return schema.new_rejection_record(**kwargs)


def _legacy_record(record_id="legacy1"):
    return {
        "recordType": schema.RECORD_TYPE_REJECTION,
        "recordId": record_id,
        "candidateShape": {
            "category": "BOLA/IDOR",
            "reachabilityPath": [
                {"path": "src/Controllers/ReportsController.cs", "symbol": "Get"},
                {"path": "src/Repositories/ReportRepository.cs", "symbol": "FindById"},
            ],
        },
        "rejectionReason": "ownership check present",
        "evidence": {"path": "src/Repositories/ReportRepository.cs", "observation": "o"},
        "scope": "this path only",
    }


def _decide(record, **overrides):
    shape = record.get("candidateShape", {})
    rp = shape.get("reachabilityPath", []) if isinstance(shape, dict) else []
    kwargs = dict(
        record=record,
        candidate_category=shape.get("category") if isinstance(shape, dict) else None,
        candidate_evidence_path="src/Repositories/ReportRepository.cs",
        candidate_reachability_path=rp,
        candidate_trace_confidence="HIGH",
        pattern_and_scope_match=True,
        known_condition_states={},
        changed_files=[],
        hop_controls_confirmed={
            eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True
            for e in rp if isinstance(e, dict) and isinstance(e.get("qualifiedSymbol"), str) and e["qualifiedSymbol"]
        },
    )
    kwargs.update(overrides)
    return eligibility.decide_reuse(**kwargs)


class TempRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo_root = self._tmp.name
        self.security_dir = os.path.join(self.repo_root, ".security")
        os.makedirs(self.security_dir)
        self.path = os.path.join(self.security_dir, "feedback.json")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_raw(self, s):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(s, f)


class LegacyDefinitionTests(unittest.TestCase):
    def test_legacy_means_key_absent_only(self):
        self.assertTrue(schema.is_legacy_shaped(_legacy_record()))
        current = _valid_record()
        self.assertFalse(schema.is_legacy_shaped(current))
        for bad_value in (None, "", "   ", 123, ["x"], {"a": 1}, True):
            with self.subTest(value=bad_value):
                broken = _valid_record()
                broken["candidateShape"]["reachabilityPath"][0]["qualifiedSymbol"] = bad_value
                self.assertFalse(schema.is_legacy_shaped(broken), "present-but-invalid is a broken CURRENT record")
                with self.assertRaises(schema.SchemaError):
                    schema.validate_rejection_record(broken)

    def test_one_definition_everywhere(self):
        """[STRENGTHENED, per explicit instruction after Round 6 (a
        Round 5 Nit): the previous assertion compared a module global
        to itself and was tautological]. Now a MUTATION test: replace
        `schema.is_legacy_shaped` with a stub that says "everything is
        legacy" and confirm identity, store (append + load-time
        validation) and invalidation all change behaviour together --
        which they can only do if each delegates to that one definition
        rather than carrying its own copy."""
        legacy = _legacy_record()
        current = _valid_record()
        self.assertTrue(identity._is_legacy_schema_record(legacy))
        self.assertFalse(hasattr(store, "_record_is_legacy_shaped"))
        original = schema.is_legacy_shaped
        try:
            schema.is_legacy_shaped = lambda record: True  # mutation: everything is "legacy"
            # identity: a perfectly valid current record is now refused as legacy
            r = identity.check_occurrence_identity(
                candidate_category="BOLA/IDOR", candidate_evidence_path="src/Repositories/ReportRepository.cs",
                candidate_reachability_path=current["candidateShape"]["reachabilityPath"],
                candidate_trace_confidence="HIGH", record=current,
            )
            self.assertEqual(r.reasons, [identity.LEGACY_RECORD_SCHEMA])
            # store: append refuses it as legacy-shaped
            with self.assertRaises(schema.SchemaError):
                store.append_rejection_record(store.empty_store(), current)
            # invalidation: skipped as audit-only instead of flagged stale
            self.assertEqual(invalidation.find_directly_stale({"c": current}, ["src/Repositories/ReportRepository.cs"]), [])
        finally:
            schema.is_legacy_shaped = original
        # and with the real definition restored, all three behave normally again
        self.assertTrue(identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR", candidate_evidence_path="src/Repositories/ReportRepository.cs",
            candidate_reachability_path=current["candidateShape"]["reachabilityPath"],
            candidate_trace_confidence="HIGH", record=current,
        ).same_occurrence)
        store.append_rejection_record(store.empty_store(), current)
        self.assertEqual([f.record_id for f in invalidation.find_directly_stale({"c": current}, ["src/Repositories/ReportRepository.cs"])], ["c"])

    def test_legacy_record_is_audit_only_never_reusable(self):
        d = _decide(_legacy_record(), candidate_reachability_path=[
            {"path": "src/Controllers/ReportsController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportsController.Get(int)"},
            {"path": "src/Repositories/ReportRepository.cs", "qualifiedSymbol": "MyApp.Repositories.ReportRepository.FindById(int)"},
        ])
        self.assertFalse(d.reusable)
        self.assertEqual(d.reasons, [eligibility.REASON_RECORD_LEGACY_SCHEMA])


class StrictValidatorFieldTests(unittest.TestCase):
    """Every field that participates in identity / reuse / invalidation /
    status decisions must be a real value, never merely a present key."""

    def _assert_rejected(self, mutate):
        rec = _valid_record()
        mutate(rec)
        with self.assertRaises(schema.SchemaError):
            schema.validate_rejection_record(rec)
        d = _decide(rec)
        self.assertFalse(d.reusable)
        self.assertEqual(d.reasons, [eligibility.REASON_RECORD_SCHEMA_INVALID])
        self.assertTrue(d.detail)

    def test_identity_strings_must_be_nonempty_str(self):
        for field in ("category", "suspicionPattern", "safetyPattern"):
            for bad in (None, "", "   ", 0, 1, [], {}, False):
                with self.subTest(field=field, value=bad):
                    self._assert_rejected(lambda r, f=field, b=bad: r["candidateShape"].__setitem__(f, b))

    def test_qualifiedSymbol_null_blank_numeric_all_rejected_not_legacy(self):
        for bad in (None, "", " \t", 0, 42, 1.5, [], True):
            with self.subTest(value=bad):
                rec = _valid_record()
                rec["candidateShape"]["reachabilityPath"][1]["qualifiedSymbol"] = bad
                self.assertFalse(schema.is_legacy_shaped(rec))
                d = _decide(rec)
                self.assertFalse(d.reusable)
                self.assertEqual(d.reasons, [eligibility.REASON_RECORD_SCHEMA_INVALID])

    def test_other_string_fields_must_be_nonempty_str(self):
        for field in ("recordId", "rejectionReason", "scope"):
            for bad in (None, "", 7):
                with self.subTest(field=field, value=bad):
                    self._assert_rejected(lambda r, f=field, b=bad: r.__setitem__(f, b))
        self._assert_rejected(lambda r: r["evidence"].__setitem__("observation", ""))
        # [Option A, per explicit instruction after Round 5]: `commit` may
        # be null (no-git repositories); an empty string or non-string
        # is still rejected -- see test_round5_closeout.py.
        self._assert_rejected(lambda r: r["lastValidation"].__setitem__("commit", 5))
        self._assert_rejected(lambda r: r["lastValidation"].__setitem__("timestamp", ""))
        self._assert_rejected(lambda r: r.__setitem__("staleReason", ""))

    def test_status_is_an_allowlist(self):
        for bad in ("stale", "ACTIVE", "active", "", None, 0, "STALE ", "REVALIDATED"):
            with self.subTest(value=bad):
                self._assert_rejected(lambda r, b=bad: r.__setitem__("status", b))
        # The only two legal states:
        ok = _valid_record()
        schema.validate_rejection_record(ok)
        ok["status"] = schema.STATUS_STALE
        schema.validate_rejection_record(ok)
        self.assertEqual(_decide(ok).reasons, [eligibility.REASON_RECORD_STALE])

    def test_dependencies_never_defaulted(self):
        self._assert_rejected(lambda r: r.pop("dependencies"))
        for bad in (None, [], "src/x.cs", 5, {"a": 1}):
            with self.subTest(value=bad):
                self._assert_rejected(lambda r, b=bad: r.__setitem__("dependencies", b))
        for bad_entry in (None, 3, "/abs/x.cs", "a/../b.cs", "C:/x.cs", ""):
            with self.subTest(entry=bad_entry):
                self._assert_rejected(lambda r, b=bad_entry: r["dependencies"].append(b))
        # dropping a reachabilityPath file from dependencies is also invalid
        self._assert_rejected(lambda r: r["dependencies"].pop(0))

    def test_reuse_count_and_conditions_never_defaulted(self):
        self._assert_rejected(lambda r: r.pop("reuseCount"))
        self._assert_rejected(lambda r: r.pop("invalidationConditions"))
        for bad in (None, "0", -1, True, 1.0):
            with self.subTest(value=bad):
                self._assert_rejected(lambda r, b=bad: r.__setitem__("reuseCount", b))
        for bad in (None, "cond", [""], [None]):
            with self.subTest(value=bad):
                self._assert_rejected(lambda r, b=bad: r.__setitem__("invalidationConditions", b))


class DecideReuseTrustBoundaryTests(unittest.TestCase):
    def test_round4_reproduction_missing_dependencies_and_bad_status_not_reusable(self):
        """The reviewer's own reproduction: a record with real
        qualifiedSymbols but no `dependencies` and `status: "stale"`
        (wrong case) handed straight to decide_reuse -- previously
        REUSABLE even with the sink in changed_files."""
        rec = {
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
            "status": "stale",
        }
        d = eligibility.decide_reuse(
            record=rec, candidate_category="BOLA/IDOR", candidate_evidence_path="src/R.cs",
            candidate_reachability_path=rec["candidateShape"]["reachabilityPath"],
            candidate_trace_confidence="HIGH", pattern_and_scope_match=True, known_condition_states={},
            changed_files=["src/R.cs"],
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in rec["candidateShape"]["reachabilityPath"]},
        )
        self.assertFalse(d.reusable)
        self.assertEqual(d.reasons, [eligibility.REASON_RECORD_SCHEMA_INVALID])
        self.assertIn("dependencies", d.detail)

    def test_non_mapping_record_is_a_decision_not_an_exception(self):
        for junk in (None, "garbage", 42, [], {}):
            with self.subTest(value=junk):
                d = eligibility.decide_reuse(
                    record=junk, candidate_category="X", candidate_evidence_path="a/b.cs",
                    candidate_reachability_path=[{"path": "a/b.cs", "qualifiedSymbol": "N.T.m"}],
                    candidate_trace_confidence="HIGH", pattern_and_scope_match=True,
                    known_condition_states={}, changed_files=[], hop_controls_confirmed={},
                )
                self.assertFalse(d.reusable)
                self.assertEqual(d.reasons, [eligibility.REASON_RECORD_SCHEMA_INVALID])

    def test_valid_record_still_reusable_control(self):
        d = _decide(_valid_record())
        self.assertTrue(d.reusable, d.reasons)
        self.assertIsNone(d.detail)

    def test_degenerate_category_on_both_sides_never_matches(self):
        for bad in (None, "", 0, False):
            with self.subTest(value=bad):
                rec = _valid_record()
                rec["candidateShape"]["category"] = bad
                r = identity.check_occurrence_identity(
                    candidate_category=bad, candidate_evidence_path="src/Repositories/ReportRepository.cs",
                    candidate_reachability_path=rec["candidateShape"]["reachabilityPath"],
                    candidate_trace_confidence="HIGH", record=rec,
                )
                self.assertFalse(r.same_occurrence)
                self.assertIn(identity.CATEGORY_MISMATCH, r.reasons)
                self.assertFalse(_decide(rec).reusable)

    def test_zero_and_false_categories_are_not_equal(self):
        rec = _valid_record()
        rec["candidateShape"]["category"] = 0
        r = identity.check_occurrence_identity(
            candidate_category=False, candidate_evidence_path="src/Repositories/ReportRepository.cs",
            candidate_reachability_path=rec["candidateShape"]["reachabilityPath"],
            candidate_trace_confidence="HIGH", record=rec,
        )
        self.assertFalse(r.same_occurrence)


class StoreEntryPointTests(TempRepo):
    def _broken(self):
        rec = _valid_record("broken")
        del rec["dependencies"]
        return rec

    def test_append_rejects_malformed_current_record(self):
        s = store.empty_store()
        with self.assertRaises(schema.SchemaError):
            store.append_rejection_record(s, self._broken())
        self.assertEqual(s["rejectionRecords"], {})

    def test_append_rejects_legacy_shaped_record(self):
        s = store.empty_store()
        with self.assertRaises(schema.SchemaError):
            store.append_rejection_record(s, _legacy_record())

    def test_append_rejects_malformed_miss_record(self):
        s = store.empty_store()
        with self.assertRaises(schema.SchemaError):
            store.append_miss_record(s, {"recordId": "m", "recordType": schema.RECORD_TYPE_MISS, "layer": "routing"})

    def test_replace_rejects_malformed_and_legacy(self):
        s = store.empty_store()
        store.append_rejection_record(s, _valid_record("r1"))
        with self.assertRaises(schema.SchemaError):
            store.replace_rejection_record(s, "r1", dict(self._broken(), recordId="r1"))
        with self.assertRaises(schema.SchemaError):
            store.replace_rejection_record(s, "r1", _legacy_record("r1"))
        # untouched
        schema.validate_rejection_record(s["rejectionRecords"]["r1"])

    def test_write_refuses_a_store_holding_an_invalid_current_record(self):
        s = store.empty_store()
        s["rejectionRecords"]["broken"] = self._broken()  # bypassing append on purpose
        with self.assertRaises(store.StoreError):
            store.write(self.path, s, repo_root=self.repo_root, expected_on_disk_hash=None, git_commit=None)
        self.assertFalse(os.path.exists(self.path))

    def test_write_still_accepts_legacy_records_loaded_from_disk(self):
        s = store.empty_store()
        s["schemaVersion"] = schema.LEGACY_SCHEMA_VERSION
        s["rejectionRecords"]["legacy1"] = _legacy_record()
        self._write_raw(s)
        loaded = store.load(self.path, repo_root=self.repo_root)
        self.assertTrue(loaded.ok)
        store.write(self.path, loaded.store, repo_root=self.repo_root, expected_on_disk_hash=loaded.on_disk_hash, git_commit=None)
        again = store.load(self.path, repo_root=self.repo_root)
        self.assertTrue(again.ok)
        self.assertTrue(again.has_legacy_records)

    def test_load_degrades_on_present_but_invalid_qualifiedSymbol_never_legacy(self):
        for bad in (None, "", 123):
            with self.subTest(value=bad):
                rec = _valid_record()
                rec["candidateShape"]["reachabilityPath"][0]["qualifiedSymbol"] = bad
                for tag in (schema.SCHEMA_VERSION, schema.LEGACY_SCHEMA_VERSION):
                    s = store.empty_store()
                    s["schemaVersion"] = tag
                    s["rejectionRecords"]["r1"] = rec
                    self._write_raw(s)
                    result = store.load(self.path, repo_root=self.repo_root)
                    self.assertFalse(result.ok, f"tag={tag} value={bad!r} must degrade, not load as legacy")
                    self.assertTrue(result.degraded)

    def test_load_degrades_on_unknown_status_missing_or_null_dependencies(self):
        mutations = {
            "status": lambda r: r.__setitem__("status", "ACTIVE"),
            "missing_deps": lambda r: r.pop("dependencies"),
            "null_deps": lambda r: r.__setitem__("dependencies", None),
            "bad_dep_path": lambda r: r["dependencies"].append("C:/abs.cs"),
        }
        for name, mutate in mutations.items():
            with self.subTest(case=name):
                rec = _valid_record()
                mutate(rec)
                s = store.empty_store()
                s["rejectionRecords"]["r1"] = rec
                self._write_raw(s)
                result = store.load(self.path, repo_root=self.repo_root)
                self.assertFalse(result.ok)

    def test_deeply_nested_json_degrades_instead_of_crashing(self):
        depth = 200000
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("[" * depth + "]" * depth)
        result = store.load(self.path, repo_root=self.repo_root)  # must not raise
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)
        self.assertIn("deep", result.reason)


class PathSemanticsConsistencyTests(unittest.TestCase):
    """identity, eligibility check (c), hop_key, direct and central
    invalidation all go through paths.canonical -- prove it with the
    same Src/File.cs vs src/file.cs pair at every layer."""

    def _rec(self):
        return _valid_record(
            reachability_path=[{"path": "Src/File.cs", "qualifiedSymbol": "Ns.File.Do(int)"}],
            evidence={"path": "Src/File.cs", "observation": "o"},
        )

    def test_check_c_sees_case_variant_as_changed(self):
        d = eligibility.decide_reuse(
            record=self._rec(), candidate_category="BOLA/IDOR", candidate_evidence_path="src/file.cs",
            candidate_reachability_path=[{"path": "src/file.cs", "qualifiedSymbol": "Ns.File.Do(int)"}],
            candidate_trace_confidence="HIGH", pattern_and_scope_match=True, known_condition_states={},
            changed_files=["src/file.cs"],
            hop_controls_confirmed={eligibility.hop_key("SRC/FILE.CS", "Ns.File.Do(int)"): True},
        )
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_DEPENDENCY_CHANGED, d.reasons)
        # and (d) accepted the differently-cased hop key -- same rule
        self.assertNotIn(eligibility.REASON_HOP_CONTROL_NOT_CONFIRMED, d.reasons)

    def test_identity_uses_the_same_rule(self):
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR", candidate_evidence_path="src/file.cs",
            candidate_reachability_path=[{"path": "src/file.cs", "qualifiedSymbol": "Ns.File.Do(int)"}],
            candidate_trace_confidence="HIGH", record=self._rec(),
        )
        self.assertTrue(r.same_occurrence)

    def test_direct_and_central_invalidation_use_the_same_rule(self):
        records = {"r1": self._rec()}
        self.assertEqual([f.record_id for f in invalidation.find_directly_stale(records, ["src/file.cs"])], ["r1"])
        self.assertEqual(
            [f.record_id for f in invalidation.find_central_component_stale(records, central_component_file="x", affected_path_prefixes=["SRC"])],
            ["r1"],
        )
        # negative controls
        self.assertEqual(invalidation.find_directly_stale(records, ["src/other.cs"]), [])
        self.assertEqual(invalidation.find_central_component_stale(records, central_component_file="x", affected_path_prefixes=["lib"]), [])

    def test_no_module_compares_paths_with_bare_equality_on_validate(self):
        # Every comparison must be via canonical()/same_path(); a
        # regression to `paths.validate(a) == paths.validate(b)` would
        # silently reintroduce case sensitivity in one place only.
        import ast
        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        offenders = []
        for fname in ("eligibility.py", "identity.py", "invalidation.py"):
            with open(os.path.join(pkg_dir, fname), encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=fname)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "paths" and node.func.attr in ("validate", "normalize"):
                        offenders.append((fname, node.lineno))
        self.assertEqual(offenders, [], "compare via paths.canonical/same_path only")


class CentralInvalidationRobustnessTests(unittest.TestCase):
    def test_one_malformed_record_does_not_stop_central_scan(self):
        good = _valid_record("good", reachability_path=[{"path": "auth/Handler.cs", "qualifiedSymbol": "Ns.Handler.Do"}],
                             evidence={"path": "auth/Handler.cs", "observation": "o"})
        for bad_deps in (None, 5, ["../x.cs"], [None]):
            with self.subTest(deps=bad_deps):
                bad = _valid_record("bad", reachability_path=[{"path": "auth/Other.cs", "qualifiedSymbol": "Ns.Other.Do"}],
                                    evidence={"path": "auth/Other.cs", "observation": "o"})
                bad["dependencies"] = bad_deps
                findings = invalidation.find_central_component_stale(
                    {"bad": bad, "good": good}, central_component_file="auth/Boot.cs", affected_path_prefixes=["auth"],
                )
                by_id = {f.record_id: f.reason for f in findings}
                self.assertEqual(by_id, {"bad": invalidation.REASON_RECORD_MALFORMED, "good": invalidation.REASON_CENTRAL_COMPONENT})


class LockPollingTests(unittest.TestCase):
    def test_unremovable_stale_lock_polls_instead_of_busy_looping(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "feedback.json")
            lock = store._lock_path_for(path)
            open(lock, "w").close()
            stale = __import__("time").time() - (store.LOCK_STALE_SECONDS + 5)
            os.utime(lock, (stale, stale))
            sleeps = []
            real_sleep = __import__("time").sleep

            def counting_sleep(s):
                sleeps.append(s)
                real_sleep(s)

            with unittest.mock.patch("os.remove", side_effect=OSError("denied")), \
                 unittest.mock.patch("time.sleep", side_effect=counting_sleep):
                with self.assertRaises(store.LockTimeoutError) as ctx:
                    store._acquire_lock(path, timeout=0.3)
            self.assertGreater(len(sleeps), 0, "stale-lock branch must poll, not spin")
            self.assertLess(len(sleeps), 50, "a 0.3s wait at the poll interval is a handful of iterations, not hundreds")
            self.assertIn("could not be removed", str(ctx.exception))
            os.remove(lock)

    def test_persistent_permission_error_without_lockfile_names_the_real_cause(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "feedback.json")
            with unittest.mock.patch("os.open", side_effect=PermissionError("denied")):
                with self.assertRaises(store.LockTimeoutError) as ctx:
                    store._acquire_lock(path, timeout=0.2)
            self.assertIn("no lock file exists", str(ctx.exception))
            self.assertNotIn("appears to be active", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
