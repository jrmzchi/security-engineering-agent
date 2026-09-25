"""Manifest validity check -- context-manifest-schema.md section 3.

Applied identically to a Jev-produced or built-in-produced manifest --
there is no separate, more lenient check for either producer (no Jev
producer exists yet in this batch; this module is written so batch 2
can apply it to Jev's output unmodified, per implementation-batches.md
Batch 0's own scope note).

A manifest that fails ANY check is discarded WHOLE, never repaired in
place (see v4-design.md section 4.3: "repairing a partially-wrong
manifest risks silently keeping an unsound piece of it"). This module
enforces that by construction: validate_manifest() never mutates its
input and never returns a "corrected" manifest, only a pass/fail
ValidationResult naming every failed check; the caller's only two moves
on failure are "discard, fall back to the built-in layer" -- there is
no partial-accept path in this API for a caller to misuse.

**Item 0 (independent classification) is NOT performed by this
module.** For TARGETED/QUICK, it is a diff-scoped reasoning pass
(context-manifest-schema.md section 3, item 0) the calling agent
performs, the same way skills/security-change-detection always has --
never reducible to code (see that section's own worked-example
counterexample for why a mechanical version of this check is wrong).
For STANDARD, it is a repo-wide architecture-discovery pass, also
agent-reasoning. Only for DEEP is the floor genuinely, mechanically
recomputable from structured baseline facts -- domains.py's
compute_deep_domains() does exactly that. validate_manifest() therefore
takes the applicable floor as an explicit `floor` argument (a
Classification the caller already produced) rather than computing it
itself -- this is the honest seam between "reasoning the algorithm
document assigns to an agent" and "mechanical checks this module owns
outright" (items 1, 2, 2a, 4, 6, 7, 8 below, plus item 3/5's
*comparison*, once given the floor).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet, List, Mapping, Optional

from . import budget as budget_mod
from . import schema
from .domains import ALL_DOMAINS, compute_deep_domains, Fact


@dataclass(frozen=True)
class Classification:
    """Item 0's (or, for STANDARD, the architecture pass's) own output --
    produced by a reasoning step this module never performs. For DEEP,
    build this via Classification.for_deep() instead, which IS
    mechanically recomputable."""

    sensitivity: Optional[str]  # meaningful for TARGETED only; None otherwise
    implicated_domains: FrozenSet[str]

    @staticmethod
    def for_deep(baseline_facts: Mapping[str, Fact]) -> "Classification":
        result = compute_deep_domains(baseline_facts)
        return Classification(sensitivity=None, implicated_domains=result.domains)


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    failed_checks: List[str] = field(default_factory=list)


SCANNER_DOMAIN_MAP = {
    "code-review": {"semgrep"},
    "web-security": {"semgrep"},
    "api-security": {"semgrep"},
    "authentication": {"semgrep"},
    "authorization": {"semgrep"},
    "data-security": {"semgrep"},
    "file-security": {"semgrep"},
    "configuration-security": {"semgrep", "trivy"},
    "secrets-security": {"gitleaks"},
    "dependency-security": {"osv-scanner", "ecosystem-native"},
}
# scripts/*/scan.* record a skipped/gapped ecosystem-native tool by its
# specific name, not the group name -- see tools/README.md's "Scan
# metadata" section. Any of these satisfies the "ecosystem-native" slot.
_ECOSYSTEM_NATIVE_ALIASES = {"ecosystem-native", "dotnet-list-package", "npm-audit", "pip-audit"}


def _tool_accounted_for(tool: str, selected: set, skipped: set, gaps: set) -> bool:
    names = _ECOSYSTEM_NATIVE_ALIASES if tool == "ecosystem-native" else {tool}
    return bool(names & (selected | skipped | gaps))


def validate_manifest(manifest: Mapping, *, floor: Classification) -> ValidationResult:
    failed: List[str] = []

    def fail(msg: str) -> None:
        failed.append(msg)

    # --- item 1: schema completeness (presence AND type) -----------------
    # [FIXED, per independent review Major]: the schema doc's own item 1
    # requires "no field of the wrong type", not just presence -- an
    # earlier version of this function only checked presence, so a
    # manifest with e.g. scannersSkipped: ["gitleaks"] (a list of plain
    # strings instead of {"tool": ..., "reason": ...} dicts) raised an
    # uncaught TypeError out of item 6 instead of failing validation,
    # and fallbackUsed: "false" (a truthy non-empty string) was silently
    # accepted by item 8. Every required field's type is now checked
    # here, before any later item indexes into it.
    def check_type(value: Any, expected, path: str) -> bool:
        ok = isinstance(value, expected)
        if not ok:
            fail(f"item1: field '{path}' has the wrong type (expected {expected}, got {type(value).__name__})")
        return ok

    if not isinstance(manifest, Mapping):
        return ValidationResult(passed=False, failed_checks=["item1: manifest is not an object"])

    for f in schema.REQUIRED_TOP_LEVEL_FIELDS:
        if f not in manifest:
            fail(f"item1: missing required field '{f}'")
    if failed:
        # Every later check assumes the required shape exists -- bail
        # out now rather than raising KeyError/TypeError deep in
        # item 2/5/6/7/8.
        return ValidationResult(passed=False, failed_checks=failed)

    check_type(manifest["manifestVersion"], str, "manifestVersion")
    check_type(manifest["producedBy"], str, "producedBy")
    check_type(manifest["reviewMode"], str, "reviewMode")
    check_type(manifest["sensitivity"], str, "sensitivity")
    check_type(manifest["reviewBudget"], str, "reviewBudget")
    domains_ok = check_type(manifest["domains"], list, "domains")
    if domains_ok:
        for i, d in enumerate(manifest["domains"]):
            check_type(d, str, f"domains[{i}]")
    scanners_selected_ok = check_type(manifest["scannersSelected"], list, "scannersSelected")
    if scanners_selected_ok:
        for i, t in enumerate(manifest["scannersSelected"]):
            check_type(t, str, f"scannersSelected[{i}]")
    # [FIXED, per a round-2 independent review Minor]: factorsEvidence
    # is OPTIONAL (schema.py), but when present its own shape must still
    # be checked -- an earlier version accepted [""], [None], a bare
    # bool, or a dict in this field with no error, none of which is "a
    # list of short strings" per that field's own definition.
    if "factorsEvidence" in manifest:
        evidence_ok = check_type(manifest["factorsEvidence"], list, "factorsEvidence")
        if evidence_ok:
            for i, e in enumerate(manifest["factorsEvidence"]):
                if check_type(e, str, f"factorsEvidence[{i}]") and not e.strip():
                    fail(f"item1: field 'factorsEvidence[{i}]' is an empty string")
    for field_name in ("scannersSkipped", "coverageGaps"):
        entries_ok = check_type(manifest[field_name], list, field_name)
        if entries_ok:
            for i, entry in enumerate(manifest[field_name]):
                if check_type(entry, Mapping, f"{field_name}[{i}]"):
                    if "tool" not in entry:
                        fail(f"item1: {field_name}[{i}] is missing required field 'tool'")
                    else:
                        check_type(entry["tool"], str, f"{field_name}[{i}].tool")
    target_change_ok = check_type(manifest["targetChange"], Mapping, "targetChange")
    degradation_ok = check_type(manifest["degradation"], Mapping, "degradation")
    if failed or not target_change_ok or not degradation_ok:
        return ValidationResult(passed=False, failed_checks=failed)

    target_change = manifest["targetChange"]
    for f in schema.REQUIRED_TARGET_CHANGE_FIELDS:
        if f not in target_change:
            fail(f"item1: missing required targetChange field '{f}'")
    degradation = manifest["degradation"]
    for f in schema.REQUIRED_DEGRADATION_FIELDS:
        if f not in degradation:
            fail(f"item1: missing required degradation field '{f}'")
    if failed:
        return ValidationResult(passed=False, failed_checks=failed)

    check_type(target_change["files"], list, "targetChange.files")
    check_type(degradation["jevAttempted"], bool, "degradation.jevAttempted")
    check_type(degradation["jevOutcome"], str, "degradation.jevOutcome")
    check_type(degradation["fallbackUsed"], bool, "degradation.fallbackUsed")
    if degradation["fallbackReason"] is not None:
        check_type(degradation["fallbackReason"], str, "degradation.fallbackReason")
    if failed:
        return ValidationResult(passed=False, failed_checks=failed)

    # --- item 2: enum validity ----------------------------------------
    review_mode = manifest["reviewMode"]
    sensitivity = manifest["sensitivity"]
    review_budget = manifest["reviewBudget"]
    produced_by = manifest["producedBy"]
    domains_declared = set(manifest["domains"])

    manifest_version = manifest["manifestVersion"]
    if manifest_version != schema.MANIFEST_VERSION:
        fail(f"item2: unrecognized manifestVersion '{manifest_version}' (expected '{schema.MANIFEST_VERSION}')")
    if review_mode not in budget_mod.REVIEW_MODES:
        fail(f"item2: invalid reviewMode '{review_mode}'")
    if sensitivity not in schema.SENSITIVITIES:
        fail(f"item2: invalid sensitivity '{sensitivity}'")
    if review_budget not in budget_mod.LEVELS:
        fail(f"item2: invalid reviewBudget '{review_budget}'")
    if produced_by not in schema.PRODUCED_BY_VALUES:
        fail(f"item2: invalid producedBy '{produced_by}'")
    for d in domains_declared:
        if d not in ALL_DOMAINS:
            fail(f"item2: invalid domain '{d}'")

    if failed:
        return ValidationResult(passed=False, failed_checks=failed)

    # --- item 2a: reviewMode/sensitivity coupling ----------------------
    if review_mode == "TARGETED" and sensitivity == "N/A":
        fail("item2a: TARGETED reviewMode requires sensitivity != N/A")
    if review_mode in ("QUICK", "STANDARD", "DEEP") and sensitivity != "N/A":
        fail(f"item2a: {review_mode} reviewMode requires sensitivity == N/A, got '{sensitivity}'")

    if failed:
        # Items 3 and 7 both key budget-floor lookups off `sensitivity`
        # when reviewMode is TARGETED; a manifest that already failed
        # the pairing check above cannot be safely used for that lookup
        # (e.g. TARGETED + "N/A" has no starting-point row at all).
        return ValidationResult(passed=False, failed_checks=failed)

    # --- item 3: sensitivity floor (TARGETED only) ---------------------
    if review_mode == "TARGETED":
        floor_sensitivity = floor.sensitivity
        if floor_sensitivity is None:
            # [FIXED, per independent review Minor]: an earlier version
            # silently SKIPPED this check when the caller passed no
            # floor sensitivity, which fails open -- a TARGETED manifest
            # always needs item 0's classification as its floor; a
            # caller that cannot supply one has not actually done item
            # 0 yet, and this must fail closed, not pass by omission.
            fail("item3: TARGETED reviewMode requires a floor.sensitivity to check against; none was given")
        else:
            order = ("NONE", "LOW", "MODERATE", "HIGH")
            if order.index(sensitivity) < order.index(floor_sensitivity):
                fail(
                    f"item3: declared sensitivity '{sensitivity}' is below the "
                    f"independently classified floor '{floor_sensitivity}'"
                )

    # --- item 4: domain non-emptiness -----------------------------------
    if not domains_declared and floor.implicated_domains:
        fail("item4: domains is empty but item 0's classification implicates at least one domain")

    # --- item 5: domain floor --------------------------------------------
    missing_from_floor = floor.implicated_domains - domains_declared
    if missing_from_floor:
        fail(
            "item5: domains is missing floor-required domain(s): "
            + ", ".join(sorted(missing_from_floor))
        )

    # --- item 6: scanner-domain consistency -------------------------------
    selected = set(manifest["scannersSelected"])
    skipped = {entry["tool"] for entry in manifest["scannersSkipped"]}
    gaps = {entry["tool"] for entry in manifest["coverageGaps"]}
    for d in domains_declared:
        for tool in SCANNER_DOMAIN_MAP.get(d, set()):
            if not _tool_accounted_for(tool, selected, skipped, gaps):
                fail(
                    f"item6: domain '{d}' maps to tool '{tool}', which is in none of "
                    "scannersSelected/scannersSkipped/coverageGaps"
                )

    # --- item 7: budget floor ----------------------------------------------
    budget_sensitivity = sensitivity if review_mode == "TARGETED" else None
    if not budget_mod.is_within_floor(review_mode, budget_sensitivity, review_budget):
        lo, hi = budget_mod.legal_range(review_mode, budget_sensitivity)
        fail(
            f"item7: reviewBudget '{review_budget}' is outside the legal movement-cap "
            f"range [{lo}, {hi}] for {review_mode}/{budget_sensitivity}"
        )
    # [FIXED, per independent review Major]: the movement-cap range
    # check above bounds HOW FAR reviewBudget can move, but an earlier
    # version let it move that whole distance with zero recorded
    # justification -- a TARGETED/HIGH manifest could declare FOCUSED
    # (one level below the ELEVATED starting point) with no Factors
    # evidence at all, and an explicit DEEP request could declare
    # MINIMAL (uncapped) the same way, contradicting
    # plays/review-budget.md's own "if the Factors genuinely support
    # it" condition on movement. This does not re-derive whether the
    # cited factors are actually correct (still the calling agent's
    # judgment, same limit as item 0) -- it only requires that SOME
    # justification was recorded whenever reviewBudget moves DOWN from
    # the mechanical starting point (toward less scrutiny).
    #
    # [FIXED, per a round-2 independent review Minor]: an earlier
    # version required evidence for movement in EITHER direction,
    # including MORE conservative (upward) movement -- this contradicts
    # context-manifest-schema.md section 3 item 7's own "not below"
    # framing (only a value below the recomputed floor is a violation)
    # and item 3's parallel "a manifest may declare a higher
    # sensitivity ... never a failure" rule for sensitivity. A
    # more-cautious budget should never need to justify itself, the
    # same way a more-cautious sensitivity or domain set never does
    # elsewhere in this validator -- and in Batch 2, this asymmetry
    # would have let a genuinely more-careful Jev manifest be discarded
    # over missing evidence for being MORE careful, wasting the call
    # for no safety benefit.
    starting = budget_mod.starting_point(review_mode, budget_sensitivity)
    moved_down = budget_mod.level_index(review_budget) < budget_mod.level_index(starting)
    if moved_down and not manifest.get("factorsEvidence"):
        fail(
            f"item7: reviewBudget '{review_budget}' is below the starting point "
            f"'{starting}' for {review_mode}/{budget_sensitivity} but factorsEvidence is empty -- "
            "moving toward less scrutiny requires recording which Factor(s) justify it"
        )

    # --- item 8: degradation field self-consistency --------------------
    jev_outcome = degradation["jevOutcome"]
    jev_attempted = degradation["jevAttempted"]
    if jev_outcome not in schema.JEV_OUTCOMES:
        fail(f"item8: invalid degradation.jevOutcome '{jev_outcome}'")
    else:
        if jev_outcome != "success":
            if not degradation["fallbackUsed"]:
                fail("item8: jevOutcome != success requires fallbackUsed == true")
            if produced_by != "built_in":
                fail("item8: jevOutcome != success requires producedBy == 'built_in'")
        # [FIXED, per independent review Minor]: jevAttempted and
        # jevOutcome must agree -- "no_token" is the one outcome where
        # Jev was never called at all (v4-design.md section 4.3's
        # degradation-path table, outcome 1); every other outcome
        # (success, or one of the four attempted-and-failed reasons)
        # means a call WAS made. An earlier version of this item never
        # checked jevAttempted against anything.
        if jev_outcome == "no_token" and jev_attempted:
            fail("item8: jevOutcome 'no_token' requires jevAttempted == false (no call was ever made)")
        if jev_outcome != "no_token" and not jev_attempted:
            fail(f"item8: jevOutcome '{jev_outcome}' requires jevAttempted == true (a call was made)")

    return ValidationResult(passed=not failed, failed_checks=failed)


def attach_validity(manifest: Mapping, result: ValidationResult) -> dict:
    """Returns a NEW manifest dict with `validity` populated -- never
    mutates the input, and never attaches validity to a manifest this
    module has not itself just validated (call validate_manifest first
    and pass its result here)."""
    out = dict(manifest)
    out["validity"] = {
        "checkedBy": "deterministic_validator",
        "passed": result.passed,
        "failedChecks": list(result.failed_checks),
    }
    return out
