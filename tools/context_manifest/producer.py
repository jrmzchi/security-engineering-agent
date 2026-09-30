"""Built-in manifest producer -- v4-design.md section 4.1.

"The no-Jev path is not a fallback tier, it is the product": this is a
full manifest producer in its own right, not a stub. It packages V3's
existing, already-tested classification/scanner-selection/budget
machinery into the Context Manifest shape -- it does not invent new
decision logic, EXCEPT for DEEP's domain set (section 3a's algorithm,
domains.py), which v4-design.md section 4.1 itself names as the one
genuinely new piece.

`sensitivity`/`implicated_domains` for TARGETED/QUICK/STANDARD are NOT
computed by this module -- they are item 0's reasoning-based
classification output (context-manifest-schema.md section 3, item 0),
performed by the calling agent exactly as skills/security-change-detection
already does in V3. This module's `Classification` input IS that
output, handed in by the caller; DEEP is the one review mode where this
module computes the domain set itself, from structured baseline facts,
via domains.py.
"""

from __future__ import annotations

from typing import FrozenSet, Iterable, Mapping, Optional

from . import budget as budget_mod
from . import schema
from .domains import Fact, compute_deep_domains
from .validator import Classification, SCANNER_DOMAIN_MAP


def _auto_scanner_selection(domains_declared: Iterable[str]):
    """Every tool mapped from a selected domain -> scannersSelected;
    every other known tool -> scannersSkipped with a domain-based
    reason, mirroring plays/scanner-selection.md's own
    "-Domains"/"--domains" behavior. A caller with real scanner-
    availability information (a tool relevant but not installed) should
    build scannersSelected/skipped/coverageGaps itself instead of using
    this helper -- it has no way to know about coverage gaps on its
    own.
    """
    all_tools = {"semgrep", "trivy", "gitleaks", "osv-scanner", "ecosystem-native"}
    selected: set = set()
    for d in domains_declared:
        selected |= SCANNER_DOMAIN_MAP.get(d, set())
    skipped = [
        {"tool": t, "reason": f"not relevant to current change (domains: {sorted(domains_declared)})"}
        for t in sorted(all_tools - selected)
    ]
    return sorted(selected), skipped, []


def build_manifest(
    *,
    review_mode: str,
    target_change_files: Iterable[str] = (),
    classification: Optional[Classification] = None,
    baseline_facts: Optional[Mapping[str, Fact]] = None,
    factor_adjustment: int = 0,
    factors_evidence: Iterable[str] = (),
    scanner_selection: Optional[tuple] = None,
    review_id: Optional[str] = None,
    produced_at: Optional[str] = None,
) -> dict:
    """Assemble a Batch 0 (built-in-only) Context Manifest.

    Exactly one of `classification` (TARGETED/QUICK/STANDARD -- item
    0's own reasoning output, produced by the caller) or
    `baseline_facts` (DEEP -- this module computes the floor itself via
    domains.py) must be given, matching which mode is which per
    context-manifest-schema.md section 3's item 5.

    `factors_evidence`: short, non-empty strings naming which of
    plays/review-budget.md's Factors the caller already weighed to
    decide `factor_adjustment` -- required (raises ValueError) whenever
    the resulting reviewBudget moves DOWN from its mechanical starting
    point (toward less scrutiny); never required for moving up (more
    scrutiny never needs to justify itself), per validator.py item 7's
    own check on the OUTPUT side of this same rule. This module does
    not judge whether the cited factors are correct, only that moving
    the budget toward less scrutiny is never silently unjustified.
    """
    if review_mode == "DEEP":
        if baseline_facts is None:
            raise ValueError("DEEP requires baseline_facts (section 3a is computed here, not passed in)")
        classification = Classification.for_deep(baseline_facts)
    elif classification is None:
        raise ValueError(f"{review_mode} requires a caller-supplied Classification (item 0's own output)")

    # [FIXED, per a round-2 independent review Nit]: a bare string is
    # itself iterable character-by-character in Python -- passing
    # factors_evidence="internal tool" instead of ["internal tool"]
    # would otherwise silently explode into a list of single characters
    # with no error at all.
    if isinstance(factors_evidence, str):
        raise TypeError("factors_evidence must be a list of strings, not a bare string")
    # [FIXED, per a round-3 independent review Minor]: an earlier
    # version coerced every element with str(e), which silently
    # accepted None ("None"), a dict, a bool, or bytes -- defeating
    # validator.py item 1's own element type check for this field.
    # Reject non-string/empty elements here instead of stringifying
    # them into something that happens to look valid.
    factors_evidence = list(factors_evidence)
    for e in factors_evidence:
        if not isinstance(e, str) or not e.strip():
            raise TypeError(f"factors_evidence elements must be non-empty strings, got {e!r}")

    sensitivity = classification.sensitivity if review_mode == "TARGETED" else "N/A"
    domains_declared = frozenset(classification.implicated_domains)
    budget_sensitivity = sensitivity if review_mode == "TARGETED" else None

    review_budget = budget_mod.compute_review_budget(
        review_mode, budget_sensitivity, factor_adjustment=factor_adjustment
    )
    # [FIXED, per independent review Major, narrowed per round-2 Minor]:
    # evidence is required only when the budget actually moved DOWN
    # (toward less scrutiny) from its mechanical starting point --
    # matching validator.py item 7's own "not below" framing. Moving up
    # (more cautious) never needs to justify itself, the same way a
    # higher-than-required sensitivity or domain set never does
    # elsewhere in this design.
    starting = budget_mod.starting_point(review_mode, budget_sensitivity)
    moved_down = budget_mod.level_index(review_budget) < budget_mod.level_index(starting)
    if moved_down and not factors_evidence:
        raise ValueError(
            f"reviewBudget moved down from the starting point '{starting}' to '{review_budget}' "
            "with no factors_evidence recorded to justify it"
        )

    if scanner_selection is not None:
        selected, skipped, gaps = scanner_selection
    else:
        selected, skipped, gaps = _auto_scanner_selection(domains_declared)

    manifest = {
        "manifestVersion": schema.MANIFEST_VERSION,
        "producedBy": "built_in",
        "targetChange": schema.new_target_change(files=target_change_files),
        "reviewMode": review_mode,
        "sensitivity": sensitivity,
        "domains": sorted(domains_declared),
        "reviewBudget": review_budget,
        "scannersSelected": selected,
        "scannersSkipped": skipped,
        "coverageGaps": gaps,
        "degradation": schema.new_degradation_no_jev_attempted(),
    }
    if factors_evidence:
        manifest["factorsEvidence"] = factors_evidence
    if review_id is not None:
        manifest["reviewId"] = review_id
    if produced_at is not None:
        manifest["producedAt"] = produced_at
    return manifest
