"""Tests for tools/context_manifest/budget.py -- computeReviewBudget.

Covers, of the 17 cases in tests/validation/v3-review-budget-test-cases.md:
the 9 pure level-computation cases (3, 4, 5, 6, 9, 10, 11, 12, 13); the
VALUE half of cases 7/7b specifically (that an explicit DEEP request's
budget can move all the way down to MINIMAL, uncapped) -- their LOADING
and ACTIVITY halves (does DEEP mode still load/run everything it
requires regardless of that low budget value) are NOT tested by this
module, since this module has no concept of "loading" or "activities"
at all; and the TARGETED movement-cap rule itself. The remaining 6
cases (1, 2, 8, 14, 15, 16) are pure process/wiring guarantees this
module does not implement or claim to test on its own -- see
work/v4-planning/batch0-verification-log.md for how those, and cases
7/7b's own loading/activity halves, are traced against
skills/security-review/SKILL.md and plays/secure-development-workflow.md
instead.
"""

from __future__ import annotations

import unittest

from .. import budget


class LevelComputationCases(unittest.TestCase):
    def test_case_3_moderate_no_factor(self):
        self.assertEqual(budget.compute_review_budget("TARGETED", "MODERATE"), "FOCUSED")

    def test_case_4_high_no_factor(self):
        self.assertEqual(budget.compute_review_budget("TARGETED", "HIGH"), "ELEVATED")

    def test_case_5_high_plus_one_factor_reaches_audit(self):
        self.assertEqual(
            budget.compute_review_budget("TARGETED", "HIGH", factor_adjustment=1), "AUDIT"
        )

    def test_case_6_moderate_plus_one_factor_reaches_elevated(self):
        # The case table names the scenario ("small internal endpoint,
        # baseline auth state UNKNOWN") but not an explicit sensitivity
        # level; review-budget.md's own "Examples" section places this
        # scenario at a MODERATE-typical starting point, moved up one
        # level by the Baseline-confidence Factor -- documented here as
        # the input this test asserts, not read off the case table
        # verbatim.
        self.assertEqual(
            budget.compute_review_budget("TARGETED", "MODERATE", factor_adjustment=1), "ELEVATED"
        )

    def test_case_9_quick_defaults_to_focused(self):
        self.assertEqual(budget.compute_review_budget("QUICK"), "FOCUSED")

    def test_case_10_standard_defaults_to_focused(self):
        self.assertEqual(budget.compute_review_budget("STANDARD"), "FOCUSED")

    def test_case_11_deep_defaults_to_audit(self):
        self.assertEqual(budget.compute_review_budget("DEEP"), "AUDIT")

    def test_case_12_moderate_pair(self):
        self.assertEqual(budget.compute_review_budget("TARGETED", "MODERATE"), "FOCUSED")

    def test_case_13_high_pair(self):
        self.assertEqual(budget.compute_review_budget("TARGETED", "HIGH"), "ELEVATED")


class CasesSevenAndSevenBDownwardMovement(unittest.TestCase):
    """An explicit DEEP request that touches nothing security-sensitive
    can move all the way down to MINIMAL -- uncapped for DEEP, unlike
    TARGETED's one-level cap."""

    def test_explicit_deep_can_move_all_the_way_down_to_minimal(self):
        self.assertEqual(
            budget.compute_review_budget("DEEP", factor_adjustment=-3), "MINIMAL"
        )

    def test_explicit_deep_downward_movement_is_uncapped_not_one_level(self):
        # A one-level-only cap would floor this at ELEVATED (AUDIT - 1);
        # DEEP has no such cap.
        self.assertNotEqual(
            budget.compute_review_budget("DEEP", factor_adjustment=-3), "ELEVATED"
        )


class MovementCapEnforcement(unittest.TestCase):
    def test_targeted_cap_limits_a_two_level_request_to_one_level(self):
        # HIGH's starting point is ELEVATED (index 2). Index 4 (two
        # levels up) does not exist; even a large positive adjustment
        # is clamped to the one-level-up cap (AUDIT), never silently
        # wrapping or raising.
        self.assertEqual(
            budget.compute_review_budget("TARGETED", "HIGH", factor_adjustment=2), "AUDIT"
        )

    def test_targeted_requires_a_sensitivity_argument(self):
        with self.assertRaises(ValueError):
            budget.starting_point("TARGETED", sensitivity=None)

    def test_quick_and_standard_ignore_whatever_sensitivity_is_passed(self):
        # [FIXED, per independent review Nit]: QUICK/STANDARD accept a
        # `sensitivity` argument (the function signature is shared with
        # TARGETED) but must ignore it -- neither mode has a
        # sensitivity classification per plays/review-budget.md's own
        # Applicability matrix. Confirms this is actually ignored, not
        # silently accepted as if meaningful.
        for junk_sensitivity in ("HIGH", "not-a-real-value", None):
            self.assertEqual(budget.starting_point("QUICK", junk_sensitivity), "FOCUSED")
            self.assertEqual(budget.starting_point("STANDARD", junk_sensitivity), "FOCUSED")


class LegalRangeAndFloorChecks(unittest.TestCase):
    def test_targeted_high_floor_rejects_minimal(self):
        self.assertFalse(budget.is_within_floor("TARGETED", "HIGH", "MINIMAL"))

    def test_targeted_high_floor_accepts_focused_through_audit(self):
        for level in ("FOCUSED", "ELEVATED", "AUDIT"):
            self.assertTrue(budget.is_within_floor("TARGETED", "HIGH", level))

    def test_explicit_deep_floor_accepts_every_level(self):
        for level in budget.LEVELS:
            self.assertTrue(budget.is_within_floor("DEEP", None, level))


if __name__ == "__main__":
    unittest.main()
