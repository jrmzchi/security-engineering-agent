from __future__ import annotations

import unittest

from .. import invalidation, schema


def _record(record_id, category, reachability_path):
    return schema.new_rejection_record(
        record_id=record_id,
        category=category,
        suspicion_pattern="p",
        safety_pattern="s",
        reachability_path=reachability_path,
        rejection_reason="r",
        evidence={"path": reachability_path[-1]["path"], "observation": "o"},
        scope="scope",
        trace_confidence="HIGH",
        last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
    )


class DirectlyStaleTests(unittest.TestCase):
    def test_matching_dependency_marks_stale(self):
        records = {
            "r1": _record("r1", "SQLi", [
                {"path": "a/Service.cs", "qualifiedSymbol": "Service.Search"},
                {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindByNameLike"},
            ]),
        }
        findings = invalidation.find_directly_stale(records, ["a/Repository.cs"])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].record_id, "r1")
        self.assertEqual(findings[0].reason, invalidation.REASON_DIRECT_DEPENDENCY)

    def test_unrelated_changed_file_does_not_mark_stale(self):
        records = {
            "r1": _record("r1", "SQLi", [
                {"path": "a/Service.cs", "qualifiedSymbol": "Service.Search"},
                {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindByNameLike"},
            ]),
        }
        findings = invalidation.find_directly_stale(records, ["b/Unrelated.cs"])
        self.assertEqual(findings, [])

    def test_only_matching_records_affected_others_untouched(self):
        records = {
            "r1": _record("r1", "SQLi", [{"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindByNameLike"}]),
            "r2": _record("r2", "BOLA", [{"path": "b/Repository.cs", "qualifiedSymbol": "Repository.FindById"}]),
        }
        findings = invalidation.find_directly_stale(records, ["a/Repository.cs"])
        self.assertEqual([f.record_id for f in findings], ["r1"])

    def _malformed_current(self, record_id, **overrides):
        # A CURRENT-shaped record (has qualifiedSymbol) with broken data.
        rec = {
            "recordId": record_id,
            "candidateShape": {"category": "X", "reachabilityPath": [{"path": "b/File.cs", "qualifiedSymbol": "File.Do"}]},
            "dependencies": ["C:/absolute/leftover.cs"],
        }
        rec.update(overrides)
        return rec

    def test_one_records_malformed_dependency_does_not_abort_scanning_others(self):
        """[ADDED, per a Round 3 Nit; REVISED per explicit instruction
        closing Round 4 findings]: a record's OWN malformed data must
        neither abort the scan of every other record NOR be silently
        skipped -- it is reported as RECORD_MALFORMED_NEEDS_REVALIDATION
        for that record only, with a diagnostic, while the genuinely
        stale record alongside it is still found."""
        records = {
            "good": _record("good", "SQLi", [{"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindByNameLike"}]),
            "malformed": self._malformed_current("malformed"),
        }
        findings = invalidation.find_directly_stale(records, ["a/Repository.cs"])
        by_id = {f.record_id: f for f in findings}
        self.assertEqual(set(by_id), {"good", "malformed"})
        self.assertEqual(by_id["good"].reason, invalidation.REASON_DIRECT_DEPENDENCY)
        self.assertEqual(by_id["malformed"].reason, invalidation.REASON_RECORD_MALFORMED)
        self.assertIn("dependencies[0]", by_id["malformed"].detail)

    def test_every_malformed_dependencies_shape_is_reported_not_raised(self):
        """`dependencies: null`, missing, a non-list, a list with a
        non-string, a list with an invalid path -- none may escape as
        TypeError/InvalidPathError; each is a MALFORMED finding with the
        reason preserved, and the good record is still evaluated."""
        good = _record("good", "SQLi", [{"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindByNameLike"}])
        shapes = {
            "null": {"dependencies": None},
            "int": {"dependencies": 5},
            "str": {"dependencies": "a/Repository.cs"},
            "non_str_entry": {"dependencies": ["a/Repository.cs", None]},
            "bad_path_entry": {"dependencies": ["../escape.cs"]},
        }
        for name, override in shapes.items():
            with self.subTest(shape=name):
                bad = self._malformed_current("bad", **override)
                findings = invalidation.find_directly_stale({"good": good, "bad": bad}, ["a/Repository.cs"])
                by_id = {f.record_id: f for f in findings}
                self.assertEqual(by_id["good"].reason, invalidation.REASON_DIRECT_DEPENDENCY)
                self.assertEqual(by_id["bad"].reason, invalidation.REASON_RECORD_MALFORMED)
                self.assertTrue(by_id["bad"].detail)
        # missing key entirely
        bad = self._malformed_current("bad")
        del bad["dependencies"]
        findings = invalidation.find_directly_stale({"good": good, "bad": bad}, ["a/Repository.cs"])
        self.assertEqual({f.record_id: f.reason for f in findings},
                         {"good": invalidation.REASON_DIRECT_DEPENDENCY, "bad": invalidation.REASON_RECORD_MALFORMED})

    def test_legacy_record_is_skipped_not_reported_malformed(self):
        # A genuine v1 record (no qualifiedSymbol key) is audit-only and
        # can never be reused regardless of status -- it is neither a
        # stale finding nor a malformed one here.
        legacy = {
            "recordId": "legacy",
            "candidateShape": {"category": "X", "reachabilityPath": [{"path": "a/Repository.cs", "symbol": "Find"}]},
        }
        findings = invalidation.find_directly_stale({"legacy": legacy}, ["a/Repository.cs"])
        self.assertEqual(findings, [])

    def test_case_difference_between_record_and_diff_still_invalidates(self):
        """[ADDED, per explicit instruction]: `Src/File.cs` recorded,
        `src/file.cs` reported by the diff (or vice versa) -- must be
        seen as the same file changing. Both directions."""
        rec = _record("r1", "SQLi", [{"path": "Src/File.cs", "qualifiedSymbol": "Ns.File.Do"}])
        self.assertEqual([f.record_id for f in invalidation.find_directly_stale({"r1": rec}, ["src/file.cs"])], ["r1"])
        rec2 = _record("r2", "SQLi", [{"path": "src/file.cs", "qualifiedSymbol": "Ns.File.Do"}])
        self.assertEqual([f.record_id for f in invalidation.find_directly_stale({"r2": rec2}, ["Src/File.cs"])], ["r2"])
        # Negative control: a genuinely different file still does not.
        self.assertEqual(invalidation.find_directly_stale({"r1": rec}, ["src/other.cs"]), [])

    def test_changed_files_argument_still_raises_loudly_on_malformed_entry(self):
        # Control case: the fix above must not have weakened the
        # round-2 fix for the CALLER's own argument -- that must still
        # raise, not silently skip.
        records = {"r1": _record("r1", "SQLi", [{"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindByNameLike"}])}
        with self.assertRaises(invalidation.paths.InvalidPathError):
            invalidation.find_directly_stale(records, ["C:/absolute/changed.cs"])


class CentralComponentTests(unittest.TestCase):
    def test_bounded_by_explicit_category(self):
        records = {
            "auth1": _record("auth1", "session fixation", [{"path": "auth/SessionHelper.cs", "qualifiedSymbol": "SessionHelper.Issue"}]),
            "other": _record("other", "SQLi", [{"path": "b/Repository.cs", "qualifiedSymbol": "Repository.Find"}]),
        }
        findings = invalidation.find_central_component_stale(
            records,
            central_component_file="Program.cs",
            affected_categories=["session fixation"],
        )
        self.assertEqual([f.record_id for f in findings], ["auth1"])
        self.assertEqual(findings[0].reason, invalidation.REASON_CENTRAL_COMPONENT)

    def test_bounded_by_explicit_path_prefix(self):
        records = {
            "a": _record("a", "X", [{"path": "shared/auth/Middleware.cs", "qualifiedSymbol": "Middleware.Invoke"}]),
            "b": _record("b", "Y", [{"path": "unrelated/Other.cs", "qualifiedSymbol": "Other.Do"}]),
        }
        findings = invalidation.find_central_component_stale(
            records,
            central_component_file="shared/auth/Middleware.cs",
            affected_path_prefixes=["shared/auth"],
        )
        self.assertEqual([f.record_id for f in findings], ["a"])

    def test_empty_scope_invalidates_nothing_not_everything(self):
        records = {
            "a": _record("a", "X", [{"path": "any/File.cs", "qualifiedSymbol": "File.Do"}]),
        }
        findings = invalidation.find_central_component_stale(records, central_component_file="Program.cs")
        self.assertEqual(findings, [])

    def test_never_invalidates_the_whole_store_by_accident(self):
        # A caller passing a broad prefix must only match what that
        # prefix actually contains, never records outside it.
        records = {
            "in_scope": _record("in_scope", "X", [{"path": "auth/Handler.cs", "qualifiedSymbol": "Handler.Do"}]),
            "out_of_scope": _record("out_of_scope", "Y", [{"path": "billing/Invoice.cs", "qualifiedSymbol": "Invoice.Do"}]),
        }
        findings = invalidation.find_central_component_stale(
            records, central_component_file="auth/Bootstrap.cs", affected_path_prefixes=["auth"],
        )
        self.assertEqual([f.record_id for f in findings], ["in_scope"])


class CentralComponentPrefixValidationTests(unittest.TestCase):
    def test_malformed_prefix_raises_not_silently_matches_nothing(self):
        """[ADDED, per a round-1 independent review Minor]: an absolute
        or otherwise malformed prefix previously matched zero records
        silently -- fail-open for a caller who actually intended a
        real, bounded scope."""
        records = {"a": _record("a", "X", [{"path": "auth/Handler.cs", "qualifiedSymbol": "Handler.Do"}])}
        with self.assertRaises(invalidation.paths.InvalidPathError):
            invalidation.find_central_component_stale(
                records, central_component_file="x", affected_path_prefixes=["C:/repo/a"],
            )
        with self.assertRaises(invalidation.paths.InvalidPathError):
            invalidation.find_central_component_stale(
                records, central_component_file="x", affected_path_prefixes=["a/../b"],
            )


class NonFileConditionTests(unittest.TestCase):
    def test_confirmed_true_condition_marks_stale(self):
        findings = invalidation.resolve_non_file_conditions(
            {"r1": ["EF Core version bump"]},
            {"EF Core version bump": True},
        )
        self.assertEqual([f.record_id for f in findings], ["r1"])

    def test_unknown_condition_marks_stale_fail_closed(self):
        findings = invalidation.resolve_non_file_conditions(
            {"r1": ["feature flag X enabled"]},
            {},
        )
        self.assertEqual([f.record_id for f in findings], ["r1"])

    def test_string_state_fails_closed_not_treated_as_false(self):
        """[ADDED, per a round-1 independent review Major]"""
        for sneaky_value in ("UNKNOWN", "true", "False", 1):
            with self.subTest(value=sneaky_value):
                findings = invalidation.resolve_non_file_conditions(
                    {"r1": ["feature flag X enabled"]},
                    {"feature flag X enabled": sneaky_value},
                )
                self.assertEqual([f.record_id for f in findings], ["r1"])

    def test_confirmed_false_condition_does_not_mark_stale(self):
        findings = invalidation.resolve_non_file_conditions(
            {"r1": ["feature flag X enabled"]},
            {"feature flag X enabled": False},
        )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
