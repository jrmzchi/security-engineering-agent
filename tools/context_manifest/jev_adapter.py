"""Jev adapter -- typed request construction and response parsing ONLY.
V4 Batch 2.

Jev does not emit a Context Manifest. It answers typed questions
(Choice / Score / Noul -- the only primitives the API offers) about a
`state` object. This adapter therefore:

  build_request(input)   -> the minimal allowed `state` plus a fixed set
                            of typed questions whose answers map 1:1 onto
                            the manifest fields Jev is PERMITTED to
                            influence (v4-design.md section 4.2 / 5):
                            sensitivity (TARGETED), domains (as a floor
                            superset), reviewBudget, priorityOrder,
                            intelligenceConsulted (only records the caller
                            already proved reusable), and the review-budget
                            Factor that justifies a downward budget move.
  parse_response(...)    -> a manifest CANDIDATE dict, or raises one
                            of two DIFFERENT errors:
                            AdapterError -- OUTPUT COMPLETENESS: the
                            response is not an object with `answers`
                            covering every asked question with the right
                            answer type and well-formed, mutually
                            consistent fields (-> incomplete_output);
                            PolicyFloorError -- POLICY FLOOR: the response
                            is a complete, well-formed candidate, but it
                            falls below an effective floor only the
                            adapter can see (the caller-adjusted budget
                            gate; an unsure sensitivity below the floor)
                            (-> below_floor, like a validator failure).
                            Completeness is always decided first: policy
                            refusals are collected while parsing and
                            raised only after EVERY answer has parsed, so
                            a response that is both incomplete and below
                            the floor is incomplete_output. Nothing is guessed, no
                            missing field is filled in, and answers to
                            questions this adapter never asked (a forged
                            "final_verdict") are ignored and REPORTED, never
                            copied into the candidate.

Everything Jev may NOT decide (CONFIRMED findings, exploitability,
attack chains, remediation correctness, Security Gate, skipping
validation or DEEP activities) has no question here, so it has no
channel into the candidate at all. Scanner selection is derived
deterministically from the candidate's domains (Option A: a total
function of the domain set), never asked.

The candidate is NOT validated here -- the orchestrator runs Batch 0's
`validator.validate_manifest` on it, the same check the built-in
producer's output gets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

from . import budget as budget_mod
from . import schema
from .domains import ALL_DOMAINS
from .producer import _auto_scanner_selection

# Docs (confidence.md): below 0.5 "the model is genuinely unsure -- don't
# guess". Applied ASYMMETRICALLY, in the fail-closed direction only: an
# unsure answer may never move the review toward LESS scrutiny (a
# reviewBudget below the caller-adjusted budget -- see the B2 paragraph
# below; originally "below the starting point" -- or a sensitivity below
# what was declared as floor -- the latter the validator rejects anyway).
# An unsure answer that keeps or raises scrutiny is accepted as Jev's
# choice and its confidence is recorded in the audit; the deterministic
# validator, not Jev's confidence, is what guarantees the manifest is
# never below the floor. [CHANGED after the first real smoke test: a
# strict "any low confidence = incomplete_output" rule made the real
# model's 4-option budget Choice fall back almost always, which would
# have left the success path unexercisable while adding no safety --
# the validator already bounds every field.]
#
# [CHANGED, Batch 2 independent review #2/#3, user decision B2]: the
# EXACT comparison object for a budget is the CALLER-ADJUSTED budget --
# `budget.compute_review_budget(review_mode, <sensitivity the candidate
# declares>, caller factor_adjustment)`; when the candidate declares the
# floor sensitivity (the common case) this is exactly the budget the
# built-in producer would emit. Jev may RAISE the budget freely. Jev may
# LOWER it below the caller-adjusted budget only when BOTH its
# review_budget Choice AND its budget_factor Choice have confidence
# >= this threshold (0.5 itself passes) AND it names a real Factor (not
# `none`); otherwise the candidate is refused WHOLE as below_floor
# (PolicyFloorError -- the output is complete; it is below the effective
# floor) and the built-in manifest, carrying the caller-adjusted budget,
# is used; the one field is never clamped. [CORRECTED, outcome-semantic
# correction after close-out: this was first mapped to incomplete_output,
# which is for output-contract failures only.] A
# lowering that passes this gate is still subject to the unchanged,
# producer-independent validator (item 7 legal range + factorsEvidence,
# item 5 domain floor incl. DEEP's Group-1 mandatory activities).
# `factor_adjustment` is caller input only: Jev is never asked for it and
# an answer keyed by it is ignored like any other unasked answer.
MIN_CONFIDENCE_TO_REDUCE_SCRUTINY = 0.5
# A Noul is a probability of "yes"; this is the decision threshold.
NOUL_YES_THRESHOLD = 0.5

# plays/review-budget.md's Factors -- the vocabulary Jev must pick from
# when justifying a DOWNWARD budget move (validator item 7 requires
# recorded factorsEvidence for that). "none" is the explicit no-match
# option the docs recommend; if chosen while the budget moved down, the
# candidate will (correctly) fail item 7 and fall back.
BUDGET_FACTORS = (
    "External exposure",
    "Attacker control",
    "Privilege",
    "Data sensitivity",
    "Blast radius",
    "Reversibility",
    "Changed attack-surface centrality",
)
FACTOR_NONE = "none"

_LEVEL_DESCRIPTIONS = {
    "MINIMAL": "lightweight check only; the change cannot plausibly touch a security boundary",
    "FOCUSED": "targeted review of the directly affected code paths",
    "ELEVATED": "targeted review plus directly connected neighbors of the changed components",
    "AUDIT": "exhaustive review of every path the change can influence",
}
_SENSITIVITY_DESCRIPTIONS = {
    "NONE": "no security relevance at all",
    "LOW": "security-adjacent but no plausible impact",
    "MODERATE": "could affect a security property under some conditions",
    "HIGH": "directly affects authentication, authorization, data exposure, or another security boundary",
}
_PRIORITY_LEVELS = (
    "examine last, if at all beyond the mandatory pass",
    "examine after the primary concerns",
    "examine early",
    "examine first",
)


class AdapterError(ValueError):
    """OUTPUT COMPLETENESS: the Jev response cannot yield a complete,
    well-formed manifest candidate -- unparseable, a missing answer, a
    wrong type, an out-of-range or non-finite number, a Choice whose
    probabilities contradict it (-> jevOutcome incomplete_output).
    `detail` names the failing path; it never includes response content."""


class PolicyFloorError(ValueError):
    """POLICY FLOOR: the Jev response IS a complete, well-formed
    candidate, but it is below an effective floor that only the adapter
    can check -- a reviewBudget below the caller-adjusted budget without
    the confidence and Factor required to lower it, or an unsure
    sensitivity below the floor (-> jevOutcome below_floor, exactly like
    a candidate the validator rejects). Deliberately NOT a subclass of
    AdapterError, so an `except AdapterError` can never absorb it into
    incomplete_output. Raised only after every answer has parsed."""


@dataclass(frozen=True)
class ReusableRecordSummary:
    """The ONLY thing Jev is told about a Feedback record: an id the
    caller has already proven reusable via Batch 1's eligibility checks,
    its category, and its sink path. Never evidence text, never the
    rejection reason."""

    record_id: str
    category: str
    sink_path: str


@dataclass(frozen=True)
class AllowedInput:
    """The minimum-data request surface (batch instruction Part 5)."""

    review_mode: str
    target_files: Tuple[str, ...]
    domain_floor: FrozenSet[str]
    sensitivity_floor: Optional[str] = None      # TARGETED only
    diff_summary: Optional[str] = None
    change_summary: Optional[str] = None
    tech_stack: Tuple[str, ...] = ()
    scanner_availability: Mapping[str, bool] = field(default_factory=dict)
    baseline_summary: Tuple[str, ...] = ()       # short, already-allowed security facts (no values)
    attack_surface_summary: Tuple[str, ...] = ()
    reusable_records: Tuple[ReusableRecordSummary, ...] = ()
    budget_factor_notes: Tuple[str, ...] = ()    # caller's own Factor observations, short strings
    factor_adjustment: int = 0                   # caller's own Factors conclusion (never Jev's)
    factors_evidence: Tuple[str, ...] = ()       # caller's own Factor names justifying factor_adjustment


@dataclass(frozen=True)
class JevRequest:
    state: Dict[str, Any]
    questions: Dict[str, Dict[str, Any]]


@dataclass(frozen=True)
class ParsedCandidate:
    manifest: Dict[str, Any]
    ignored_answer_keys: Tuple[str, ...]
    usage: Mapping[str, Any]
    model: str
    confidences: Mapping[str, float]  # per Choice question, for the audit only
    budget_reference: str = ""        # the caller-adjusted budget the gate compared against


def response_metadata(payload: Any) -> Dict[str, Any]:
    """`model` / `usage` / answer-key list from a raw payload, for the
    orchestrator's audit even when the candidate parse fails. Never the
    answers' content."""
    if not isinstance(payload, Mapping):
        return {}
    usage = payload.get("usage") if isinstance(payload.get("usage"), Mapping) else {}
    return {
        "model": payload.get("model") if isinstance(payload.get("model"), str) else None,
        "usage": {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")},
        "answer_keys": sorted(str(k) for k in payload["answers"]) if isinstance(payload.get("answers"), Mapping) else None,
    }


# --------------------------------------------------------------------- request


def _dedupe_records(records: Sequence[ReusableRecordSummary]) -> Tuple[ReusableRecordSummary, ...]:
    """[ADDED, Batch 2 independent review #9]: one entry per record id,
    first-occurrence order kept (deterministic). Two entries with the
    same id but different content are a caller defect: refused, never
    silently resolved. Error text names indices only, never the id."""
    first_index: Dict[str, int] = {}
    kept: Dict[str, ReusableRecordSummary] = {}
    out: List[ReusableRecordSummary] = []
    for i, r in enumerate(records):
        if not isinstance(r, ReusableRecordSummary):
            raise ValueError(f"reusable_records[{i}] is not a ReusableRecordSummary")
        if not isinstance(r.record_id, str) or not r.record_id.strip():
            raise ValueError(f"reusable_records[{i}].record_id is not a non-empty string")
        if r.record_id in kept:
            if kept[r.record_id] != r:
                raise ValueError(
                    f"reusable_records[{first_index[r.record_id]}] and reusable_records[{i}] share one record id "
                    "but differ in category/sink; refusing to choose one"
                )
            continue
        first_index[r.record_id] = i
        kept[r.record_id] = r
        out.append(r)
    return tuple(out)


def _caller_adjusted_budget(review_mode: str, sensitivity: Optional[str], factor_adjustment: int) -> str:
    return budget_mod.compute_review_budget(review_mode, sensitivity, factor_adjustment=factor_adjustment)


def build_request(inp: AllowedInput) -> JevRequest:
    if inp.review_mode not in budget_mod.REVIEW_MODES:
        raise ValueError(f"unknown review_mode {inp.review_mode!r}")
    for d in inp.domain_floor:
        if d not in ALL_DOMAINS:
            raise ValueError(f"unknown floor domain {d!r}")
    if inp.review_mode == "TARGETED" and inp.sensitivity_floor not in budget_mod.SENSITIVITIES:
        raise ValueError("TARGETED requires a sensitivity_floor")
    if not isinstance(inp.factor_adjustment, int) or isinstance(inp.factor_adjustment, bool):
        raise ValueError("factor_adjustment must be an int")
    if isinstance(inp.factors_evidence, (str, bytes)) or any(
        not isinstance(e, str) or not e.strip() for e in inp.factors_evidence
    ):
        raise ValueError("factors_evidence must be a sequence of non-empty strings")
    records = _dedupe_records(inp.reusable_records)

    budget_sensitivity = inp.sensitivity_floor if inp.review_mode == "TARGETED" else None
    lo, hi = budget_mod.legal_range(inp.review_mode, budget_sensitivity)
    starting = budget_mod.starting_point(inp.review_mode, budget_sensitivity)
    caller_adjusted = _caller_adjusted_budget(inp.review_mode, budget_sensitivity, inp.factor_adjustment)

    state: Dict[str, Any] = {
        "review_mode": inp.review_mode,
        "changed_paths": list(inp.target_files),
        "deterministic_floor": {
            "domains_required": sorted(inp.domain_floor),
            "sensitivity_required": inp.sensitivity_floor,
            "review_budget_starting_point": starting,
            "review_budget_legal_range": [lo, hi],
            "review_budget_caller_adjusted": caller_adjusted,
        },
    }
    if inp.diff_summary:
        state["diff_summary"] = inp.diff_summary
    if inp.change_summary:
        state["change_summary"] = inp.change_summary
    if inp.tech_stack:
        state["tech_stack"] = list(inp.tech_stack)
    if inp.scanner_availability:
        state["scanner_availability"] = {k: bool(v) for k, v in inp.scanner_availability.items()}
    if inp.baseline_summary:
        state["baseline_security_facts"] = list(inp.baseline_summary)
    if inp.attack_surface_summary:
        state["attack_surface_summary"] = list(inp.attack_surface_summary)
    if inp.budget_factor_notes:
        state["review_budget_factor_notes"] = list(inp.budget_factor_notes)
    if records:
        state["reusable_intelligence"] = [
            {"record_id": r.record_id, "category": r.category, "sink_path": r.sink_path}
            for r in records
        ]

    questions: Dict[str, Dict[str, Any]] = {}
    if inp.review_mode == "TARGETED":
        questions["sensitivity"] = {
            "type": "choice",
            "instructions": (
                "Which security sensitivity level does this change have? It must not be below "
                f"`deterministic_floor.sensitivity_required` ({inp.sensitivity_floor}); choosing a higher level is allowed."
            ),
            "criteria": dict(_SENSITIVITY_DESCRIPTIONS),
        }
    for d in ALL_DOMAINS:
        questions[f"domain_{d}"] = {
            "type": "noul",
            "instructions": (
                f"Is the security domain `{d}` implicated by this change? Every domain listed in "
                "`deterministic_floor.domains_required` is implicated by definition; you may add others."
            ),
        }
        questions[f"priority_{d}"] = {
            "type": "score",
            "instructions": f"If `{d}` is reviewed, how early should it be examined relative to the other domains?",
            "criteria": list(_PRIORITY_LEVELS),
        }
    questions["review_budget"] = {
        "type": "choice",
        "instructions": (
            "How much review effort does this change justify? The answer must lie within "
            "`deterministic_floor.review_budget_legal_range`; the starting point is "
            "`deterministic_floor.review_budget_starting_point`, and the caller's own Factors analysis already "
            "concluded `deterministic_floor.review_budget_caller_adjusted`. Choosing a lower level than that "
            "conclusion requires a clear Factor; choosing a higher level is always allowed."
        ),
        "criteria": {level: _LEVEL_DESCRIPTIONS[level] for level in budget_mod.LEVELS},
    }
    questions["budget_factor"] = {
        "type": "choice",
        "instructions": (
            "Which review-budget Factor most justifies your review_budget choice? Choose `none` if no Factor "
            "supports moving below `deterministic_floor.review_budget_caller_adjusted`."
        ),
        "criteria": {**{f: None for f in BUDGET_FACTORS}, FACTOR_NONE: "no Factor supports a lower budget"},
    }
    for r in records:
        questions[f"reuse_{r.record_id}"] = {
            "type": "noul",
            "instructions": (
                f"Is the already-validated intelligence record `{r.record_id}` (category `{r.category}`, sink "
                f"`{r.sink_path}`) relevant to this change and worth consulting?"
            ),
        }
    return JevRequest(state=state, questions=questions)


# -------------------------------------------------------------------- response


def _require(cond: bool, detail: str) -> None:
    if not cond:
        raise AdapterError(detail)


def _is_number(x: Any) -> bool:
    # json.loads accepts NaN / Infinity literals; neither is a probability.
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _answer(answers: Mapping[str, Any], key: str, expected_type: str) -> Mapping[str, Any]:
    _require(key in answers, f"answers.{key} missing")
    ans = answers[key]
    _require(isinstance(ans, Mapping), f"answers.{key} is not an object")
    _require(ans.get("type") == expected_type, f"answers.{key}.type is not {expected_type!r}")
    return ans


def _choice(answers: Mapping[str, Any], key: str, criteria: Mapping[str, Any]) -> Tuple[str, float]:
    ans = _answer(answers, key, "choice")
    choice = ans.get("choice")
    _require(isinstance(choice, str) and choice in criteria, f"answers.{key}.choice is not one of the offered criteria")
    confidence = ans.get("confidence")
    _require(_is_number(confidence) and 0.0 <= confidence <= 1.0, f"answers.{key}.confidence is not a number in [0, 1]")
    probs = ans.get("probabilities")
    _require(isinstance(probs, Mapping) and probs, f"answers.{key}.probabilities missing")
    # Official contract (primitives/choice.md, re-read 2026-09-23):
    # `choice` is the option with the highest probability; `probabilities`
    # is the full distribution across EVERY option and sums to 1. The docs
    # define no tie rule, so a tie at the top is refused rather than
    # resolved here. [ADDED, Batch 2 independent review #8.]
    for k in probs:
        _require(k in criteria, f"answers.{key}.probabilities has an unknown option")
    _require(all(k in probs for k in criteria), f"answers.{key}.probabilities does not cover every offered option")
    total = 0.0
    for k, v in probs.items():
        _require(_is_number(v) and 0.0 <= v <= 1.0, f"answers.{key}.probabilities.{k} is not a finite number in [0, 1]")
        total += float(v)
    _require(abs(total - 1.0) <= 0.05, f"answers.{key}.probabilities do not sum to 1")
    top = max(float(v) for v in probs.values())
    leaders = [k for k, v in probs.items() if float(v) == top]
    _require(len(leaders) == 1, f"answers.{key}.probabilities has a tie at the top; the contract defines no tie rule")
    _require(leaders[0] == choice, f"answers.{key}.choice is not the highest-probability option")
    return choice, float(confidence)


def _noul(answers: Mapping[str, Any], key: str) -> float:
    ans = _answer(answers, key, "noul")
    value = ans.get("noul")
    _require(_is_number(value) and 0.0 <= value <= 1.0, f"answers.{key}.noul is not a number in [0, 1]")
    return float(value)


def _score(answers: Mapping[str, Any], key: str, levels: int) -> float:
    ans = _answer(answers, key, "score")
    value = ans.get("score")
    _require(_is_number(value) and 0.0 <= value <= levels - 1, f"answers.{key}.score is not a number within the offered levels")
    confidence = ans.get("confidence")
    _require(_is_number(confidence) and 0.0 <= confidence <= 1.0, f"answers.{key}.confidence is not a number in [0, 1]")
    return float(value)


def parse_response(
    payload: Any,
    inp: AllowedInput,
    request: JevRequest,
    *,
    scanner_selection: Optional[tuple] = None,
) -> ParsedCandidate:
    """Turn a raw 2xx JSON object into a manifest candidate, or raise
    AdapterError (incomplete) / PolicyFloorError (complete but below the
    effective floor). Never repairs, never defaults a missing answer,
    never clamps a field."""
    _require(isinstance(payload, Mapping), "response is not an object")
    model = payload.get("model")
    _require(isinstance(model, str) and model.strip(), "response.model missing")
    answers = payload.get("answers")
    _require(isinstance(answers, Mapping), "response.answers missing or not an object")
    usage = payload.get("usage")
    _require(isinstance(usage, Mapping), "response.usage missing or not an object")

    asked = set(request.questions)
    ignored = tuple(sorted((k for k in answers if k not in asked), key=repr))  # forged/over-scope answers: reported, never used

    confidences: Dict[str, float] = {}
    # Policy-floor refusals are COLLECTED, not raised, until every answer
    # has parsed -- completeness is decided first (see module docstring).
    policy_refusals: List[str] = []

    # sensitivity (TARGETED only). An unsure answer BELOW the floor is a
    # policy-floor refusal (the validator's item 3 would refuse it too);
    # unsure at or above the floor is accepted.
    if inp.review_mode == "TARGETED":
        sensitivity, conf = _choice(answers, "sensitivity", request.questions["sensitivity"]["criteria"])
        confidences["sensitivity"] = conf
        order = ("NONE", "LOW", "MODERATE", "HIGH")
        if conf < MIN_CONFIDENCE_TO_REDUCE_SCRUTINY and order.index(sensitivity) < order.index(inp.sensitivity_floor):
            policy_refusals.append(
                f"model unsure (sensitivity confidence {conf!r} < {MIN_CONFIDENCE_TO_REDUCE_SCRUTINY}) while "
                f"declaring a sensitivity below the floor {inp.sensitivity_floor}"
            )
    else:
        sensitivity = "N/A"

    # domains: Jev's own yes/no per domain -- NOT unioned with the floor
    # here. The floor is INPUT (Jev was told it); if Jev still says no
    # to a floor domain, the candidate genuinely lacks it and the
    # validator's item 5 will (correctly) reject it as below_floor.
    domains = [d for d in ALL_DOMAINS if _noul(answers, f"domain_{d}") >= NOUL_YES_THRESHOLD]

    # priorityOrder: chosen domains ordered by Jev's per-domain score
    # (higher = earlier), ties broken by the canonical domain order --
    # generic adapter behaviour, no domain is ever dropped.
    scores = {d: _score(answers, f"priority_{d}", len(_PRIORITY_LEVELS)) for d in ALL_DOMAINS}
    priority_order = sorted(domains, key=lambda d: (-scores[d], ALL_DOMAINS.index(d)))

    review_budget, conf = _choice(answers, "review_budget", request.questions["review_budget"]["criteria"])
    confidences["review_budget"] = conf
    factor, factor_conf = _choice(answers, "budget_factor", request.questions["budget_factor"]["criteria"])
    confidences["budget_factor"] = factor_conf

    # The budget gate (see MIN_CONFIDENCE_TO_REDUCE_SCRUTINY). The
    # reference is keyed off the DECLARED sensitivity (what the
    # validator's item 7 uses), not the floor -- Jev may lawfully declare
    # a higher sensitivity than the floor, which moves the starting point
    # and therefore the caller-adjusted budget up with it.
    budget_sensitivity = sensitivity if inp.review_mode == "TARGETED" else None
    reference = _caller_adjusted_budget(inp.review_mode, budget_sensitivity, inp.factor_adjustment)
    lowered = budget_mod.level_index(review_budget) < budget_mod.level_index(reference)
    if lowered:
        if conf < MIN_CONFIDENCE_TO_REDUCE_SCRUTINY:
            policy_refusals.append(
                f"model unsure (review_budget confidence {conf!r} < {MIN_CONFIDENCE_TO_REDUCE_SCRUTINY}) while "
                f"lowering reviewBudget {review_budget} below the caller-adjusted budget {reference}; an unsure answer may not reduce scrutiny"
            )
        if factor == FACTOR_NONE:
            policy_refusals.append(
                f"reviewBudget {review_budget} lowered below the caller-adjusted budget {reference} with budget_factor `none`"
            )
        elif factor_conf < MIN_CONFIDENCE_TO_REDUCE_SCRUTINY:
            policy_refusals.append(
                f"model unsure (budget_factor confidence {factor_conf!r} < {MIN_CONFIDENCE_TO_REDUCE_SCRUTINY}) "
                f"about the Factor justifying reviewBudget {review_budget} below the caller-adjusted budget {reference}"
            )

    records = _dedupe_records(inp.reusable_records)
    consulted = [
        r.record_id for r in records
        if _noul(answers, f"reuse_{r.record_id}") >= NOUL_YES_THRESHOLD
    ]

    # Every answer has parsed: the output is complete. Only now may a
    # policy-floor refusal be reported -- the whole candidate is refused.
    if policy_refusals:
        raise PolicyFloorError("policy_floor: " + "; ".join(policy_refusals))

    if scanner_selection is not None:
        selected, skipped, gaps = scanner_selection
    else:
        selected, skipped, gaps = _auto_scanner_selection(domains)

    target_change = schema.new_target_change(
        files=list(inp.target_files),
        **{k: v for k, v in (
            ("diffSummary", inp.diff_summary),
            ("techStack", list(inp.tech_stack) if inp.tech_stack else None),
            ("scannerAvailability", dict(inp.scanner_availability) if inp.scanner_availability else None),
        ) if v is not None},
    )
    manifest: Dict[str, Any] = {
        "manifestVersion": schema.MANIFEST_VERSION,
        "producedBy": "jev",
        "targetChange": target_change,
        "reviewMode": inp.review_mode,
        "sensitivity": sensitivity,
        "domains": sorted(domains),
        "reviewBudget": review_budget,
        "scannersSelected": selected,
        "scannersSkipped": skipped,
        "coverageGaps": gaps,
        "degradation": schema.new_degradation("success", fallback_reason=None),
    }
    if priority_order:
        manifest["priorityOrder"] = priority_order
    if consulted:
        manifest["intelligenceConsulted"] = {
            "baselineFactsUsed": [],
            "attackSurfaceNodesUsed": [],
            "feedbackRecordsConsulted": consulted,
        }
    # factorsEvidence: the caller's own evidence (the same list the
    # built-in producer records), plus Jev's Factor when -- and only
    # when -- Jev lowered the budget below the caller's conclusion (the
    # gate above guarantees that Factor is real and confident). If the
    # result is below the starting point with no evidence at all,
    # validator item 7 rejects it (below_floor), the honest result.
    evidence = list(inp.factors_evidence)
    if lowered and factor not in evidence:
        evidence.append(factor)
    if evidence:
        manifest["factorsEvidence"] = evidence

    return ParsedCandidate(
        manifest=manifest,
        ignored_answer_keys=ignored,
        usage={"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")},
        model=model,
        confidences=confidences,
        budget_reference=reference,
    )
