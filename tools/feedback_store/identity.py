"""Occurrence identity precondition -- context-manifest-schema.md
section 5.1.

"a new candidate is the same occurrence as an existing Feedback record
only if ALL of: (i) evidence.path (the sink) is identical; (ii)
candidateShape.category is identical; (iii) reachabilityPath matches
EXACTLY... Failing (i), (ii), or (iii) means the candidate is a
DIFFERENT occurrence and is never checked against this record at all
-- it goes straight to full validation, the checks (a)-(d) never even
apply."

This module implements ONLY that precondition -- (i)/(ii)/(iii) above.
Condition (iv) in that section's initial enumeration ("current code
still matches safetyPattern") is deliberately NOT re-implemented here:
`context-manifest-schema.md`'s own worked Case 2 has a candidate that
passes identity on sink+category+path and only THEN fails at
eligibility check (a) when the sink's own code changes -- proving (iv)
is evaluated at check (a), not at the identity-precondition stage. This
is a disclosed reading of an internally ambiguous passage (the
section's own summary sentence -- "matches on sink, category, and
exact reachability path proceeds to (a)-(d)" -- names only three
conditions, not four), not a silent choice between two equally-clear
options. See eligibility.py for check (a).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Mapping, Sequence

from . import paths
from . import schema

SINK_MISMATCH = "SINK_MISMATCH"
CATEGORY_MISMATCH = "CATEGORY_MISMATCH"
REACHABILITY_PATH_MISMATCH = "REACHABILITY_PATH_MISMATCH"
CANDIDATE_TRACE_NOT_HIGH_CONFIDENCE = "CANDIDATE_TRACE_NOT_HIGH_CONFIDENCE"
LEGACY_RECORD_SCHEMA = "LEGACY_RECORD_SCHEMA_NOT_REUSABLE"
SAME_OCCURRENCE = "SAME_OCCURRENCE"


def _is_legacy_schema_record(record: Mapping) -> bool:
    """A record built under schema version 1 has bare `symbol` entries
    with no `qualifiedSymbol` key at all. Such a record must NEVER be
    matched for reuse, regardless of the store's own claimed
    `schemaVersion` -- this check is at the RECORD level, so it holds
    even if a legacy record ends up loaded alongside version-2
    records. The only way a legacy record becomes reusable again is a
    genuine re-derivation through the full independent Validator,
    producing a freshly-built version-2 record.

    [CORRECTED, per explicit instruction closing a Round 4 independent
    review Minor]: the definition now lives in ONE place --
    `schema.is_legacy_shaped` (key genuinely ABSENT), shared with
    store.py and invalidation.py -- rather than two hand-kept copies
    that had already drifted (Round 3 made this copy also treat a
    present-but-invalid value as legacy, which was wrong in the
    fail-open direction for the store; see that function's docstring).
    A present-but-invalid `qualifiedSymbol` is a BROKEN CURRENT record:
    `paths.same_reachability_path` refuses to match it (non-string /
    empty values never compare equal) and `eligibility.decide_reuse`
    rejects it outright via strict validation, so it is still never
    reusable -- it is just no longer mislabelled "legacy".
    """
    return schema.is_legacy_shaped(record)


@dataclass(frozen=True)
class IdentityResult:
    same_occurrence: bool
    reasons: List[str] = field(default_factory=list)


def check_occurrence_identity(
    *,
    candidate_category: str,
    candidate_evidence_path: str,
    candidate_reachability_path: Sequence[Mapping[str, str]],
    candidate_trace_confidence: str,
    record: Mapping,
) -> IdentityResult:
    """`record` is a `feedback_rejection` record (schema.py shape).

    Fails CLOSED on anything malformed on the candidate side (an
    unparseable path, a missing symbol) by returning
    `same_occurrence=False` rather than raising -- a candidate this
    module cannot confidently identity-match is, by definition, not
    safely reusable, which is exactly the same outcome as an explicit
    mismatch. The caller (eligibility.py / the reviewing workflow)
    still runs full validation on it either way.
    """
    reasons: List[str] = []

    if _is_legacy_schema_record(record):
        # Refuse immediately -- a legacy (schema-version-1) record must
        # never be matched for reuse, full stop; do not even bother
        # evaluating the other conditions against it.
        return IdentityResult(same_occurrence=False, reasons=[LEGACY_RECORD_SCHEMA])
    shape = record["candidateShape"]

    if candidate_trace_confidence != "HIGH":
        # A LOW/MEDIUM-confidence candidate trace cannot be confidently
        # compared against a HIGH-confidence recorded path at all --
        # per schema section 5.1, only a HIGH-confidence trace may even
        # be CACHED; the same standard applies to what may be MATCHED
        # against a cached record, for the identical reason (a
        # truncated/inferred chain is more permissive to match, the
        # wrong direction for a strict identity check).
        reasons.append(CANDIDATE_TRACE_NOT_HIGH_CONFIDENCE)

    # [ADDED, per explicit instruction closing a Round 4 independent
    # review Minor]: both sides must be actual non-empty strings before
    # they can be "the same category" -- a bare `!=` let a record whose
    # category had been hand-edited to `None`/`""`/`0` match a candidate
    # carrying the same degenerate value (and `0 == False`). Same bug
    # class as the `qualifiedSymbol: None` case; same fix shape.
    record_category = shape.get("category")
    if not (isinstance(candidate_category, str) and candidate_category.strip()):
        reasons.append(CATEGORY_MISMATCH)
    elif not (isinstance(record_category, str) and record_category.strip()):
        reasons.append(CATEGORY_MISMATCH)
    elif candidate_category != record_category:
        reasons.append(CATEGORY_MISMATCH)

    try:
        sink_matches = paths.same_path(candidate_evidence_path, record["evidence"]["path"])
    except paths.InvalidPathError:
        sink_matches = False
    if not sink_matches:
        reasons.append(SINK_MISMATCH)

    if not paths.same_reachability_path(candidate_reachability_path, shape["reachabilityPath"]):
        reasons.append(REACHABILITY_PATH_MISMATCH)

    if reasons:
        return IdentityResult(same_occurrence=False, reasons=reasons)
    return IdentityResult(same_occurrence=True, reasons=[SAME_OCCURRENCE])
