"""`.security/feedback.json` record shapes -- context-manifest-schema.md
sections 4/5, revised a third time (reachabilityPath added).

Two record types share one store: `feedback_rejection` (section 5, a
subtype of section 4's general record, reusing a
`plays/finding-validation.md` `REJECTED` result) and `feedback_miss`
(v4-design.md section 3.4's four-layer root-cause attribution record
for a human-discovered false negative -- NOT a rejection record; a
missed vulnerability is never stored as though it were a rejected
candidate).

This module only builds and validates individual records in memory --
`store.py` owns the file-level container, I/O, and atomic writes.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from . import paths
from .. import secret_heuristic

SCHEMA_VERSION = 2

# [ADDED, per explicit instruction closing a round-2 independent review
# Major: a fifth recurrence of occurrence-identity imprecision --
# reachabilityPath's `symbol` field required SOME qualification marker
# but never verified it actually disambiguated anything; two different
# methods sharing a name (an overload, or a generic framework-
# convention handler name reused across route registrations) still
# collided under the round-1 fix. `qualifiedSymbol` replaces `symbol`;
# schema version bumped from 1 to 2 because this is an identity-
# semantics change, not merely an additive field -- a version-1 record
# (bare `symbol`, no `qualifiedSymbol`) must never be silently treated
# as version-2-compatible.] Any store reporting this version is
# recognized (not "unsupported"), but every record loaded from it is
# audit-only -- see store.py's `load()` and identity.py's own
# legacy-schema guard, which refuses to match ANY record missing
# `qualifiedSymbol` regardless of what version number the store claims.
LEGACY_SCHEMA_VERSION = 1

RECORD_TYPE_REJECTION = "feedback_rejection"
RECORD_TYPE_MISS = "feedback_miss"

# plays/finding-validation.md's "Confidence model" -- the SAME scale
# plays/cross-file-data-flow.md's own "Confidence" section reuses for a
# multi-hop trace, not a new scale invented here. Deliberately NOT the
# same set as tools/context_manifest/domains.py's baseline-fact
# CONFIDENCE_LEVELS (HIGH/MEDIUM/LOW/UNKNOWN, Value/Source-based) --
# schema section 4's own mapping table calls this out explicitly as a
# collision V4 does not reintroduce.
TRACE_CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW")

# context-manifest-schema.md section 4.3: "Jev is never a valid value
# for validatedBy" -- the schema-level enforcement of v4-design.md
# section 5's permission boundary.
VALIDATED_BY_VALUES = ("human", "code_reviewer_subagent", "validator_procedure")

# v4-design.md section 3.4's four root-cause layers, in the order that
# section names them (routing -> attack surface -> cross-file flow ->
# reasoning) -- this module does not impose that order as a priority
# ranking (schema/callers must not "just pick the first" -- see
# attribution.py), it is only the canonical spelling/membership set.
MISS_LAYERS = ("routing", "attack_surface", "cross_file_flow", "reasoning")


class SchemaError(ValueError):
    """A record (or a field within one) does not match this schema."""


def _validate_path(raw: Any) -> str:
    """Wraps `paths.validate` so every path problem this module
    surfaces is a `SchemaError` (this module's own single exception
    type for "this record is invalid"), never a bare
    `paths.InvalidPathError` a caller of THIS module was never told to
    expect. `paths.InvalidPathError` remains the primitive other
    modules (identity.py, eligibility.py, invalidation.py) catch
    directly for their own fail-closed handling -- only this module's
    public record-building/validating functions re-wrap it.
    """
    try:
        return paths.validate(raw)
    except paths.InvalidPathError as exc:
        raise SchemaError(str(exc)) from exc


class LikelySecretError(SchemaError):
    """A string field looks like it contains a credential/secret and
    was refused rather than silently stored or silently redacted --
    per explicit instruction, storing is refused; the caller must
    redact the value itself and retry, rather than this module
    guessing what to keep.
    """


# [MOVED, V4 Batch 2]: the pattern list itself now lives in
# `tools/secret_heuristic.py` so `tools/context_manifest`'s outbound
# Jev-request redaction applies the IDENTICAL rule without either
# package importing the other (see that module's docstring). The
# round-1 Minor (`\b` vs snake_case) and round-2 Nit (JSON-quoted key)
# corrections travelled with it. This alias keeps every call site in
# this module unchanged.
_SECRET_PATTERNS = secret_heuristic.SECRET_PATTERNS


def _looks_like_secret(value: str) -> bool:
    """A DISCLOSED HEURISTIC, not a guarantee -- see
    `tools/secret_heuristic.py`. Its job is a cheap backstop, not a
    security control on its own."""
    return secret_heuristic.looks_like_secret(value)


def _check_no_secret(field_name: str, value: Any) -> None:
    if isinstance(value, str) and _looks_like_secret(value):
        raise LikelySecretError(
            f"{field_name} looks like it contains a credential/secret and was refused; "
            "redact the value before storing it in a Feedback record"
        )


def check_no_secret(field_name: str, value: Any) -> None:
    """Public alias of the secret heuristic for store.py's mutators
    (e.g. `mark_stale`'s `reason`), so they apply the SAME check the
    validators do rather than a re-implementation that could drift."""
    _check_no_secret(field_name, value)


def _check_no_secret_recursive(field_name: str, value: Any) -> None:
    """[ADDED, per a round-1 independent review Minor]: `new_miss_record`'s
    `evidence` argument is deliberately typed `Any` (a miss record's
    evidence can be a single {path, observation} mapping or a list of
    them, unlike a rejection record's fixed shape) -- the previous
    version only checked `evidence is not None`, never actually
    scanning its string content, so the same secret-shaped text that
    `new_rejection_record` refuses would pass through a miss record
    completely unchecked. Walks any combination of dict/list/tuple/
    string.

    [CORRECTED, Batch 2 preflight, per explicit instruction closing a
    Round 6 Nit]: mapping KEYS are scanned too, not only values -- a
    secret placed as a dict key used to pass. A non-string key (int,
    tuple, None) is simply not text and is skipped safely; the error
    message names the field path only, never the offending value. The
    same function serves rejection and miss records.

    Also rejects a string containing a lone surrogate (a code point
    that cannot be encoded as UTF-8): such a value used to pass every
    validator and then blow up inside `store.write()` as a raw
    `UnicodeEncodeError` after the temp file was already created.
    """
    if isinstance(value, str):
        _check_utf8_encodable(field_name, value)
        _check_no_secret(field_name, value)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str):
                _check_utf8_encodable(f"{field_name}.<key>", key)
                if _looks_like_secret(key):
                    raise LikelySecretError(
                        f"a key under {field_name} looks like it contains a credential/secret and was refused; "
                        "redact it before storing it in a Feedback record"
                    )
            _check_no_secret_recursive(f"{field_name}.{key if isinstance(key, str) else '<non-string-key>'}", item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for i, item in enumerate(value):
            _check_no_secret_recursive(f"{field_name}[{i}]", item)


def _check_utf8_encodable(field_name: str, value: str) -> None:
    """[ADDED, Batch 2 preflight]: refuse a string that cannot be
    encoded as UTF-8 (a lone surrogate, e.g. from a `surrogateescape`-
    decoded non-UTF-8 file name). Reported as a SchemaError naming the
    field and the position -- never echoing the value."""
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise SchemaError(
            f"{field_name} contains a code point that cannot be encoded as UTF-8 "
            f"(lone surrogate at position {exc.start}); the value cannot be stored"
        ) from None


def derive_minimum_dependencies(reachability_path: Sequence[Mapping[str, str]]) -> List[str]:
    """The dependency list `dependencies` must be AT LEAST as large as
    -- every path entry in `reachabilityPath`, in first-seen order,
    deduplicated. Callers may supply additional dependencies beyond
    this (e.g. a config file that gates a control without being a
    named hop) but never fewer.
    """
    seen: List[str] = []
    for entry in reachability_path:
        p = _validate_path(entry["path"])
        if not any(paths.same_path(p, existing) for existing in seen):
            seen.append(p)
    return seen


_QUALIFICATION_MARKERS = (".", "::", "#", "->")


def _looks_unqualified(symbol: str) -> bool:
    """`[STRENGTHENED, per explicit instruction closing a round-2
    independent review Major]`: the round-1 version of this check only
    asked "does SOME qualification marker character appear anywhere in
    the string" -- `"."`, `"#"`, or `"Get."` all passed despite naming
    nothing. This version additionally requires at least TWO real
    identifier-bearing segments around a marker (so a bare marker, or a
    marker with an empty segment on one side, is still rejected) -- but
    this remains a FLOOR, not a guarantee: it still cannot verify two
    DIFFERENT qualifiedSymbol strings that both look well-formed
    actually name different callables (e.g. it cannot detect that a
    caller wrote `ReportController.Get` for BOTH of two overloads,
    omitting the signature that would have told them apart) -- getting
    that right is the value-content responsibility documented on
    `qualifiedSymbol` itself, the same way `paths.py` can validate a
    path's SHAPE but not whether it names the file the caller actually
    meant.

    [CORRECTED, per a Round 3 independent review Minor]: this used to
    look for markers anywhere in the WHOLE string, including inside the
    parenthesized parameter signature -- so `"GetReport(System.Int32)"`,
    `"Get(List<System.String>)"`, and `"get(a::b)"` all passed despite
    having no real namespace/type qualifier before the method name at
    all (exactly the shape `templates/feedback-store.md`'s own prose
    says must be refused). Markers are now only looked for in the part
    BEFORE the first `"("`, so a qualifier embedded purely inside the
    signature can no longer satisfy this check.
    """
    name_part = symbol.split("(", 1)[0]
    for marker in _QUALIFICATION_MARKERS:
        if marker not in name_part:
            continue
        segments = [s for s in name_part.split(marker) if s.strip() and re.search(r"[A-Za-z0-9_]", s)]
        if len(segments) >= 2:
            return False
    return True


def _validate_line_range(entry_index: int, line_range: Any) -> Optional[MutableMapping[str, int]]:
    """`lineRange` is OPTIONAL evidence-location/diagnostic metadata --
    per explicit instruction, it must NEVER become part of occurrence
    identity (see identity.py/paths.py, which never read it at all).
    Validated here only so a malformed value fails loudly at
    construction time rather than being silently stored as junk.
    """
    if line_range is None:
        return None
    if not isinstance(line_range, Mapping) or "start" not in line_range or "end" not in line_range:
        raise SchemaError(f"reachabilityPath[{entry_index}].lineRange must be a mapping with 'start' and 'end', got {line_range!r}")
    start, end = line_range["start"], line_range["end"]
    for name, value in (("start", start), ("end", end)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise SchemaError(f"reachabilityPath[{entry_index}].lineRange.{name} must be a positive int, got {value!r}")
    if start > end:
        raise SchemaError(f"reachabilityPath[{entry_index}].lineRange.start ({start}) must not exceed .end ({end})")
    return {"start": start, "end": end}


def _validate_reachability_path(reachability_path: Any) -> List[MutableMapping[str, Any]]:
    if not isinstance(reachability_path, Sequence) or isinstance(reachability_path, (str, bytes)):
        raise SchemaError(f"reachabilityPath must be a list, got {reachability_path!r}")
    if len(reachability_path) == 0:
        raise SchemaError("reachabilityPath must not be empty -- an occurrence with no path to a sink cannot be identity-checked")
    normalized: List[MutableMapping[str, Any]] = []
    for i, entry in enumerate(reachability_path):
        if not isinstance(entry, Mapping):
            raise SchemaError(f"reachabilityPath[{i}] must be a mapping with path/qualifiedSymbol, got {entry!r}")
        if "path" not in entry or "qualifiedSymbol" not in entry:
            raise SchemaError(f"reachabilityPath[{i}] missing required 'path' or 'qualifiedSymbol': {entry!r}")
        qualified_symbol = entry["qualifiedSymbol"]
        if not isinstance(qualified_symbol, str) or not qualified_symbol.strip():
            raise SchemaError(f"reachabilityPath[{i}].qualifiedSymbol must be a non-empty string, got {qualified_symbol!r}")
        _check_no_secret(f"reachabilityPath[{i}].qualifiedSymbol", qualified_symbol)
        if _looks_unqualified(qualified_symbol):
            raise SchemaError(
                f"reachabilityPath[{i}].qualifiedSymbol {qualified_symbol!r} does not look like it can uniquely "
                "identify a callable -- include the enclosing namespace/module and type (e.g. "
                "'MyApp.Controllers.ReportController.Get'), and the parameter signature or arity when the "
                "language has overloads (e.g. 'MyApp.Controllers.ReportController.Get(int)') so two different "
                "methods can never collide. If a reliably unique qualifiedSymbol cannot actually be built for "
                "this trace, do not call this function at all -- do not cache the rejection; re-derive it "
                "through the full independent Validator every time it recurs instead."
            )
        normalized_path = _validate_path(entry["path"])
        normalized_entry: MutableMapping[str, Any] = {"path": normalized_path, "qualifiedSymbol": qualified_symbol}
        line_range = _validate_line_range(i, entry.get("lineRange"))
        if line_range is not None:
            normalized_entry["lineRange"] = line_range
        normalized.append(normalized_entry)
    return normalized


def _require_nonempty_str(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{name} must be a non-empty string, got {value!r}")
    _check_no_secret(name, value)
    return value


def new_rejection_record(
    *,
    record_id: str,
    category: str,
    suspicion_pattern: str,
    safety_pattern: str,
    reachability_path: Sequence[Mapping[str, str]],
    rejection_reason: str,
    evidence: Mapping[str, str],
    scope: str,
    trace_confidence: str,
    dependencies: Optional[Iterable[str]] = None,
    invalidation_conditions: Iterable[str] = (),
    last_validation: Mapping[str, str] = None,
    reuse_count: int = 0,
) -> dict:
    """Build one `feedback_rejection` record. Raises SchemaError (or a
    subclass) for anything this schema requires and the caller did not
    provide correctly -- this function never silently drops or
    coerces an invalid input into something that merely looks valid.

    `trace_confidence` (context-manifest-schema.md section 5.1,
    "[NEW, closes a third-round Major]"): must be exactly "HIGH" --
    a `reachabilityPath` built from a MEDIUM/LOW-confidence trace must
    never be persisted as a reusable record at all (a truncated or
    inferred chain is MORE permissive to match against than the real
    one, the wrong direction for a check whose entire purpose is to be
    strict). This is enforced HERE, at creation time, not deferred to
    a later "is this reusable" check.
    """
    _require_nonempty_str("record_id", record_id)
    _require_nonempty_str("category", category)
    _require_nonempty_str("suspicion_pattern", suspicion_pattern)
    _require_nonempty_str("safety_pattern", safety_pattern)
    _require_nonempty_str("rejection_reason", rejection_reason)
    _require_nonempty_str("scope", scope)

    if trace_confidence not in TRACE_CONFIDENCE_LEVELS:
        raise SchemaError(f"trace_confidence must be one of {TRACE_CONFIDENCE_LEVELS}, got {trace_confidence!r}")
    if trace_confidence != "HIGH":
        raise SchemaError(
            f"reachabilityPath may only be recorded from a HIGH-confidence trace, got {trace_confidence!r} -- "
            "do not cache this rejection; re-derive it every time it recurs instead"
        )

    normalized_path = _validate_reachability_path(reachability_path)

    if not isinstance(evidence, Mapping) or "path" not in evidence or "observation" not in evidence:
        raise SchemaError(f"evidence must be a mapping with 'path' and 'observation', got {evidence!r}")
    evidence_path = _validate_path(evidence["path"])
    _require_nonempty_str("evidence.observation", evidence["observation"])

    # [ADDED, per a round-1 independent review Minor]: without this,
    # evidence.path (the sink) could point somewhere OUTSIDE
    # reachabilityPath entirely, so dependencies (derived from
    # reachabilityPath) would never include the sink file -- check (c)
    # could then miss a sink-local regression (schema section 5.1's own
    # "covers every file along the verified path by construction"
    # claim depends on the sink actually being the path's own last
    # entry).
    if not paths.same_path(evidence_path, normalized_path[-1]["path"]):
        raise SchemaError(
            f"evidence.path {evidence_path!r} must match reachabilityPath's own last entry "
            f"{normalized_path[-1]['path']!r} -- the sink is, by definition, the end of the path"
        )

    minimum_deps = derive_minimum_dependencies(normalized_path)
    if dependencies is None:
        final_deps = list(minimum_deps)
    else:
        final_deps = [_validate_path(d) for d in dependencies]
        for required in minimum_deps:
            if not any(paths.same_path(required, d) for d in final_deps):
                raise SchemaError(
                    f"dependencies is missing {required!r}, which appears in reachabilityPath -- "
                    "dependencies must be a superset of every reachabilityPath entry, never fewer"
                )

    # [ADDED, Batch 2 preflight, per explicit instruction closing a Round
    # 6 disclosure]: a bare string (or bytes) is iterable character by
    # character in Python -- `invalidation_conditions="flagX"` silently
    # became ['f','l','a','g','X'] (fail-closed downstream, but a
    # nonsense record). Callers must pass a collection of non-empty
    # strings.
    if isinstance(invalidation_conditions, (str, bytes)):
        raise SchemaError(
            "invalidation_conditions must be a collection of non-empty strings, "
            f"not a bare {type(invalidation_conditions).__name__}"
        )
    invalidation_conditions = list(invalidation_conditions)
    for cond in invalidation_conditions:
        _require_nonempty_str("invalidationConditions entry", cond)

    if last_validation is None or not isinstance(last_validation, Mapping):
        raise SchemaError(f"last_validation is required and must be a mapping, got {last_validation!r}")
    validated_by = last_validation.get("validatedBy")
    if validated_by not in VALIDATED_BY_VALUES:
        raise SchemaError(
            f"lastValidation.validatedBy must be one of {VALIDATED_BY_VALUES}, got {validated_by!r} "
            "-- Jev is never a valid value here (v4-design.md section 5's permission boundary)"
        )
    _validate_last_validation_fields(last_validation)

    if not isinstance(reuse_count, int) or isinstance(reuse_count, bool) or reuse_count < 0:
        raise SchemaError(f"reuse_count must be a non-negative int, got {reuse_count!r}")

    record = {
        "recordId": record_id,
        "recordType": RECORD_TYPE_REJECTION,
        "candidateShape": {
            "category": category,
            "suspicionPattern": suspicion_pattern,
            "safetyPattern": safety_pattern,
            "reachabilityPath": normalized_path,
        },
        "rejectionReason": rejection_reason,
        "evidence": {"path": evidence_path, "observation": evidence["observation"]},
        "scope": scope,
        "dependencies": final_deps,
        "lastValidation": dict(last_validation),
        "invalidationConditions": invalidation_conditions,
        "reuseCount": reuse_count,
    }
    # [ADDED, per explicit instruction closing a Round 5 independent
    # review Minor]: the builder validates its OWN output with the same
    # validator every entry point applies, so the two can never drift
    # again (Round 5 found the validator requiring things the builder
    # did not check -- an error that only surfaced later, at append/
    # write time, far from the call that caused it).
    validate_rejection_record(record)
    return record


def _validate_last_validation_fields(last_validation: Mapping) -> None:
    """`timestamp`: required, non-empty string. `commit`: required key;
    a non-empty string OR `null` -- [DECIDED, Option A, per explicit
    instruction closing a Round 5 independent review Minor]: this kit
    documents that a repository with no git (or no commit yet) records
    `gitCommit: null` (`tools/README.md`); requiring a non-empty commit
    here would have made Evidence Reuse unusable for exactly those
    repositories, and `commit` participates in no identity/reuse/
    invalidation/status decision -- it is provenance for a human. An
    empty string or a non-string is still rejected (it is not "unknown",
    it is malformed)."""
    for key in ("timestamp", "commit"):
        if key not in last_validation:
            raise SchemaError(f"lastValidation missing required field {key!r}")
    _require_nonempty_str("lastValidation.timestamp", last_validation["timestamp"])
    commit = last_validation["commit"]
    if commit is not None:
        _require_nonempty_str("lastValidation.commit", commit)


# `status` allowlist. A record with NO `status` key is the one and only
# "active" (reusable-eligible) state; `"STALE"` is the one and only
# non-active state. Any other value -- including `None`, `""`, wrong
# case, or a plausible-looking new word -- is a schema error, never
# silently treated as active (eligibility.py's `decide_reuse` applies
# the same allowlist itself, per the Round 4 trust-boundary fix).
STATUS_STALE = "STALE"
_VALID_STATUS_VALUES = (STATUS_STALE,)


def is_legacy_shaped(record: Any) -> bool:
    """The ONE definition of "legacy (schema-version-1) shaped", shared
    by store.py (which validator to run), identity.py (refuse to match)
    and invalidation.py (audit-only, skipped): a rejection record whose
    `candidateShape.reachabilityPath` has at least one hop where the
    `qualifiedSymbol` KEY IS ABSENT ENTIRELY.

    [CORRECTED, per explicit instruction closing a Round 4 independent
    review Minor]: the Round 3 version of this check ALSO treated a
    present-but-invalid value (`None`, `""`, `123`, a list) as
    legacy-shaped. That was wrong in the fail-open direction for the
    STORE: a corrupted CURRENT record was thereby reclassified as
    "legacy", routed to the lenient audit-only validator, and loaded
    successfully -- instead of failing strict validation and degrading
    the whole store as this package's own corruption policy requires
    ("a single record failing validation degrades the WHOLE store").
    A genuine version-1 record never had the key at all; a record that
    HAS the key but with a bad value is a broken version-2 record, and
    the legacy validator must never be used to paper over that. The
    present-but-invalid case is instead caught by
    `validate_rejection_record`'s own non-empty-string requirement, at
    every entry point (load/write/append/replace/decide_reuse).

    A record too malformed to even inspect (not a mapping, no
    `reachabilityPath` list, a non-mapping hop) is NOT legacy either --
    it is a broken current record and falls through to the strict
    validator, whose own error is the right diagnostic.
    """
    if not isinstance(record, Mapping):
        return False
    shape = record.get("candidateShape")
    if not isinstance(shape, Mapping):
        return False
    reachability_path = shape.get("reachabilityPath")
    if not isinstance(reachability_path, list):
        return False
    return any(isinstance(hop, Mapping) and "qualifiedSymbol" not in hop for hop in reachability_path)


def validate_rejection_record(record: Any) -> None:
    """Re-validate an already-built CURRENT (schema-version-2) record.
    Raises SchemaError on the first problem found. This is the single
    strict trust boundary every entry point applies before treating a
    record as anything other than opaque audit data: `store.load()`,
    `store.write()`, `store.append_rejection_record()`,
    `store.replace_rejection_record()`, and -- so that no caller can
    bypass those -- `eligibility.decide_reuse()` itself (Round 4
    independent review, promoted to Major by explicit instruction: the
    append/replace APIs accepted unvalidated in-memory records, so
    "decide_reuse can only ever see a load()-validated record" was not
    actually true).

    [STRENGTHENED, per a round-1 independent review Minor: the previous
    version did not validate `status`/`reuseCount`/`invalidationConditions`'
    types at all (a hand-edited `"status": "stale"` in the wrong case,
    or `"reuseCount": "x"`, loaded successfully and only broke later,
    inside eligibility.py, in a way store.py's own "load() never
    raises" guarantee did not cover), and did not guard against a
    non-mapping `record`/`candidateShape`/`evidence` before indexing
    into it (an `AttributeError`/`TypeError` instead of a clean
    `SchemaError`).]

    [STRENGTHENED, per explicit instruction closing a Round 4
    independent review Minor: `category`/`suspicionPattern`/
    `safetyPattern` were only checked for KEY PRESENCE -- a hand-edited
    `"category": null` (or `""`, or `0`) passed, and then matched a
    candidate whose category was the same degenerate value. The same
    "key present therefore value valid" mistake had already been found
    twice before in this batch (`qualifiedSymbol`, `dependencies`).
    Every field that participates in identity, reuse, invalidation or
    status decisions is now required to be an actual non-empty string
    (or the exact expected type), and `dependencies`/`reuseCount`/
    `invalidationConditions` are REQUIRED, never defaulted -- a missing
    `dependencies` is not "no dependencies", it is an unusable record.]
    """
    if not isinstance(record, Mapping):
        raise SchemaError(f"rejection record must be a mapping, got {record!r}")
    if record.get("recordType") != RECORD_TYPE_REJECTION:
        raise SchemaError(f"recordType must be {RECORD_TYPE_REJECTION!r}, got {record.get('recordType')!r}")
    for key in (
        "recordId", "candidateShape", "rejectionReason", "evidence", "scope",
        "dependencies", "lastValidation", "invalidationConditions", "reuseCount",
    ):
        if key not in record:
            raise SchemaError(f"rejection record missing required field {key!r}")
    _require_nonempty_str("recordId", record["recordId"])
    _require_nonempty_str("rejectionReason", record["rejectionReason"])
    _require_nonempty_str("scope", record["scope"])

    shape = record["candidateShape"]
    if not isinstance(shape, Mapping):
        raise SchemaError(f"candidateShape must be a mapping, got {shape!r}")
    for key in ("category", "suspicionPattern", "safetyPattern", "reachabilityPath"):
        if key not in shape:
            raise SchemaError(f"candidateShape missing required field {key!r}")
    _require_nonempty_str("candidateShape.category", shape["category"])
    _require_nonempty_str("candidateShape.suspicionPattern", shape["suspicionPattern"])
    _require_nonempty_str("candidateShape.safetyPattern", shape["safetyPattern"])
    _validate_reachability_path(shape["reachabilityPath"])

    evidence = record["evidence"]
    if not isinstance(evidence, Mapping) or "path" not in evidence or "observation" not in evidence:
        raise SchemaError(f"evidence must be a mapping with path/observation, got {evidence!r}")
    evidence_path = _validate_path(evidence["path"])
    _require_nonempty_str("evidence.observation", evidence["observation"])
    if not paths.same_path(evidence_path, shape["reachabilityPath"][-1]["path"]):
        raise SchemaError(
            f"evidence.path {evidence_path!r} must match reachabilityPath's own last entry -- "
            "the sink is, by definition, the end of the path"
        )

    deps = record["dependencies"]
    if not isinstance(deps, list):
        raise SchemaError(f"dependencies must be a list, got {deps!r}")
    if len(deps) == 0:
        raise SchemaError("dependencies must not be empty -- it must at least cover every reachabilityPath entry")
    for d in deps:
        _validate_path(d)  # raises SchemaError for non-str / absolute / '..' / empty
    minimum = derive_minimum_dependencies(shape["reachabilityPath"])
    for required in minimum:
        if not any(paths.same_path(required, d) for d in deps):
            raise SchemaError(f"dependencies is missing {required!r} from reachabilityPath")

    last_validation = record["lastValidation"]
    if not isinstance(last_validation, Mapping):
        raise SchemaError(f"lastValidation must be a mapping, got {last_validation!r}")
    if last_validation.get("validatedBy") not in VALIDATED_BY_VALUES:
        raise SchemaError(f"lastValidation.validatedBy must be one of {VALIDATED_BY_VALUES}, got {last_validation.get('validatedBy')!r}")
    _validate_last_validation_fields(last_validation)

    if "status" in record and record["status"] not in _VALID_STATUS_VALUES:
        raise SchemaError(f"status, if present, must be one of {_VALID_STATUS_VALUES}, got {record['status']!r}")
    if "staleReason" in record:
        _require_nonempty_str("staleReason", record["staleReason"])

    reuse_count = record["reuseCount"]
    if not isinstance(reuse_count, int) or isinstance(reuse_count, bool) or reuse_count < 0:
        raise SchemaError(f"reuseCount must be a non-negative int, got {reuse_count!r}")

    conditions = record["invalidationConditions"]
    if not isinstance(conditions, list):
        raise SchemaError(f"invalidationConditions must be a list, got {conditions!r}")
    for cond in conditions:
        # [CORRECTED, per explicit instruction closing a Round 6
        # independent review Minor]: the same non-empty-string + secret
        # check the builder applies -- previously the validator checked
        # type/emptiness only, so a secret-shaped condition the builder
        # would refuse could be hand-written into a record and pass
        # append/write/load.
        _require_nonempty_str("invalidationConditions entry", cond)

    # [ADDED, same instruction: "no accepted-but-unscanned field may
    # exist"]: the decision taken is ACCEPT unknown top-level keys and
    # extra `lastValidation` keys (forward compatibility; rejecting them
    # would make any additive schema change a hard break for older
    # stores) BUT scan every value in the whole record -- including
    # those unknown keys, nested mappings and lists -- with the same
    # recursive secret heuristic the miss-record validator uses.
    # [UPDATED, Batch 2 preflight]: mapping KEYS are scanned as well now
    # (see `_check_no_secret_recursive`); the earlier "values only"
    # limitation is closed.
    _check_no_secret_recursive("rejectionRecord", record)


def validate_legacy_rejection_record_for_audit(record: Any) -> None:
    """[ADDED, per explicit instruction for the schema-version-2
    migration]: a schema-version-1 record (bare `symbol`, no
    `qualifiedSymbol`) loaded from an old store is kept for AUDIT
    display only -- it is never matched for reuse (identity.py's own
    legacy-schema guard refuses it regardless of this function's
    result). This validator is deliberately lenient: it confirms the
    record is well-formed ENOUGH to display safely (a mapping, with
    the fields a human/tool would want to read), not that it satisfies
    version-2's stricter identity rules -- it never will, and must
    never be silently upgraded to satisfy them (see store.py's own
    "do not guess a qualifiedSymbol" rule).
    """
    if not isinstance(record, Mapping):
        raise SchemaError(f"legacy rejection record must be a mapping, got {record!r}")
    if record.get("recordType") != RECORD_TYPE_REJECTION:
        raise SchemaError(f"recordType must be {RECORD_TYPE_REJECTION!r}, got {record.get('recordType')!r}")
    for key in ("recordId", "candidateShape", "rejectionReason", "evidence", "scope"):
        if key not in record:
            raise SchemaError(f"legacy rejection record missing required field {key!r}")
    shape = record["candidateShape"]
    if not isinstance(shape, Mapping) or "reachabilityPath" not in shape:
        raise SchemaError(f"legacy candidateShape must be a mapping with reachabilityPath, got {shape!r}")
    rp = shape["reachabilityPath"]
    if not isinstance(rp, Sequence) or isinstance(rp, (str, bytes)) or len(rp) == 0:
        raise SchemaError(f"legacy reachabilityPath must be a non-empty list, got {rp!r}")
    for i, entry in enumerate(rp):
        if not isinstance(entry, Mapping) or "path" not in entry:
            raise SchemaError(f"legacy reachabilityPath[{i}] must be a mapping with at least 'path', got {entry!r}")


def new_miss_record(
    *,
    record_id: str,
    layer: str,
    observed_miss: str,
    expected_finding: str,
    prior_layers_passed: Iterable[str],
    evidence: Any,
    remediation: str,
    scope: str,
    human_confirmed_by: str,
    created_at: str,
) -> dict:
    """Build one `feedback_miss` record (v4-design.md section 3.4) --
    NEVER a rejection record. A human-discovered false negative is
    recorded here, never in the rejection-record collection, so this
    package can never accidentally treat a confirmed miss as a cached
    "safe" conclusion.
    """
    if layer not in MISS_LAYERS:
        raise SchemaError(f"layer must be one of {MISS_LAYERS}, got {layer!r}")
    prior_layers_passed = list(prior_layers_passed)
    for p in prior_layers_passed:
        if p not in MISS_LAYERS:
            raise SchemaError(f"prior_layers_passed entry must be one of {MISS_LAYERS}, got {p!r}")
        if p == layer:
            raise SchemaError(
                f"prior_layers_passed must not include the attributed layer itself ({layer!r}) -- "
                "a layer cannot simultaneously be 'passed' (ruled out) and be where the miss is attributed"
            )
    record = {
        "recordId": record_id,
        "recordType": RECORD_TYPE_MISS,
        "layer": layer,
        "observedMiss": observed_miss,
        "expectedFinding": expected_finding,
        "priorLayersPassed": prior_layers_passed,
        "evidence": evidence,
        "remediation": remediation,
        "scope": scope,
        "createdAt": created_at,
        "humanConfirmedBy": human_confirmed_by,
    }
    # The builder validates its own output with the same validator
    # every entry point applies (see new_rejection_record) -- every
    # field/type/secret rule lives in validate_miss_record, once.
    validate_miss_record(record)
    return record


_MISS_STRING_FIELDS = ("recordId", "observedMiss", "expectedFinding", "remediation", "scope", "createdAt", "humanConfirmedBy")


def _validate_miss_evidence(evidence: Any) -> None:
    """A miss record's evidence is one `{path?, observation}` mapping or
    a non-empty list of them. `observation` is required and must be a
    non-empty string (it is what pins the miss to a layer); `path`, when
    present, must be a valid repository-relative path. Anything else
    (None, a bare string, an empty list, a list with a non-mapping) is
    malformed -- `None` in particular is not "no evidence", it is an
    unusable record."""
    if isinstance(evidence, Mapping):
        entries = [evidence]
    elif isinstance(evidence, list) and evidence:
        entries = evidence
    else:
        raise SchemaError(f"evidence must be a {{path?, observation}} mapping or a non-empty list of them, got {evidence!r}")
    for i, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise SchemaError(f"evidence[{i}] must be a mapping, got {entry!r}")
        if "observation" not in entry:
            raise SchemaError(f"evidence[{i}] missing required field 'observation'")
        _require_nonempty_str(f"evidence[{i}].observation", entry["observation"])
        if "path" in entry:
            _validate_path(entry["path"])
    _check_no_secret_recursive("evidence", evidence)


def validate_miss_record(record: Any) -> None:
    """Strict validator for a `feedback_miss` record -- the single rule
    `new_miss_record` (on its own output), `store.append_miss_record`,
    `store.write` and `store.load` all apply.

    [STRENGTHENED, per explicit instruction closing a Round 5
    independent review Minor]: the previous version checked only that
    keys were PRESENT -- the same "key present therefore value valid"
    class this batch has now removed everywhere else -- so
    `append_miss_record` accepted a record `new_miss_record` would have
    refused (empty strings, `evidence: None`, a `password=...` value),
    and it was written to disk. Now: every string field is a non-empty
    string (a bool is never a string; there is no integer field in this
    record type for a bool to impersonate), `layer` is allowlisted,
    `priorLayersPassed` is a list of allowlisted layers not containing
    the attributed layer, `evidence` has the structure above, and the
    recursive secret heuristic runs over every text and nested value.
    """
    if not isinstance(record, Mapping):
        raise SchemaError(f"miss record must be a mapping, got {record!r}")
    if record.get("recordType") != RECORD_TYPE_MISS:
        raise SchemaError(f"recordType must be {RECORD_TYPE_MISS!r}, got {record.get('recordType')!r}")
    for key in _MISS_STRING_FIELDS + ("layer", "priorLayersPassed", "evidence"):
        if key not in record:
            raise SchemaError(f"miss record missing required field {key!r}")
    for key in _MISS_STRING_FIELDS:
        _require_nonempty_str(key, record[key])
    layer = record["layer"]
    if layer not in MISS_LAYERS:
        raise SchemaError(f"layer must be one of {MISS_LAYERS}, got {layer!r}")
    prior = record["priorLayersPassed"]
    if not isinstance(prior, list):
        raise SchemaError(f"priorLayersPassed must be a list, got {prior!r}")
    for p in prior:
        if p not in MISS_LAYERS:
            raise SchemaError(f"priorLayersPassed entry must be one of {MISS_LAYERS}, got {p!r}")
        if p == layer:
            raise SchemaError(
                f"priorLayersPassed must not include the attributed layer itself ({layer!r}) -- "
                "a layer cannot simultaneously be 'passed' (ruled out) and be where the miss is attributed"
            )
    _validate_miss_evidence(record["evidence"])
    _check_no_secret_recursive("missRecord", {k: v for k, v in record.items() if k != "evidence"})
