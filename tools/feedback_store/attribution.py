"""Four-layer root-cause attribution for a human-discovered false
negative -- v4-design.md section 3.4.

```text
routing         the classifier/manifest never selected the right
                domain/play for this change at all
attack_surface  the map was missing the entry point, control, or sink
cross_file_flow the flow existed in the map/domain but the multi-hop
                trace didn't connect it
reasoning       everything was in scope and traced correctly, but the
                manual semantic analysis step itself missed the
                vulnerability
```

Each layer is a gate in a fixed DEPENDENCY order (routing must be
confirmed correct before attack-surface completeness is even a
meaningful question; attack-surface completeness before cross-file
connection; that before reasoning) -- but per explicit instruction,
this is not "just pick the first non-null layer": every earlier gate
must have its OWN pass/fail evidence explicitly supplied and confirmed
PASSED before the next gate is even considered, and a gate with no
evidence at all refuses to attribute anything (`AttributionError`)
rather than silently defaulting to any particular layer (routing,
reasoning, or otherwise). Requiring the fail-closed refusal at every
gate is what keeps this from degenerating into "reasoning is the
catch-all bucket for anything ambiguous."
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from . import schema


class AttributionError(ValueError):
    """Insufficient or contradictory evidence to attribute a miss to
    exactly one layer."""


_LAYER_ORDER = ("routing", "attack_surface", "cross_file_flow", "reasoning")


def attribute_layer(
    *,
    routing_correct: Optional[bool],
    attack_surface_complete: Optional[bool] = None,
    cross_file_flow_connected: Optional[bool] = None,
    reasoning_would_catch_it: Optional[bool] = None,
) -> Tuple[str, List[str]]:
    """Each gate argument is the caller's own confirmed verdict: True
    (this gate is ruled out / passed), False (this is where it
    failed), or None (not evidenced). Evaluates gates in dependency
    order; a gate's own verdict is only consulted once every earlier
    gate has been confirmed True. Returns `(layer, prior_layers_passed)`.

    Raises `AttributionError` if:
    - a gate that must be consulted (because every earlier one passed)
      has no evidence (`None`);
    - every gate reports `True` (there is no failing layer at all, so
      this is not a miss to attribute).
    """
    gates = (
        ("routing", routing_correct),
        ("attack_surface", attack_surface_complete),
        ("cross_file_flow", cross_file_flow_connected),
        ("reasoning", reasoning_would_catch_it),
    )
    passed: List[str] = []
    for layer, verdict in gates:
        if verdict is None:
            raise AttributionError(
                f"no evidence supplied for the {layer!r} gate -- refusing to attribute "
                "(every earlier layer must be confirmed passed with evidence, not assumed)"
            )
        # [CORRECTED, per a round-1 independent review Minor]: the
        # previous version only special-cased `is False`, so ANY other
        # non-None value (a string "false", 0, "no") fell through to
        # `passed.append` and was silently treated as "this gate
        # passed" -- including making it possible for a mis-typed
        # gate to be recorded as passed in the resulting record's own
        # `priorLayersPassed`. Require an actual bool.
        if not isinstance(verdict, bool):
            raise AttributionError(
                f"the {layer!r} gate's verdict must be an actual bool (True/False), got {verdict!r} -- "
                "a value that merely looks true/false is never treated as evidence"
            )
        if verdict is False:
            return layer, passed
        passed.append(layer)
    raise AttributionError(
        "all four gates report 'passed' -- there is no failing layer to attribute a miss to; "
        "re-check the evidence, this is not a Feedback miss record situation"
    )


def record_miss(
    *,
    record_id: str,
    routing_correct: Optional[bool],
    attack_surface_complete: Optional[bool] = None,
    cross_file_flow_connected: Optional[bool] = None,
    reasoning_would_catch_it: Optional[bool] = None,
    observed_miss: str,
    expected_finding: str,
    evidence,
    remediation: str,
    scope: str,
    human_confirmed_by: str,
    created_at: str,
) -> dict:
    """Attribute the layer, then build a `feedback_miss` record via
    `schema.new_miss_record` -- the single entry point Batch 1 code
    should use rather than calling `attribute_layer` and
    `schema.new_miss_record` separately and risking the two drifting
    out of sync (e.g. a caller passing a `prior_layers_passed` list
    that doesn't actually match what `attribute_layer` derived).
    """
    layer, prior_layers_passed = attribute_layer(
        routing_correct=routing_correct,
        attack_surface_complete=attack_surface_complete,
        cross_file_flow_connected=cross_file_flow_connected,
        reasoning_would_catch_it=reasoning_would_catch_it,
    )
    return schema.new_miss_record(
        record_id=record_id,
        layer=layer,
        observed_miss=observed_miss,
        expected_finding=expected_finding,
        prior_layers_passed=prior_layers_passed,
        evidence=evidence,
        remediation=remediation,
        scope=scope,
        human_confirmed_by=human_confirmed_by,
        created_at=created_at,
    )
