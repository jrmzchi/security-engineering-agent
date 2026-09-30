from __future__ import annotations

import unittest

from .. import eligibility, schema


def _record(**overrides):
    kwargs = dict(
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
    kwargs.update(overrides)
    return schema.new_rejection_record(**kwargs)


def _all_hops_confirmed(record):
    return {
        eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True
        for e in record["candidateShape"]["reachabilityPath"]
    }


def _decide(record, **overrides):
    kwargs = dict(
        record=record,
        candidate_category=record["candidateShape"]["category"],
        candidate_evidence_path=record["evidence"]["path"],
        candidate_reachability_path=record["candidateShape"]["reachabilityPath"],
        candidate_trace_confidence="HIGH",
        pattern_and_scope_match=True,
        known_condition_states={},
        changed_files=[],
        hop_controls_confirmed=_all_hops_confirmed(record),
    )
    kwargs.update(overrides)
    return eligibility.decide_reuse(**kwargs)


class DecideReuseTests(unittest.TestCase):
    def test_all_pass_is_reusable(self):
        d = _decide(_record())
        self.assertTrue(d.reusable)
        self.assertEqual(d.reasons, [])

    def test_stale_record_never_reusable_identity_never_checked(self):
        rec = _record()
        rec["status"] = "STALE"
        d = _decide(rec)
        self.assertFalse(d.reusable)
        self.assertEqual(d.reasons, [eligibility.REASON_RECORD_STALE])
        self.assertIsNone(d.identity_result)

    def test_different_occurrence_never_reaches_a_d(self):
        rec = _record()
        d = _decide(rec, candidate_category="something else entirely")
        self.assertFalse(d.reusable)
        self.assertIn("CATEGORY_MISMATCH", d.reasons)
        # none of (a)-(d)'s reason codes should appear -- they never ran
        for r in (eligibility.REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED, eligibility.REASON_DEPENDENCY_CHANGED,
                  eligibility.REASON_HOP_CONTROL_NOT_CONFIRMED, eligibility.REASON_INVALIDATION_CONDITION_TRUE):
            self.assertNotIn(r, d.reasons)

    def test_check_a_fails_on_none_verdict(self):
        d = _decide(_record(), pattern_and_scope_match=None)
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED, d.reasons)

    def test_check_a_fails_on_false_verdict(self):
        d = _decide(_record(), pattern_and_scope_match=False)
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED, d.reasons)

    def test_check_b_fails_when_condition_true(self):
        rec = _record(invalidation_conditions=["EF Core package version changes"])
        d = _decide(rec, known_condition_states={"EF Core package version changes": True})
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_INVALIDATION_CONDITION_TRUE, d.reasons)

    def test_check_b_fails_closed_when_condition_unknown(self):
        rec = _record(invalidation_conditions=["EF Core package version changes"])
        d = _decide(rec, known_condition_states={})  # condition present on record, no state supplied
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_INVALIDATION_CONDITION_UNKNOWN, d.reasons)

    def test_check_b_fails_closed_on_a_string_that_is_not_the_bool_false(self):
        """[ADDED, per a round-1 independent review Major] previously,
        any value other than the literal `True`/`None` (e.g. the
        string "UNKNOWN", which plays/finding-validation.md itself
        uses as prose for this exact state) silently fell through as
        "confirmed false" -- fail-open. Only the exact bool `False` may
        now count as safe."""
        rec = _record(invalidation_conditions=["EF Core package version changes"])
        for sneaky_value in ("UNKNOWN", "true", "false", 1, 0, "False", {}):
            with self.subTest(value=sneaky_value):
                d = _decide(rec, known_condition_states={"EF Core package version changes": sneaky_value})
                self.assertFalse(d.reusable)
                self.assertIn(eligibility.REASON_INVALIDATION_CONDITION_UNKNOWN, d.reasons)

    def test_check_b_passes_when_condition_confirmed_false(self):
        rec = _record(invalidation_conditions=["EF Core package version changes"])
        d = _decide(rec, known_condition_states={"EF Core package version changes": False})
        self.assertTrue(d.reusable)

    def test_check_c_fails_when_dependency_changed(self):
        d = _decide(_record(), changed_files=["a/Service.cs"])
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_DEPENDENCY_CHANGED, d.reasons)

    def test_check_c_raises_on_bare_string_changed_files(self):
        """[ADDED, per a round-2 independent review Major]: passing a
        bare string instead of a list used to iterate it
        character-by-character and silently fail open (no character
        matches a real path, so the check always "passed")."""
        with self.assertRaises(TypeError):
            _decide(_record(), changed_files="a/Repository.cs")

    def test_check_c_raises_on_malformed_changed_file_entry(self):
        """[ADDED, per a round-2 independent review Major]: a malformed
        entry (absolute path) in changed_files used to be silently
        skipped instead of raising -- fail-open for a caller whose diff
        tooling handed it an unexpected path shape."""
        with self.assertRaises(Exception):
            _decide(_record(), changed_files=["/etc/passwd"])

    def test_check_c_ignores_unrelated_changed_files(self):
        d = _decide(_record(), changed_files=["unrelated/File.cs"])
        self.assertTrue(d.reusable)

    def test_check_d_fails_when_a_hop_not_confirmed(self):
        rec = _record()
        confirmed = _all_hops_confirmed(rec)
        # Drop confirmation for the middle hop only.
        middle = eligibility.hop_key("a/Service.cs", "Service.Get")
        del confirmed[middle]
        d = _decide(rec, hop_controls_confirmed=confirmed)
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_HOP_CONTROL_NOT_CONFIRMED, d.reasons)

    def test_all_four_checks_always_evaluated_not_short_circuited(self):
        # (a) and (b) both fail; (c) and (d) must ALSO be reported even
        # though (a)/(b) already failed -- per explicit instruction not
        # to skip evaluating the remaining checks.
        rec = _record(invalidation_conditions=["EF Core package version changes"])
        d = _decide(
            rec,
            pattern_and_scope_match=False,
            known_condition_states={"EF Core package version changes": True},
            changed_files=["a/Repository.cs"],
            hop_controls_confirmed={},
        )
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED, d.reasons)
        self.assertIn(eligibility.REASON_INVALIDATION_CONDITION_TRUE, d.reasons)
        self.assertIn(eligibility.REASON_DEPENDENCY_CHANGED, d.reasons)
        self.assertIn(eligibility.REASON_HOP_CONTROL_NOT_CONFIRMED, d.reasons)

    def test_reuse_count_threshold_forces_full_rederivation(self):
        rec = _record(reuse_count=eligibility.REUSE_COUNT_THRESHOLD)
        d = _decide(rec)
        self.assertFalse(d.reusable)
        self.assertIn(eligibility.REASON_REUSE_COUNT_THRESHOLD_HIT, d.reasons)

    def test_reuse_count_below_threshold_does_not_trigger(self):
        rec = _record(reuse_count=eligibility.REUSE_COUNT_THRESHOLD - 1)
        d = _decide(rec)
        self.assertTrue(d.reusable)


class LineRangeShiftDoesNotBypassEligibilityTests(unittest.TestCase):
    """[ADDED, per the qualifiedSymbol redesign's required test
    matrix]: a candidate whose reachabilityPath differs from the
    record ONLY by lineRange (path + qualifiedSymbol unchanged) still
    passes the identity precondition (see test_identity.py's
    LineRangeIdentityTests) -- but that must never, by itself, grant
    reuse. Every one of (a)-(d) must still run and can still refuse
    it; identity match is necessary, not sufficient."""

    def _record_with_line_ranges(self):
        return schema.new_rejection_record(
            record_id="lr-elig",
            category="BOLA/IDOR",
            suspicion_pattern="object reference from caller-supplied ID",
            safety_pattern="ownership check enforced",
            reachability_path=[
                {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get", "lineRange": {"start": 10, "end": 12}},
                {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById", "lineRange": {"start": 40, "end": 44}},
            ],
            rejection_reason="ownership check present",
            evidence={"path": "a/Repository.cs", "observation": "no check at sink, enforced upstream"},
            scope="this path only",
            trace_confidence="HIGH",
            last_validation={"timestamp": "t", "commit": "c", "validatedBy": "human"},
        )

    def _shifted_candidate_path(self):
        # Same path + qualifiedSymbol at every hop; only lineRange moved
        # (as if a comment were inserted above the first hop).
        return [
            {"path": "a/Controller.cs", "qualifiedSymbol": "Controller.Get", "lineRange": {"start": 15, "end": 17}},
            {"path": "a/Repository.cs", "qualifiedSymbol": "Repository.FindById", "lineRange": {"start": 40, "end": 44}},
        ]

    def test_identity_matches_but_check_a_still_refuses_reuse(self):
        record = self._record_with_line_ranges()
        candidate_path = self._shifted_candidate_path()
        d = eligibility.decide_reuse(
            record=record,
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=candidate_path,
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=False,  # re-inspection says the pattern no longer holds
            known_condition_states={},
            changed_files=[],
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in candidate_path},
        )
        self.assertTrue(d.identity_result.same_occurrence)  # identity alone says "same occurrence"...
        self.assertFalse(d.reusable)  # ...but reuse is still correctly refused
        self.assertIn(eligibility.REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED, d.reasons)

    def test_identity_matches_and_all_of_a_d_pass_then_reuse_is_granted(self):
        # Control case: proves the refusal above is really about check
        # (a), not some side effect of the lineRange shift itself.
        record = self._record_with_line_ranges()
        candidate_path = self._shifted_candidate_path()
        d = eligibility.decide_reuse(
            record=record,
            candidate_category="BOLA/IDOR",
            candidate_evidence_path="a/Repository.cs",
            candidate_reachability_path=candidate_path,
            candidate_trace_confidence="HIGH",
            pattern_and_scope_match=True,
            known_condition_states={},
            changed_files=[],
            hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in candidate_path},
        )
        self.assertTrue(d.identity_result.same_occurrence)
        self.assertTrue(d.reusable)


if __name__ == "__main__":
    unittest.main()
