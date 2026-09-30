"""Context Manifest field contract -- context-manifest-schema.md section 1.

Required/optional is decided by actual consumer need, per instruction,
not by "might be useful later":

  REQUIRED  -- the manifest validity checker (validator.py) or a named
              skills/security-review consumer step cannot do its job
              without this field. Missing -> the WHOLE manifest is
              discarded (see validator.py's own docstring for why a
              partial repair is never attempted).
  OPTIONAL  -- diagnostic, human-readable, or forward-looking only
              (Batch 1's Feedback Learning, a future execution
              mechanism with a hard per-review cap, bookkeeping). Its
              absence never fails validation and never blocks a
              consumer step; a step that WOULD use it if present falls
              back to a documented default.

`validity` is deliberately excluded from REQUIRED_TOP_LEVEL_FIELDS: it
does not exist yet at the moment validate_manifest() runs (that
would be circular -- a field stating whether the manifest is valid,
required to already be present before validation decides that). It is
required only of the FINAL, post-validation artifact -- attach_validity()
always adds it, so this is satisfied by construction, not by a
separate check.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from .domains import ALL_DOMAINS
from .budget import LEVELS as REVIEW_BUDGETS
from .budget import REVIEW_MODES

MANIFEST_VERSION = "1.0"

SENSITIVITIES = ("NONE", "LOW", "MODERATE", "HIGH", "N/A")
PRODUCED_BY_VALUES = ("jev", "built_in")
JEV_OUTCOMES = (
    "success",
    "no_token",
    "invalid_token",
    "timeout",
    "incomplete_output",
    "below_floor",
)

REQUIRED_TOP_LEVEL_FIELDS = (
    "manifestVersion",
    "producedBy",
    "targetChange",
    "reviewMode",
    "sensitivity",
    "domains",
    "reviewBudget",
    "scannersSelected",
    "scannersSkipped",
    "coverageGaps",
    "degradation",
)

OPTIONAL_TOP_LEVEL_FIELDS = (
    "reviewId",
    "producedAt",
    "priorityOrder",
    "intelligenceConsulted",
    "validity",  # see module docstring -- present only post-validation
    "factorsEvidence",  # [ADDED, per independent review Major] -- see
    # validator.py item 7's own note: a list of short strings naming
    # which of plays/review-budget.md's Factors were actually weighed
    # to justify moving `reviewBudget` away from its mechanical
    # starting point. Optional when reviewBudget equals that starting
    # point (no movement, nothing to justify); the validator requires
    # it non-empty whenever it does not. This does NOT validate WHICH
    # factors were cited are correct (that remains the calling agent's
    # judgment, same as item 0) -- it only closes the gap where a
    # budget could move with zero recorded justification at all.
)

REQUIRED_TARGET_CHANGE_FIELDS = ("files",)
OPTIONAL_TARGET_CHANGE_FIELDS = ("diffSummary", "techStack", "scannerAvailability")

REQUIRED_DEGRADATION_FIELDS = ("jevAttempted", "jevOutcome", "fallbackUsed", "fallbackReason")


def new_degradation_no_jev_attempted(reason: str = "no Jev token configured") -> dict:
    """The Batch 0 built-in-only path's degradation record: no Jev call
    was ever made -- distinct from a Jev call that was attempted and
    failed. See context-manifest-schema.md's own note: this field
    exists specifically so "no Jev token" is a first-class, testable,
    honestly-recorded scenario, never a silent "jevOutcome: success".

    `fallbackUsed: True` here is deliberate, not a copy-paste of the
    Jev-attempted-and-failed shape: per validator.py's item 8 ("if
    jevOutcome is anything other than 'success,' fallbackUsed must be
    true"), the built-in layer ran INSTEAD of Jev for every non-success
    outcome, including this one -- v4-design.md section 4.3's own
    six-outcome degradation table lists "Jev token missing/empty" as
    outcome 1, leading to "built-in layer, no Jev call made", on equal
    footing with the other five attempted-and-failed outcomes. Whether
    Jev was ever ATTEMPTED is `jevAttempted`'s own, separate question.
    """
    # [V4 Batch 2] `reason` lets the one other legitimate "never
    # attempted" case -- a NONE-sensitivity change with no implicated
    # domain, where no live review happens at all (measurement-plan.md's
    # T1: "does the system correctly make no Jev call") -- say so
    # honestly in the reason string while keeping the enum at six values
    # (validator item 8 binds jevAttempted:false to jevOutcome:no_token).
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string")
    return {
        "jevAttempted": False,
        "jevOutcome": "no_token",
        "fallbackUsed": True,
        "fallbackReason": reason,
    }


def new_degradation(jev_outcome: str, *, fallback_reason: Optional[str]) -> dict:
    """[ADDED, V4 Batch 2] The degradation record for a review in which
    the Jev producer path WAS entered (`jevAttempted: True`). One of the
    fixed six outcomes; `success` means the Jev manifest was accepted
    (no fallback, reason None); every other outcome means the built-in
    producer ran instead and `fallback_reason` carries the precise,
    human-readable cause -- the enum value classifies, the reason
    string preserves the exact diagnostic (an HTTP status, a validator
    check id, a parse error path). Never invents a seventh enum value;
    an outcome not in `JEV_OUTCOMES` is a programming error here, not a
    new state.
    """
    if jev_outcome not in JEV_OUTCOMES:
        raise ValueError(f"unknown jevOutcome {jev_outcome!r}; the enum is fixed at {JEV_OUTCOMES}")
    if jev_outcome == "no_token":
        # no_token is the one outcome where no attempt is made; use
        # new_degradation_no_jev_attempted() for it.
        raise ValueError("no_token is never an 'attempted' outcome -- use new_degradation_no_jev_attempted()")
    if jev_outcome == "success":
        if fallback_reason is not None:
            raise ValueError("a success outcome has no fallback reason")
        return {"jevAttempted": True, "jevOutcome": "success", "fallbackUsed": False, "fallbackReason": None}
    if not isinstance(fallback_reason, str) or not fallback_reason.strip():
        raise ValueError(f"a non-success outcome requires a non-empty fallbackReason, got {fallback_reason!r}")
    return {"jevAttempted": True, "jevOutcome": jev_outcome, "fallbackUsed": True, "fallbackReason": fallback_reason}


def new_target_change(files: Mapping[str, Any] = (), **optional) -> dict:
    result = {"files": list(files)}
    for key in OPTIONAL_TARGET_CHANGE_FIELDS:
        if key in optional:
            result[key] = optional[key]
    return result
