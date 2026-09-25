from __future__ import annotations

import unittest

from .. import identity, schema


def _record():
    return schema.new_rejection_record(
        record_id="r1",
        category="BOLA/IDOR",
        suspicion_pattern="object reference from caller-supplied ID",
        safety_pattern="ownership check enforced",
        reachability_path=[
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"},
            {"path": "a/Service.cs", "qualifiedSymbol": "Service.Get"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ],
        rejection_reason="ownership check present",
        evidence={"path": "a/Repository.cs", "observation": "no check at sink, enforced upstream"},
        scope="this path only",
        trace_confidence="HIGH",
        last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
    )


class IdentityTests(unittest.TestCase):
    def _same_path(self):
        return [
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"},
            {"path": "a/Service.cs", "qualifiedSymbol": "Service.Get"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ]

    def test_same_occurrence(self):
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=self._same_path(),
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertTrue(r.same_occurrence)
        self.assertEqual(r.reasons, [identity.SAME_OCCURRENCE])

    def test_category_mismatch_is_different_occurrence(self):
        r = identity.check_occurrence_identity(
            candidate_category="tenant isolation bypass",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=self._same_path(),
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.CATEGORY_MISMATCH, r.reasons)

    def test_sink_mismatch(self):
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/OtherRepository.cs",
            candidate_reachability_path=self._same_path(),
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.SINK_MISMATCH, r.reasons)

    def test_new_caller_different_path_same_sink(self):
        new_path = [
            {"path": "a/NewJob.cs", "qualifiedSymbol": "NewJob.Handle"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=new_path,
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, r.reasons)

    def test_same_files_different_symbols(self):
        new_path = [
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.GetExport"},
            {"path": "a/Service.cs", "qualifiedSymbol": "Service.GetForExport"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=new_path,
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, r.reasons)

    def test_missing_hop_is_different_occurrence(self):
        shorter = [
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=shorter,
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, r.reasons)

    def test_low_confidence_candidate_trace_never_matches(self):
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=self._same_path(),
            candidate_trace_confidence="LOW",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.CANDIDATE_TRACE_NOT_HIGH_CONFIDENCE, r.reasons)

    def test_malformed_candidate_path_fails_closed_not_raises(self):
        bad_path = [{"path": "/etc/passwd", "qualifiedSymbol": "x"}]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=bad_path,
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)

    def test_extra_hop_is_different_occurrence(self):
        """[ADDED, per the qualifiedSymbol redesign's required test
        matrix]: an ordered-path variation the existing missing-hop test
        doesn't cover -- one EXTRA hop inserted, everything else
        identical. Must not match (same reasoning as the missing-hop
        case: length must match exactly)."""
        longer = self._same_path() + [{"path": "a/Extra.cs", "qualifiedSymbol": "Extra.Step"}]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=longer,
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, r.reasons)


class QualifiedSymbolCollisionTests(unittest.TestCase):
    """[ADDED, per explicit instruction for the qualifiedSymbol
    redesign]: the two concrete counterexamples that motivated it -- a
    C# overload collision (same enclosing type and method name,
    different parameter signature) and a Python two-classes-same-method
    collision (same method name and signature, different enclosing
    class) -- must never be treated as the same occurrence."""

    def _csharp_record(self):
        return schema.new_rejection_record(
            record_id="cs1",
            category="BOLA/IDOR",
            suspicion_pattern="object reference from caller-supplied ID",
            safety_pattern="ownership check enforced",
            reachability_path=[
                {"path": "a/ReportController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportController.Get(int)"},
                {"path": "a/Repository.cs", "qualifiedSymbol": "MyApp.Data.Repository.FindById"},
            ],
            rejection_reason="ownership check present",
            evidence={"path": "a/Repository.cs", "observation": "no check at sink, enforced upstream"},
            scope="this path only",
            trace_confidence="HIGH",
            last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
        )

    def test_csharp_overload_with_different_signature_does_not_match(self):
        different_overload = [
            {"path": "a/ReportController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportController.Get(string)"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "MyApp.Data.Repository.FindById"},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=different_overload,
            candidate_trace_confidence="HIGH",
            record=self._csharp_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, r.reasons)

    def test_csharp_overload_with_same_signature_does_match(self):
        # Control case: proves the mismatch above is really about the
        # signature, not some unrelated difference.
        same_overload = [
            {"path": "a/ReportController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportController.Get(int)"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "MyApp.Data.Repository.FindById"},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=same_overload,
            candidate_trace_confidence="HIGH",
            record=self._csharp_record(),
        )
        self.assertTrue(r.same_occurrence)

    def _python_record(self):
        return schema.new_rejection_record(
            record_id="py1",
            category="BOLA/IDOR",
            suspicion_pattern="object reference from caller-supplied ID",
            safety_pattern="ownership check enforced",
            reachability_path=[
                {"path": "app/views.py", "qualifiedSymbol": "app.views.ClassA.get_report"},
                {"path": "app/repo.py", "qualifiedSymbol": "app.repo.Repository.find_by_id"},
            ],
            rejection_reason="ownership check present",
            evidence={"path": "app/repo.py", "observation": "no check at sink, enforced upstream"},
            scope="this path only",
            trace_confidence="HIGH",
            last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
        )

    def test_python_different_class_same_method_name_does_not_match(self):
        different_class = [
            {"path": "app/views.py", "qualifiedSymbol": "app.views.ClassB.get_report"},
            {"path": "app/repo.py", "qualifiedSymbol": "app.repo.Repository.find_by_id"},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="app/repo.py",
            candidate_reachability_path=different_class,
            candidate_trace_confidence="HIGH",
            record=self._python_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, r.reasons)


class LineRangeIdentityTests(unittest.TestCase):
    """[ADDED, per explicit instruction]: `lineRange` is evidence-
    location/diagnostic metadata only and must never be part of
    occurrence identity -- a pure line shift (e.g. a comment added
    above a hop) must never by itself change the identity result."""

    def test_lineRange_shift_alone_does_not_change_identity(self):
        record = schema.new_rejection_record(
            record_id="lr1", category="BOLA/IDOR",
            suspicion_pattern="p", safety_pattern="s",
            reachability_path=[
                {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get", "lineRange": {"start": 10, "end": 12}},
                {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById", "lineRange": {"start": 40, "end": 44}},
            ],
            rejection_reason="r",
            evidence={"path": "a/Repository.cs", "observation": "o"},
            scope="scope", trace_confidence="HIGH",
            last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
        )
        shifted = [
            # Same path, same qualifiedSymbol, lineRange shifted by +5
            # (as if a comment were inserted above this hop).
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get", "lineRange": {"start": 15, "end": 17}},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById", "lineRange": {"start": 40, "end": 44}},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=shifted,
            candidate_trace_confidence="HIGH",
            record=record,
        )
        self.assertTrue(r.same_occurrence)

    def test_missing_lineRange_on_either_side_still_matches(self):
        # lineRange is optional -- its absence must not itself break a
        # match when path/qualifiedSymbol are otherwise identical.
        record = schema.new_rejection_record(
            record_id="lr2", category="BOLA/IDOR",
            suspicion_pattern="p", safety_pattern="s",
            reachability_path=[{"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get", "lineRange": {"start": 10, "end": 12}}],
            rejection_reason="r",
            evidence={"path": "a/Controller.cs", "observation": "o"},
            scope="scope", trace_confidence="HIGH",
            last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
        )
        no_line_range = [{"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"}]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Controller.cs",
            candidate_reachability_path=no_line_range,
            candidate_trace_confidence="HIGH",
            record=record,
        )
        self.assertTrue(r.same_occurrence)


class MissingOrAmbiguousCandidateSymbolTests(unittest.TestCase):
    """[ADDED, per explicit instruction]: a candidate hop with a
    missing, `None`, or empty `qualifiedSymbol` must never match an
    existing record -- it fails closed to full independent validation,
    the same outcome as any other identity mismatch, never a crash."""

    def test_candidate_hop_missing_qualifiedSymbol_key_does_not_match(self):
        candidate = [{"path": "a/Controller.cs"}, {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"}]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=candidate,
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertIn(identity.REACHABILITY_PATH_MISMATCH, r.reasons)

    def test_candidate_hop_with_none_qualifiedSymbol_does_not_match(self):
        candidate = [
            {"path": "a/Controller.cs", "qualifiedSymbol": None},
            {"path": "a/Service.cs", "qualifiedSymbol": "Service.Get"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=candidate,
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)

    def test_candidate_hop_with_empty_qualifiedSymbol_does_not_match(self):
        candidate = [
            {"path": "a/Controller.cs", "qualifiedSymbol": ""},
            {"path": "a/Service.cs", "qualifiedSymbol": "Service.Get"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=candidate,
            candidate_trace_confidence="HIGH",
            record=_record(),
        )
        self.assertFalse(r.same_occurrence)


class LegacySchemaRecordTests(unittest.TestCase):
    """[ADDED, per explicit instruction for the schema-version-2
    migration]: a record built under schema version 1 (bare `symbol`
    hops, no `qualifiedSymbol` at all) must NEVER be matched for reuse
    -- not even when the candidate's sink, category, and path would
    otherwise be a perfect match -- because there is no reliable way to
    know the old bare name was actually unambiguous. This is checked at
    the RECORD level (any hop missing `qualifiedSymbol`), not by
    trusting the store's own claimed schemaVersion tag."""

    def _legacy_record(self):
        # Hand-built: a genuine v1 store would have produced exactly
        # this shape (bare "symbol" keys, no "qualifiedSymbol" at all).
        # Built by hand here (bypassing schema.new_rejection_record,
        # which now refuses to construct this shape at all) specifically
        # to prove the identity guard catches it regardless of how it
        # got loaded.
        return {
            "recordType": "feedback_rejection",
            "recordId": "legacy1",
            "candidateShape": {
                "category": "BOLA/IDOR",
                "reachabilityPath": [
                    {"path": "a/Controller.cs", "symbol": "Get"},
                    {"path": "a/Repository.cs", "symbol": "FindById"},
                ],
            },
            "evidence": {"path": "a/Repository.cs", "observation": "o"},
        }

    def test_legacy_record_never_matches_even_a_perfect_looking_candidate(self):
        candidate = [
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
        ]
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=candidate,
            candidate_trace_confidence="HIGH",
            record=self._legacy_record(),
        )
        self.assertFalse(r.same_occurrence)
        self.assertEqual(r.reasons, [identity.LEGACY_RECORD_SCHEMA])

    def test_legacy_record_with_only_one_hop_missing_qualifiedSymbol_still_refused(self):
        # Only ONE hop lacks qualifiedSymbol (the other was somehow
        # migrated by hand) -- must still be treated as legacy in full,
        # not partially trusted.
        mixed = self._legacy_record()
        mixed["candidateShape"]["reachabilityPath"][1] = {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"}
        r = identity.check_occurrence_identity(
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=[
                {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get"},
                {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById"},
            ],
            candidate_trace_confidence="HIGH",
            record=mixed,
        )
        self.assertFalse(r.same_occurrence)
        self.assertEqual(r.reasons, [identity.LEGACY_RECORD_SCHEMA])


if __name__ == "__main__":
    unittest.main()
