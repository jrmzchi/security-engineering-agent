"""computeReviewBudget -- v4-design.md section 7 (Option B, decided).

The single, merged review-budget entry point. Replaces
plays/secure-development-workflow.md's sensitivity-driven computation
and skills/security-review/SKILL.md's mode-driven computation each
independently re-deriving a level -- both call this one function.

`plays/review-budget.md` is explicit that the Factors ("External
exposure", "Attacker control", "Privilege", ... "Changed attack-surface
centrality") are QUALITATIVELY WEIGHED, not scored by a formula ("None
of these alone determines the level -- weigh them together"). This
module therefore does not attempt to compute the Factors adjustment
itself -- that reasoning is the calling agent's job, the same way
context-manifest-schema.md section 3's item 0 classification is agent
reasoning this package does not perform. What this module DOES own,
mechanically:

  1. The starting-point lookup (mode, sensitivity) -> level -- a pure
     table, per "Default starting point" / "Explicit mode".
  2. The movement-cap RULE: at most one level of movement from the
     starting point for TARGETED; uncapped (any of the four levels)
     for QUICK/STANDARD/DEEP. This is what "single merged entry point"
     actually buys -- one place that can never disagree with itself
     about which mode gets which cap.
  3. Applying an already-decided factor_adjustment (a signed integer:
     how many levels the calling agent's own Factors reasoning already
     concluded to move, and in which direction) within that cap.

`legal_range` is the mechanical half of the manifest validator's
"budget floor" check (context-manifest-schema.md section 3, item 7):
it does not re-derive what the Factors reasoning concluded (this
module cannot, and does not try to), but it DOES reject a declared
budget that violates the movement cap itself -- e.g. a TARGETED/HIGH
manifest (starting point ELEVATED, cap +/-1) declaring MINIMAL is
illegal regardless of what Factors were cited, since MINIMAL is two
levels below the floor the cap permits.
"""

from __future__ import annotations

from typing import Optional, Tuple

LEVELS = ("MINIMAL", "FOCUSED", "ELEVATED", "AUDIT")
_INDEX = {level: i for i, level in enumerate(LEVELS)}

REVIEW_MODES = ("TARGETED", "QUICK", "STANDARD", "DEEP")
SENSITIVITIES = ("NONE", "LOW", "MODERATE", "HIGH")


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def level_index(level: str) -> int:
    """Ordinal position of `level` in LEVELS (MINIMAL=0 .. AUDIT=3) --
    the public way to compare two levels' ordering (e.g. "did the
    budget move up or down from its starting point"), instead of a
    caller reaching into this module's own _INDEX directly."""
    if level not in _INDEX:
        raise ValueError(f"invalid budget level: {level!r}")
    return _INDEX[level]


def starting_point(review_mode: str, sensitivity: Optional[str] = None) -> str:
    """The "Default starting point" / "Explicit mode" lookup, before Factors.

    For TARGETED, `sensitivity` is required (NONE/LOW/MODERATE/HIGH).
    Per the Applicability matrix, NONE/LOW never actually reach a live
    computation (NONE has no review at all; LOW only escalates or
    stops) -- this function still returns a defined value for both,
    matching "the rows exist for completeness, not because every
    sensitivity value is computed and applied on every change". LOW's
    own row is stated ambiguously in the play itself ("MINIMAL or
    FOCUSED") precisely because it is never live-applied; MINIMAL is
    returned here as the single deterministic choice this module must
    make, which is inconsequential given LOW is unreachable.
    """
    if review_mode == "TARGETED":
        if sensitivity not in SENSITIVITIES:
            raise ValueError(f"TARGETED requires a sensitivity in {SENSITIVITIES}, got {sensitivity!r}")
        return {
            "NONE": "MINIMAL",
            "LOW": "MINIMAL",
            "MODERATE": "FOCUSED",
            "HIGH": "ELEVATED",
        }[sensitivity]
    if review_mode in ("QUICK", "STANDARD"):
        return "FOCUSED"
    if review_mode == "DEEP":
        return "AUDIT"
    raise ValueError(f"unknown review_mode: {review_mode!r}")


def legal_range(review_mode: str, sensitivity: Optional[str] = None) -> Tuple[str, str]:
    """(lowest, highest) legal budget level for this (mode, sensitivity).

    TARGETED: capped at one level of movement from the starting point,
    per "Move at most one level up or down from this default per the
    Factors". QUICK/STANDARD/DEEP: uncapped -- "The 'move at most one
    level' cap ... does not apply here", per review-budget.md's
    "Explicit mode" section (case 7/7b's own downward-to-MINIMAL
    movement from an explicit DEEP request is exactly this).
    """
    start_idx = _INDEX[starting_point(review_mode, sensitivity)]
    if review_mode == "TARGETED":
        lo, hi = start_idx - 1, start_idx + 1
    else:
        lo, hi = 0, len(LEVELS) - 1
    lo, hi = _clamp(lo, 0, len(LEVELS) - 1), _clamp(hi, 0, len(LEVELS) - 1)
    return LEVELS[lo], LEVELS[hi]


def compute_review_budget(
    review_mode: str, sensitivity: Optional[str] = None, factor_adjustment: int = 0
) -> str:
    """The merged entry point. `factor_adjustment` is a signed integer the
    calling agent's own Factors reasoning already decided (positive =
    move up, negative = move down) -- this function only applies the
    movement-cap rule, it does not decide the adjustment itself."""
    start_idx = _INDEX[starting_point(review_mode, sensitivity)]
    lo_level, hi_level = legal_range(review_mode, sensitivity)
    lo_idx, hi_idx = _INDEX[lo_level], _INDEX[hi_level]
    idx = _clamp(start_idx + factor_adjustment, lo_idx, hi_idx)
    return LEVELS[idx]


def is_within_floor(review_mode: str, sensitivity: Optional[str], declared_budget: str) -> bool:
    """The mechanical half of the validator's budget-floor check (item
    7): is `declared_budget` within the legal movement-cap range for
    this (mode, sensitivity)? Does NOT re-derive whether the specific
    Factors cited actually justify the declared value -- that
    reasoning is the calling agent's, not recomputed here (see this
    module's own docstring)."""
    if declared_budget not in _INDEX:
        raise ValueError(f"invalid budget level: {declared_budget!r}")
    lo_level, hi_level = legal_range(review_mode, sensitivity)
    return _INDEX[lo_level] <= _INDEX[declared_budget] <= _INDEX[hi_level]
