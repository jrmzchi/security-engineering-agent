"""Selective Invalidation for Feedback records --
context-manifest-schema.md section 4.2, reusing
`plays/security-impact-analysis.md`'s existing `freshnessOf` /
changed-files-set mechanism rather than inventing a second,
contradictory freshness rule.

Two mechanisms, matching that play's own two mechanisms exactly:

1. **Ordinary (direct-lookup)**: a record's `dependencies` (derived
   from `reachabilityPath`, per schema.py) is checked against the
   changed-files set -- an exact match, nothing content-aware. This is
   fully mechanical (`find_directly_stale`).

2. **Central-component broader invalidation**: `plays/security-impact-
   analysis.md`'s "Incremental invalidation" section reserves this for
   "central routing, authentication/authorization bootstrap, or other
   configuration" specifically -- a DELIBERATELY NARROWER list than
   `plays/review-budget.md`'s "Changed attack-surface centrality"
   qualitative list (shared HTTP client factory, shared deserialization
   helper, etc.), which that play's own text says explicitly is "not
   the same list... use this broader one for sizing effort, that
   narrower one for deciding what to invalidate." [DISCLOSED, found
   while implementing this batch] `context-manifest-schema.md` section
   4.2's own prose conflates the two lists as though they were "the
   same one" -- this module follows `plays/review-budget.md`'s own,
   more precise text (the authoritative source) instead of the schema
   doc's imprecise restatement, per this kit's established practice of
   preferring the authoritative Play over a condensed description that
   has drifted from it. Using the broader list here would over-widen
   invalidation blast radius beyond what the play that owns this
   mechanism actually licenses.

   "Recognizing which files are this central is itself a
   security-relevant judgment" (that play's own words) -- this module
   does NOT try to infer centrality from a file's name or content. The
   caller (the reviewing agent, which already makes this exact
   judgment call for baseline.json/attack-surface.json today) supplies
   an explicit, bounded list of affected categories and/or path
   prefixes; this module's own job is purely mechanical from there:
   given that explicit input, deterministically find every matching
   record, never "the entire store."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, List, Mapping, Optional

from . import paths
from . import schema

REASON_DIRECT_DEPENDENCY = "DIRECT_DEPENDENCY_CHANGED"
REASON_CENTRAL_COMPONENT = "CENTRAL_COMPONENT_BROADER_INVALIDATION"
REASON_INVALIDATION_CONDITION = "INVALIDATION_CONDITION_TRUE_OR_UNKNOWN"
# [ADDED, per explicit instruction closing Round 4 independent review
# findings]: a CURRENT record whose own data is too malformed for this
# module to evaluate (missing/non-list/non-string/invalid-path
# `dependencies`, non-mapping record, ...) is reported with THIS reason
# -- with the diagnostic preserved in `detail`, never skipped silently
# and never allowed to abort the scan of every other record.
# [CLARIFIED, Batch 2 preflight, per a Round 6 Nit]: what the caller
# must DO with such a finding is re-derive the record through the full
# Validator, or quarantine it (remove it / re-load the store) -- NOT
# call `store.mark_stale()` on it. `mark_stale` runs the strict
# validator on the whole record before committing (copy -> mutate ->
# validate -> commit), so a malformed current record is refused there
# too; it can never be reused regardless (`eligibility.decide_reuse`
# re-validates and returns RECORD_SCHEMA_INVALID), so nothing is
# fail-open in the meantime. The earlier wording here said "marked
# stale", which the current `mark_stale` cannot do for this shape.
REASON_RECORD_MALFORMED = "RECORD_MALFORMED_NEEDS_REVALIDATION"


@dataclass(frozen=True)
class StaleFinding:
    record_id: str
    reason: str
    detail: str


def _validate_changed_files(changed_files: Collection[str]) -> set:
    """The CALLER's own argument: malformed input here is a caller-side
    bug and raises loudly (round-2 fix; a bare string would otherwise
    be iterated character by character and match nothing, silently)."""
    if isinstance(changed_files, (str, bytes)):
        raise TypeError(f"changed_files must be a list of paths, not a bare {type(changed_files).__name__}: {changed_files!r}")
    return {paths.canonical(c) for c in changed_files}


def _record_dependencies(record: Mapping) -> List[str]:
    """Return a record's `dependencies` as canonical comparison forms,
    or raise `ValueError` with a diagnostic if the record's OWN data is
    malformed (not a mapping; `dependencies` missing, `None`, not a
    list, or containing a non-string / invalid path). The caller turns
    that into a `REASON_RECORD_MALFORMED` finding for THAT record only.
    `None`/missing is deliberately NOT treated as "no dependencies": a
    current record without a dependency list cannot be judged, so it is
    unusable, not safe.
    """
    if not isinstance(record, Mapping):
        raise ValueError(f"record is not an object: {record!r}")
    if "dependencies" not in record:
        raise ValueError("dependencies is missing")
    deps = record["dependencies"]
    if not isinstance(deps, list):
        raise ValueError(f"dependencies must be a list, got {deps!r}")
    out: List[str] = []
    for i, dep in enumerate(deps):
        try:
            out.append(paths.canonical(dep))
        except paths.InvalidPathError as exc:
            raise ValueError(f"dependencies[{i}] is not a valid repository-relative path: {exc}") from exc
    return out


def find_directly_stale(records: Mapping[str, Mapping], changed_files: Collection[str]) -> List[StaleFinding]:
    """Ordinary mechanism: a record whose `dependencies` names any file
    in `changed_files` is stale. Direct lookup only -- never re-walks or
    re-considers a record with no changed dependency. Path comparison
    goes through `paths.canonical` -- the ONE rule identity and
    eligibility also use (case-insensitive; see paths.py for why that
    is the fail-closed direction HERE specifically).

    [CORRECTED, per a round-2 independent review Major]: a malformed
    `changed_files` argument (the CALLER's input) raises loudly instead
    of being silently skipped per comparison.

    [CORRECTED, per explicit instruction closing Round 4 independent
    review findings, superseding the Round 3 version]: a record's OWN
    malformed data is a different failure domain from the caller's
    argument. Round 3 caught only `InvalidPathError` and silently
    `continue`d -- `dependencies: null` still escaped as a `TypeError`
    that aborted the whole scan, and a silent skip left no diagnostic.
    Now, per record: a legacy-shaped record (audit-only by definition,
    can never be reused regardless of `status`) is skipped; a CURRENT
    record whose dependencies cannot be evaluated for ANY reason is
    reported as `REASON_RECORD_MALFORMED` with the diagnostic in
    `detail` -- it is to be marked stale / needs re-validation, never
    treated as "nothing changed", and never allowed to stop the other
    records from being evaluated.
    """
    changed = _validate_changed_files(changed_files)
    findings: List[StaleFinding] = []
    for record_id, record in records.items():
        if schema.is_legacy_shaped(record):
            continue
        try:
            record_deps = _record_dependencies(record)
        except ValueError as exc:
            findings.append(StaleFinding(record_id, REASON_RECORD_MALFORMED, str(exc)))
            continue
        for dep in record_deps:
            if dep in changed:
                findings.append(StaleFinding(record_id, REASON_DIRECT_DEPENDENCY, f"dependency {dep!r} changed"))
                break
    return findings


def find_central_component_stale(
    records: Mapping[str, Mapping],
    *,
    central_component_file: str,
    affected_categories: Collection[str] = (),
    affected_path_prefixes: Collection[str] = (),
) -> List[StaleFinding]:
    """Bounded broader invalidation. The caller has already judged
    `central_component_file` to be central routing/authn/authz
    bootstrap/other configuration (this module does not make that
    judgment) and names EXPLICITLY which categories and/or path
    prefixes it affects. A record matches if its
    `candidateShape.category` is in `affected_categories`, OR any of
    its `dependencies`/`reachabilityPath` paths starts with one of
    `affected_path_prefixes` -- both bounded, both caller-supplied,
    never "every record" and never inferred from the changed file's
    name or content by this module itself.
    """
    # [ADDED, per explicit instruction (truncated section 六 of the
    # Round 5 close-out, confirmed after Round 6)]: the CALLER's scope
    # arguments get the same bare-string guard `changed_files` already
    # had. A bare `"src"` prefix used to iterate as `s`/`r`/`c` and
    # silently invalidate nothing (fail-open for a caller who meant a
    # real bounded scope); a bare `"authorization"` category turned the
    # membership test into a substring test. Both are caller-side bugs
    # and raise loudly.
    for name, value in (("affected_categories", affected_categories), ("affected_path_prefixes", affected_path_prefixes)):
        if isinstance(value, (str, bytes)):
            raise TypeError(f"{name} must be a collection of strings, not a bare {type(value).__name__}: {value!r}")
    for category in affected_categories:
        if not isinstance(category, str) or not category.strip():
            raise TypeError(f"affected_categories entries must be non-empty strings, got {category!r}")

    if not affected_categories and not affected_path_prefixes:
        # An empty scope must invalidate nothing, not "everything" --
        # guards against a caller accidentally passing no bound at all
        # and getting silent full-store invalidation as a side effect.
        return []
    findings: List[StaleFinding] = []
    # [CORRECTED, per a round-1 independent review Minor]: `normalize()`
    # alone does not reject an absolute path or a `..` segment -- a
    # malformed prefix (e.g. an accidental absolute path) previously
    # matched zero records silently instead of failing loudly, which
    # is the fail-OPEN direction for a caller who actually intended a
    # real, bounded scope. `validate()` raises instead.
    canonical_prefixes = [paths.canonical(p) for p in affected_path_prefixes]
    for record_id, record in records.items():
        if schema.is_legacy_shaped(record):
            continue  # audit-only by definition; never reusable regardless of status
        if not isinstance(record, Mapping):
            findings.append(StaleFinding(record_id, REASON_RECORD_MALFORMED, f"record is not an object: {record!r}"))
            continue
        shape = record.get("candidateShape")
        category = shape.get("category") if isinstance(shape, Mapping) else None
        # Only a real non-empty string can match a category; a
        # degenerate value (None/""/0) neither matches nor is silently
        # treated as "some other category" -- it makes the record
        # malformed below if its dependencies can't carry it either.
        if isinstance(category, str) and category.strip() and category in affected_categories:
            findings.append(
                StaleFinding(
                    record_id,
                    REASON_CENTRAL_COMPONENT,
                    f"category {category!r} affected by central component {central_component_file!r}",
                )
            )
            continue
        # [CORRECTED, per explicit instruction closing Round 4 independent
        # review findings]: the previous version silently `continue`d
        # past an unparseable dependency entry (fail-open for that
        # record) and read `dependencies` with a default of `[]`
        # (missing = "nothing to match"). A current record whose own
        # dependencies cannot be evaluated is now reported MALFORMED,
        # for that record only; the scan of the others continues.
        try:
            record_deps = _record_dependencies(record)
        except ValueError as exc:
            findings.append(StaleFinding(record_id, REASON_RECORD_MALFORMED, str(exc)))
            continue
        matched_prefix = None
        for canonical_p in record_deps:
            for prefix in canonical_prefixes:
                if canonical_p == prefix or canonical_p.startswith(prefix + "/"):
                    matched_prefix = prefix
                    break
            if matched_prefix:
                break
        if matched_prefix:
            findings.append(
                StaleFinding(
                    record_id,
                    REASON_CENTRAL_COMPONENT,
                    f"path prefix {matched_prefix!r} affected by central component {central_component_file!r}",
                )
            )
    return findings


def resolve_non_file_conditions(
    invalidation_conditions_by_record: Mapping[str, Collection[str]],
    known_condition_states: Mapping[str, Optional[bool]],
) -> List[StaleFinding]:
    """Non-file invalidation conditions (dependency version bump,
    feature-flag flip, environment policy change) that cannot be
    resolved by a Git diff at all. `known_condition_states` is the
    caller's own best-effort current answer for each named condition
    string -- True (confirmed true -> stale), False (confirmed false
    -> not stale on this basis), or absent/None (cannot currently be
    determined). Per explicit instruction: UNKNOWN is never treated as
    "not yet true" -- an unresolvable condition marks the record stale
    (fail closed) exactly the same as a confirmed-true one, rather than
    silently assuming the changed-files lookup already covered it.

    [CORRECTED, per a round-1 independent review Major]: the previous
    version only recognized literal `True`/`None` -- any other value
    (e.g. the string `"UNKNOWN"`, which `plays/finding-validation.md`
    itself uses as prose for this exact state) fell through both
    branches and was silently treated as "not stale," the fail-OPEN
    direction this function exists to prevent. `False` (exact identity)
    is now the only value that counts as "confirmed not stale on this
    basis."
    """
    findings: List[StaleFinding] = []
    for record_id, conditions in invalidation_conditions_by_record.items():
        for cond in conditions:
            state = known_condition_states.get(cond, None)
            if state is False:
                continue
            if state is True:
                findings.append(StaleFinding(record_id, REASON_INVALIDATION_CONDITION, f"condition {cond!r} confirmed true"))
            else:
                findings.append(StaleFinding(record_id, REASON_INVALIDATION_CONDITION, f"condition {cond!r} unresolvable (UNKNOWN)"))
            break
    return findings
