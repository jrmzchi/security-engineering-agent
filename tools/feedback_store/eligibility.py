"""Reuse eligibility checks (a)-(d) -- context-manifest-schema.md
section 5.1.

Checks (b) and (c) are mechanically decidable from this module's own
inputs (a set of already-known-true invalidation conditions; a
changed-files set). Checks (a) and (d) are NOT -- the schema's own text
is explicit that re-inspecting actual code against a natural-language
description ("does the current code still match this safetyPattern",
"is this specific control at this hop still present") is not something
this package's code can decide by itself. Those two checks take an
already-made judgment as an explicit input (a caller-supplied verdict),
and this module's OWN responsibility for them is narrower but still
real: apply the fail-closed default when that judgment is absent or
`None` (ambiguous/unknown), and never silently treat "the caller didn't
say" as a pass.

`decide_reuse()` always evaluates all four checks (a)/(b)/(c)/(d) and
reports EVERY failing one -- an already-failing check is never used as
an excuse to skip evaluating the others, per explicit instruction ("不
得因前三項通過就跳過第四項").
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Optional

from . import paths
from . import identity
from . import schema

REASON_RECORD_STALE = "RECORD_STALE"
# [ADDED, per explicit instruction closing a Round 4 independent review
# finding promoted to Major]: a record that fails strict schema
# validation (or is legacy-shaped) is NOT_REUSABLE with this reason --
# never an exception that aborts the review, never a reuse.
REASON_RECORD_SCHEMA_INVALID = "RECORD_SCHEMA_INVALID"
REASON_RECORD_LEGACY_SCHEMA = identity.LEGACY_RECORD_SCHEMA
REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED = "PATTERN_OR_SCOPE_NOT_CONFIRMED"
REASON_INVALIDATION_CONDITION_TRUE = "INVALIDATION_CONDITION_TRUE"
REASON_INVALIDATION_CONDITION_UNKNOWN = "INVALIDATION_CONDITION_UNKNOWN"
REASON_DEPENDENCY_CHANGED = "DEPENDENCY_CHANGED"
REASON_HOP_CONTROL_NOT_CONFIRMED = "HOP_CONTROL_NOT_CONFIRMED"
REASON_REUSE_COUNT_THRESHOLD_HIT = "REUSE_COUNT_THRESHOLD_HIT"

# `context-manifest-schema.md` section 5.1's own "[PROPOSED placeholder]
# 20, tunable" -- forces one full re-derivation after this many
# reuses without one, then resets the counter.
REUSE_COUNT_THRESHOLD = 20


def hop_key(path: str, qualified_symbol: str) -> str:
    """Canonical key for a {path, qualifiedSymbol} hop, for use in the
    `hop_controls_confirmed` mapping check (d) takes. Exposed so
    callers build the mapping with the same key shape this module
    reads it with, rather than the two independently guessing a
    convention. `[RENAMED, per explicit instruction closing a round-2
    independent review Major]`: parameter renamed from `symbol` to
    `qualified_symbol` -- see schema.py's own note on why."""
    # `paths.canonical` (not `validate`) so a hop recorded as
    # `src/R.cs` and confirmed by the caller as `src/r.cs` build the
    # SAME key -- one path-comparison rule everywhere (paths.py).
    #
    # [CORRECTED, V4 release]: the key used to be `path + "::" + symbol`.
    # A path may contain "::" and a C++ qualifiedSymbol always does, so
    # ("a::b", "c.d") and ("a", "b::c.d") built the same key and a
    # confirmation for one hop satisfied check (d) for the other -- the
    # fail-open direction. A JSON array is an unambiguous encoding of
    # the pair (every string is quoted and escaped).
    return json.dumps([paths.canonical(path), qualified_symbol], ensure_ascii=False)


def _check_a_pattern_and_scope(pattern_and_scope_match: Optional[bool]) -> Optional[str]:
    """(a) Pattern + scope match. `pattern_and_scope_match` is the
    caller's own re-inspection verdict: True only if ALL of --
    current code at every reachabilityPath entry still matches
    `safetyPattern`; the candidate falls within the record's `scope`;
    AND `scope` itself is no wider than what `safetyPattern` and
    `evidence.observation` together demonstrate (schema section
    5.1(a) -- these are two conditions bundled into one caller verdict
    here, since both require the same code re-inspection step; a
    caller that only checked one half must pass `None`, not `True`).
    `None` (ambiguous, or not actually checked) fails closed.
    """
    if pattern_and_scope_match is True:
        return None
    return REASON_PATTERN_OR_SCOPE_NOT_CONFIRMED


def _check_b_invalidation_conditions(
    invalidation_conditions: Iterable[str],
    known_condition_states: Mapping[str, Optional[bool]],
) -> Optional[str]:
    """(b) No invalidationConditions have become true. For each
    condition string on the record, the caller supplies its current
    truth value in `known_condition_states` (True/False), or omits it
    / maps it to `None` when it cannot currently be determined (e.g. a
    dependency-version or feature-flag condition with no way to check
    it right now). Any condition that IS true, OR whose state is
    unknown, fails this check closed -- "無法取得新狀態時... UNKNOWN
    不得重用" (an UNKNOWN condition is never treated as "not yet true").

    [CORRECTED, per a round-1 independent review Major]: the previous
    version only recognized the literal values `True` and `None` as
    "confirmed true" / "unknown" -- ANY other value (a string like
    `"UNKNOWN"`, `"true"`, an int, an empty dict) fell through both
    checks and was silently treated as "confirmed false," the exact
    fail-OPEN direction this check exists to prevent. `False` (exact
    identity) is now the ONLY value that counts as "confirmed not
    true" -- everything else, including a value that merely looks
    like a safe answer, fails closed.
    """
    for cond in invalidation_conditions:
        state = known_condition_states.get(cond, None)
        if state is False:
            continue
        if state is True:
            return REASON_INVALIDATION_CONDITION_TRUE
        return REASON_INVALIDATION_CONDITION_UNKNOWN
    return None


def _check_c_dependencies(dependencies: Iterable[str], changed_files: Iterable[str]) -> Optional[str]:
    """(c) No dependencies have changed (mechanical, diff-based --
    Selective Invalidation's existing changed-files-set lookup,
    unchanged mechanism, see invalidation.py).

    [CORRECTED, per a round-2 independent review Major]: the previous
    version caught `InvalidPathError` per comparison and silently
    `continue`d past it -- an absolute path, a `..`-containing path, or
    (worse) a bare string accidentally passed as `changed_files`
    instead of a list (Python iterates a string character-by-character)
    all failed OPEN, matching this batch's own already-fixed check (b)
    bug in a different check. A caller's OWN malformed argument is a
    caller-side bug that must raise loudly here, not be silently
    absorbed the way a corrupted on-disk record degrades gracefully
    elsewhere in this package -- those are different failure domains.
    """
    if isinstance(changed_files, (str, bytes)):
        raise TypeError(f"changed_files must be a list of paths, not a bare {type(changed_files).__name__}: {changed_files!r}")
    changed = {paths.canonical(c) for c in changed_files}
    for dep in dependencies:
        if paths.canonical(dep) in changed:
            return REASON_DEPENDENCY_CHANGED
    return None


def _check_d_hop_controls(
    reachability_path: Iterable[Mapping[str, str]],
    hop_controls_confirmed: Mapping[str, Optional[bool]],
) -> Optional[str]:
    """(d) Re-inspect each intermediate {path, qualifiedSymbol} entry
    (not just the terminal sink) to confirm its specific control is
    still present. `hop_controls_confirmed` is keyed by
    `hop_key(path, qualifiedSymbol)` -> True/False/absent. Missing or
    `False` fails closed -- this check ALWAYS runs and is reported
    independently of (a), even when (a) already failed (see module
    docstring)."""
    for entry in reachability_path:
        key = hop_key(entry["path"], entry["qualifiedSymbol"])
        if hop_controls_confirmed.get(key) is not True:
            return REASON_HOP_CONTROL_NOT_CONFIRMED
    return None


@dataclass(frozen=True)
class ReuseDecision:
    reusable: bool
    reasons: List[str] = field(default_factory=list)
    identity_result: Optional[identity.IdentityResult] = None
    # Human-readable diagnostic for RECORD_SCHEMA_INVALID (the exact
    # SchemaError text) -- so a refused record can be fixed or
    # re-derived, never silently dropped.
    detail: Optional[str] = None


def decide_reuse(
    *,
    record: Mapping,
    candidate_category: str,
    candidate_evidence_path: str,
    candidate_reachability_path,
    candidate_trace_confidence: str,
    pattern_and_scope_match: Optional[bool],
    known_condition_states: Mapping[str, Optional[bool]],
    changed_files: Iterable[str],
    hop_controls_confirmed: Mapping[str, Optional[bool]],
) -> ReuseDecision:
    """Full reuse decision for one (candidate, record) pair: identity
    precondition first (schema section 5.1's "(i)/(ii)/(iii)"), then
    -- only if identity holds -- checks (a)-(d), ALL evaluated and ALL
    reported, never short-circuited after the first failure.

    A record already marked STALE (see invalidation.py) is rejected
    immediately, before identity is even checked -- Selective
    Revalidation (not Evidence Reuse) is the only path back to
    reusable for a STALE record.

    [ADDED, per explicit instruction closing a Round 4 independent
    review finding promoted to Major]: this function is its OWN trust
    boundary. It does not assume `record` came through `store.load()`
    -- `append_rejection_record`/`replace_rejection_record` used to
    accept unvalidated in-memory records, so a record missing
    `dependencies` (defaulted to `[]` here = "nothing changed"), or
    with an unknown `status` (not the exact string "STALE" = treated as
    active), reached this function and was judged REUSABLE. Now: a
    legacy-shaped record is NOT_REUSABLE (`LEGACY_RECORD_SCHEMA_...`);
    a record failing `schema.validate_rejection_record` is NOT_REUSABLE
    (`RECORD_SCHEMA_INVALID`, with the error text in `detail`) --
    fail-closed, returned as a decision, never raised (a malformed
    record must degrade Evidence Reuse for this candidate, never abort
    the review). `status` is an explicit allowlist (absent = active,
    "STALE" = stale, anything else = invalid). No field this function
    reads is defaulted any more.
    """
    if schema.is_legacy_shaped(record):
        return ReuseDecision(reusable=False, reasons=[REASON_RECORD_LEGACY_SCHEMA])
    try:
        schema.validate_rejection_record(record)
    except schema.SchemaError as exc:
        return ReuseDecision(reusable=False, reasons=[REASON_RECORD_SCHEMA_INVALID], detail=str(exc))

    status = record.get("status")
    if status is None:
        pass  # the one and only active state
    elif status == schema.STATUS_STALE:
        return ReuseDecision(reusable=False, reasons=[REASON_RECORD_STALE])
    else:
        # Unreachable after validation (its allowlist is the same one),
        # kept explicit so this function's own contract does not depend
        # on the validator's: an unknown status is never "active".
        return ReuseDecision(reusable=False, reasons=[REASON_RECORD_SCHEMA_INVALID], detail=f"unknown status {status!r}")

    id_result = identity.check_occurrence_identity(
        candidate_category=candidate_category,
        candidate_evidence_path=candidate_evidence_path,
        candidate_reachability_path=candidate_reachability_path,
        candidate_trace_confidence=candidate_trace_confidence,
        record=record,
    )
    if not id_result.same_occurrence:
        # "checks (a)-(d) never even apply" -- a different occurrence
        # is never compared against this record's eligibility at all.
        return ReuseDecision(reusable=False, reasons=list(id_result.reasons), identity_result=id_result)

    shape = record["candidateShape"]
    reasons: List[str] = []

    a = _check_a_pattern_and_scope(pattern_and_scope_match)
    if a:
        reasons.append(a)
    # No defaults below: validation above guarantees every field is
    # present and well-typed, and a default here would be exactly the
    # "missing means safe" fail-open this function must never have.
    b = _check_b_invalidation_conditions(record["invalidationConditions"], known_condition_states)
    if b:
        reasons.append(b)
    c = _check_c_dependencies(record["dependencies"], changed_files)
    if c:
        reasons.append(c)
    d = _check_d_hop_controls(shape["reachabilityPath"], hop_controls_confirmed)
    if d:
        reasons.append(d)

    if record["reuseCount"] >= REUSE_COUNT_THRESHOLD:
        reasons.append(REASON_REUSE_COUNT_THRESHOLD_HIT)

    if reasons:
        return ReuseDecision(reusable=False, reasons=reasons, identity_result=id_result)
    return ReuseDecision(reusable=True, reasons=[], identity_result=id_result)
