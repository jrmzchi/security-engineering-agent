"""Manifest orchestrator -- the two-producer entry point. V4 Batch 2.

    Input
      |- Jev usable and its candidate valid  -> Jev producer
      '- otherwise                            -> built-in producer
                                                  |
                                    the SAME validator (Batch 0)
                                                  |
                                     security-review consumer

Responsibilities (and nothing else): decide whether a token is usable;
build the minimal request (jev_adapter) and run the redaction gate; make
exactly one Jev call (jev_client; its timeout is per socket operation,
see jev_client's docstring); parse the candidate (jev_adapter); validate
it with `validator.validate_manifest` against the SAME floor the
built-in producer uses; accept the whole Jev manifest on success, or
discard it WHOLE and run `producer.build_manifest` (Batch 0's built-in
producer -- "the product, not a fallback tier") with the correct
degradation record. Never mixes a partial Jev result into a built-in
manifest. Returns exactly one accepted, validated manifest, or raises
OrchestrationError if even the built-in producer cannot produce a valid
one (never a fabricated success).

Outcome mapping onto the FIXED six-value enum (no seventh value; every
mapping decision is recorded here and in the Batch 2 verification log):

    no token / blank token          -> no_token            (no request built, no call)
    token provider raises           -> no_token            [DESIGN DECISION, disclosed] (no call)
    TARGETED, NONE sensitivity, no
      implicated domain             -> no_token            [DESIGN DECISION, disclosed] (no call)
    request_build_failed (adapter
      rejects the caller input)     -> incomplete_output   [DESIGN DECISION, disclosed] (no call)
    redaction gate refuses request  -> incomplete_output   [DESIGN DECISION, disclosed] (no call)
    client AUTH_REJECTED with
      HTTP 401/403                  -> invalid_token
    client TIMEOUT                  -> timeout
    client INVALID_JSON, adapter
      cannot parse a complete
      candidate (AdapterError)      -> incomplete_output   (OUTPUT COMPLETENESS)
    complete candidate below the
      adapter-side effective floor
      (PolicyFloorError: caller-
      adjusted budget gate, unsure
      sensitivity below the floor)  -> below_floor         (POLICY FLOOR)
    client HTTP_ERROR (422/429/5xx/
      529), TRANSPORT_ERROR, an
      unexpected client exception,
      a non-ClientResult return, an
      unknown outcome, or an
      AUTH_REJECTED without 401/403 -> incomplete_output   [DESIGN DECISION, disclosed]
    adapter raises anything other
      than AdapterError             -> incomplete_output   [DESIGN DECISION, disclosed]
    candidate fails the validator   -> below_floor         (POLICY FLOOR)
    validator / attach_validity
      raises on the Jev candidate   -> below_floor         [DESIGN DECISION, disclosed]
    built-in producer, its
      validation, or attach fails   -> OrchestrationError  (never a fabricated manifest)

The disclosed decisions: the enum has no value for "no usable response
for a non-auth, non-timeout reason" or "request refused before sending".
`incomplete_output` is the closest by the schema's own definition ("Jev
responds but output is incomplete/malformed -> no usable candidate");
the exact cause is preserved in `degradation.fallbackReason` (e.g.
"transport_error: HTTP 529", "request_redaction_refused: key at
state.x; no request sent"), so the audit trail is precise even where
the enum is coarse. Every fallbackReason passes `_safe_reason` first: a
non-string or blank detail becomes a fixed per-outcome default, a
detail containing the token or matching the shared secret heuristic is
withheld, whitespace is collapsed and length is bounded -- so no
injected collaborator can put the token or a secret into the manifest
through a reason string.

`jevAttempted` follows validator item 8, which binds `jevAttempted:
False` to `no_token` and nothing else. Where the Jev path was ENTERED (a
token existed and the request build / redaction step ran) it is `True`
with `incomplete_output`, because that is what happened. Where Jev was
never entered at all -- no token, a token provider that raised
(availability unknown), or the NONE-sensitivity shortcut (a token exists
but there is nothing for Jev to decide) -- it is `False` with
`no_token`, the enum's only never-attempted value, and the actual reason
is stated in `fallbackReason` (e.g. "no live review for a
NONE-sensitivity change ...; Jev not invoked"). So in this package
`no_token` means "Jev was not invoked" and the reason says why; it is
not by itself a claim that no token was configured. A validator that
raises has not passed the candidate, and a candidate that has not passed
is below the floor by definition -- it is never reported as valid. A
future schema revision could add `transport_error` / `request_refused` /
`not_applicable`; that is a design change, not made here.

The line between the two Jev-output outcomes: `incomplete_output` is
for OUTPUT COMPLETENESS -- the response cannot be turned into a
complete, well-formed candidate (unparseable, a missing answer, a wrong
type, a Choice whose probabilities contradict it). `below_floor` is for
the POLICY FLOOR -- the candidate is complete, but a sensitivity,
domain, budget or activity result is below the deterministic floor or
the caller-adjusted budget. Completeness is decided first. Either way
the candidate is discarded WHOLE and the built-in manifest is used;
nothing is clamped or patched. [CORRECTED, outcome-semantic correction
after close-out: the budget gate's refusals were first mapped to
incomplete_output.]

Exception containment is per seam (token provider, request build,
client construction and call, response metadata, parse, validation),
each with its own `audit["stage"]` and the exception TYPE only, never
its message. There is deliberately no blanket handler around the whole
flow: a defect in this module's own logic still surfaces as an
exception instead of being papered over as a fallback.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence

from .. import secret_heuristic
from . import jev_adapter, jev_client, producer, redaction, schema, signal_floor
from .domains import Fact
from .validator import Classification, attach_validity, validate_manifest

TOKEN_ENV_VAR = "TYPESAFE_API_KEY"
_MAX_REASON_CHARS = 400


class OrchestrationError(RuntimeError):
    """Not even the built-in producer could yield a valid manifest --
    surfaced, never papered over with a fabricated manifest."""


@dataclass(frozen=True)
class OrchestrationResult:
    manifest: Dict[str, Any]          # the ONE accepted manifest, `validity` attached
    jev_outcome: str                  # one of schema.JEV_OUTCOMES
    produced_by: str                  # "jev" | "built_in"
    audit: Dict[str, Any] = field(default_factory=dict)  # diagnostics that must NOT live in the manifest


def token_from_env(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """The default token provider: the `TYPESAFE_API_KEY` environment
    variable. Returns None for missing/blank. The value is never logged,
    printed, or stored anywhere but the client."""
    value = (env if env is not None else os.environ).get(TOKEN_ENV_VAR)
    if value is None or not value.strip():
        return None
    return value.strip()


def _safe_reason(text: Any, default: str, token: Optional[str] = None) -> str:
    """A fallbackReason that is always a non-empty string and never
    carries the token or secret-shaped text. [ADDED, Batch 2 independent
    review #7.]"""
    if not isinstance(text, str) or not text.strip():
        return default
    if (token and token in text) or secret_heuristic.looks_like_secret(text):
        return f"{default} (detail withheld: it failed the secret check)"
    text = " ".join(text.split())
    if len(text) > _MAX_REASON_CHARS:
        text = text[:_MAX_REASON_CHARS] + " [truncated]"
    return text


def produce_manifest(
    *,
    review_mode: str,
    target_change_files: Iterable[str] = (),
    classification: Optional[Classification] = None,
    baseline_facts: Optional[Mapping[str, Fact]] = None,
    scope_texts: Optional[Mapping[str, str]] = None,
    factor_adjustment: int = 0,
    factors_evidence: Iterable[str] = (),
    scanner_selection: Optional[tuple] = None,
    review_id: Optional[str] = None,
    produced_at: Optional[str] = None,
    # --- Jev-path inputs (minimum-data, see jev_adapter.AllowedInput) ---
    diff_summary: Optional[str] = None,
    change_summary: Optional[str] = None,
    tech_stack: Sequence[str] = (),
    scanner_availability: Optional[Mapping[str, bool]] = None,
    baseline_summary: Sequence[str] = (),
    attack_surface_summary: Sequence[str] = (),
    reusable_records: Sequence[jev_adapter.ReusableRecordSummary] = (),
    budget_factor_notes: Sequence[str] = (),
    # --- wiring (injected in tests) ---
    token_provider: Callable[[], Optional[str]] = token_from_env,
    client_factory: Callable[[str], Any] = None,
    timeout_seconds: float = jev_client.DEFAULT_TIMEOUT_SECONDS,
) -> OrchestrationResult:
    target_files = tuple(target_change_files)
    signal_reasons: tuple = ()
    # Caller-contract checks, before anything else, so both producers see
    # exactly the same inputs. A bare string is passed through unchanged
    # so the built-in producer raises its own TypeError for it (tuple()
    # would silently split it into characters); any other iterable is
    # materialized ONCE so a generator is not consumed by one producer
    # and seen empty by the other.
    if not isinstance(factor_adjustment, int) or isinstance(factor_adjustment, bool):
        raise TypeError("factor_adjustment must be an int")
    evidence = factors_evidence if isinstance(factors_evidence, (str, bytes)) else tuple(factors_evidence)

    # 0. The applicable floor -- computed ONCE, from the same source the
    #    built-in producer uses, never from anything Jev says.
    if review_mode == "DEEP":
        if baseline_facts is None:
            raise ValueError("DEEP requires baseline_facts")
        floor = Classification.for_deep(baseline_facts)
    else:
        if classification is None:
            raise ValueError(f"{review_mode} requires a caller-supplied Classification")
        # 0a. [V4 release] The deterministic signal floor (signal_floor.py): explicit code signals in the scope can
        #     only ADD a domain to item 0's classification, never remove one. The widened classification is the
        #     floor for BOTH producers, so neither the built-in manifest nor a Jev candidate can drop it.
        if scope_texts is not None:
            extra = signal_floor.required_domains(scope_texts)
            signal_reasons = extra.reasons
            if extra.domains - frozenset(classification.implicated_domains):
                classification = Classification(
                    sensitivity=classification.sensitivity,
                    implicated_domains=frozenset(classification.implicated_domains) | extra.domains,
                )
        floor = classification

    def built_in(degradation: Optional[dict], audit: Dict[str, Any]) -> OrchestrationResult:
        try:
            manifest = producer.build_manifest(
                review_mode=review_mode,
                target_change_files=target_files,
                classification=None if review_mode == "DEEP" else classification,
                baseline_facts=baseline_facts if review_mode == "DEEP" else None,
                factor_adjustment=factor_adjustment,
                factors_evidence=evidence,
                scanner_selection=scanner_selection,
                review_id=review_id,
                produced_at=produced_at,
            )
        except Exception as exc:  # noqa: BLE001
            raise OrchestrationError(f"built-in producer failed: {type(exc).__name__}: {exc}") from exc
        if degradation is not None:
            manifest["degradation"] = degradation
        try:
            result = validate_manifest(manifest, floor=floor)
        except Exception as exc:  # noqa: BLE001 -- a validator crash is never "valid"
            raise OrchestrationError(f"validator raised on the built-in manifest: {type(exc).__name__}") from exc
        if not result.passed:
            raise OrchestrationError(f"built-in manifest failed validation: {result.failed_checks}")
        try:
            final = attach_validity(manifest, result)
        except Exception as exc:  # noqa: BLE001
            raise OrchestrationError(f"attach_validity raised on the built-in manifest: {type(exc).__name__}") from exc
        if signal_reasons:
            audit["signalFloor"] = list(signal_reasons)
        return OrchestrationResult(manifest=final, jev_outcome=final["degradation"]["jevOutcome"], produced_by="built_in", audit=audit)

    # 1. Token.
    try:
        token = token_provider()
    except Exception as exc:  # noqa: BLE001 -- a broken provider must not abort the review
        return built_in(
            schema.new_degradation_no_jev_attempted(f"token provider raised {type(exc).__name__}; Jev not invoked"),
            {"stage": "token_provider_error", "jev_called": False, "exception_type": type(exc).__name__},
        )
    if not isinstance(token, str) or not token.strip():
        # Missing, None, empty, whitespace-only, or not a string: no request is ever built.
        return built_in(None, {"stage": "no_token", "jev_called": False})
    token = token.strip()

    # 1a. Nothing to decide: a NONE-sensitivity change with no implicated
    #     domain has no live review (plays/review-budget.md's Applicability
    #     matrix). When the caller passed `scope_texts`, `floor` already
    #     includes step 0a's signal-floor domains, so a NONE change whose
    #     scope shows the CSRF signal pair is NOT
    #     taken here: it has web-security to review. Otherwise there is no
    #     routing/budget/priority decision for Jev
    #     to contribute to. Calling it would be the "unnecessary
    #     invocation" measurement-plan.md's T1 exists to catch. Recorded
    #     as `no_token` (= "Jev not invoked", see the module docstring)
    #     with the actual reason.
    if review_mode == "TARGETED" and floor.sensitivity == "NONE" and not floor.implicated_domains:
        return built_in(
            schema.new_degradation_no_jev_attempted("no live review for a NONE-sensitivity change with no implicated domain; Jev not invoked"),
            {"stage": "not_applicable", "jev_called": False},
        )

    audit: Dict[str, Any] = {"jev_called": False}

    def fallback(outcome: str, reason: Any, stage: Optional[str] = None) -> OrchestrationResult:
        safe = _safe_reason(reason, default=f"{outcome}: no usable detail", token=token)
        audit["stage"] = stage or outcome
        audit["fallback_reason"] = safe
        return built_in(schema.new_degradation(outcome, fallback_reason=safe), audit)

    # 2. Request (minimum data) + redaction gate.
    inp = jev_adapter.AllowedInput(
        review_mode=review_mode,
        target_files=target_files,
        domain_floor=frozenset(floor.implicated_domains),
        sensitivity_floor=floor.sensitivity if review_mode == "TARGETED" else None,
        diff_summary=diff_summary,
        change_summary=change_summary,
        tech_stack=tuple(tech_stack),
        scanner_availability=dict(scanner_availability or {}),
        baseline_summary=tuple(baseline_summary),
        attack_surface_summary=tuple(attack_surface_summary),
        reusable_records=tuple(reusable_records),
        budget_factor_notes=tuple(budget_factor_notes),
        factor_adjustment=factor_adjustment,
        factors_evidence=evidence,
    )
    try:
        request = jev_adapter.build_request(inp)
    except Exception as exc:  # noqa: BLE001 -- a caller-input problem must not abort the review
        audit["exception_type"] = type(exc).__name__
        return fallback("incomplete_output", f"request_build_failed: {type(exc).__name__}: {exc}; no request sent",
                        stage="request_build_failed")
    refusal = redaction.refuse_if_secret(request.state, request.questions)
    if refusal is not None:
        return fallback("incomplete_output", f"request_redaction_refused: suspected secret ({refusal.describe()}); no request sent",
                        stage="request_redaction_refused")

    # 3. One Jev call.
    try:
        client = (client_factory or (lambda t: jev_client.JevClient(token=t, timeout_seconds=timeout_seconds)))(token)
        audit["jev_called"] = True
        result = client.system_one(request.state, request.questions)
    except Exception as exc:  # noqa: BLE001 -- an unexpected client exception must not abort the review
        audit["exception_type"] = type(exc).__name__
        return fallback("incomplete_output", f"transport_error: unexpected client exception {type(exc).__name__}",
                        stage="client_exception")
    if not isinstance(result, jev_client.ClientResult):
        return fallback("incomplete_output", f"transport_error: client returned {type(result).__name__}, not a ClientResult",
                        stage="client_contract_violation")
    audit["client_outcome"] = result.outcome if isinstance(result.outcome, str) else type(result.outcome).__name__
    audit["client_status"] = result.status if isinstance(result.status, int) else None
    audit["request_id"] = result.request_id if isinstance(result.request_id, str) else None

    if result.outcome == jev_client.AUTH_REJECTED:
        # invalid_token is ONLY for a confirmed authn/authz rejection.
        if result.status not in (401, 403):
            return fallback("incomplete_output", "transport_error: client reported auth_rejected without HTTP 401/403",
                            stage="client_contract_violation")
        return fallback("invalid_token", result.detail)
    if result.outcome == jev_client.TIMEOUT:
        return fallback("timeout", result.detail)
    if result.outcome in (jev_client.HTTP_ERROR, jev_client.TRANSPORT_ERROR):
        detail = result.detail if isinstance(result.detail, str) and result.detail.strip() else "no detail"
        return fallback("incomplete_output", f"transport_error: {detail}")
    if result.outcome == jev_client.INVALID_JSON:
        return fallback("incomplete_output", result.detail)
    if result.outcome != jev_client.OK:
        return fallback("incomplete_output", "transport_error: unknown client outcome", stage="client_contract_violation")

    # 4. Parse the candidate. Response metadata (model, token usage,
    #    which answer keys came back) is recorded for the audit BEFORE
    #    parsing, so a rejected candidate still leaves its cost trail.
    try:
        audit.update(jev_adapter.response_metadata(result.payload))
    except Exception as exc:  # noqa: BLE001 -- metadata is diagnostics only
        audit["metadata_error"] = type(exc).__name__
    try:
        parsed = jev_adapter.parse_response(result.payload, inp, request, scanner_selection=scanner_selection)
    except jev_adapter.PolicyFloorError as exc:
        return fallback("below_floor", str(exc), stage="policy_floor_refused")
    except jev_adapter.AdapterError as exc:
        return fallback("incomplete_output", str(exc))
    except Exception as exc:  # noqa: BLE001
        audit["exception_type"] = type(exc).__name__
        return fallback("incomplete_output", f"adapter raised {type(exc).__name__}", stage="adapter_exception")
    audit["ignored_answer_keys"] = list(parsed.ignored_answer_keys)
    audit["confidences"] = dict(parsed.confidences)
    audit["budget_reference"] = parsed.budget_reference
    if review_id is not None:
        parsed.manifest["reviewId"] = review_id
    if produced_at is not None:
        parsed.manifest["producedAt"] = produced_at

    # 5. The SAME validator, the SAME floor.
    try:
        validation = validate_manifest(parsed.manifest, floor=floor)
        if validation.passed:
            final = attach_validity(parsed.manifest, validation)
    except Exception as exc:  # noqa: BLE001 -- a validator crash is never "valid"
        audit["exception_type"] = type(exc).__name__
        return fallback("below_floor", f"validator raised {type(exc).__name__}; candidate not accepted",
                        stage="validator_exception")
    if not validation.passed:
        return fallback("below_floor", "; ".join(validation.failed_checks))

    # 6. Accept the whole Jev manifest.
    audit["stage"] = "success"
    if signal_reasons:
        audit["signalFloor"] = list(signal_reasons)
    return OrchestrationResult(manifest=final, jev_outcome="success", produced_by="jev", audit=audit)
