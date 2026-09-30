"""measurement-plan.md's representative task set (T1, T2, T3, T4, T4b,
T5) plus Batch 2's explicit DEEP case, run through BOTH producers with
an injected fake Jev client -- the "representative integration" layer.

This module is deliberately importable by both the unit tests
(test_measurement_tasks.py asserts the invariants) and a small report
runner (`python -m tools.context_manifest.tests.measurement_tasks`
prints the per-task comparison table copied into the verification log).
It uses a FAKE Jev: the recorded "Jev decisions" below are scripted
scenario inputs, not model output -- Batch 2 verifies wiring and a
discernible effect, never a token-cost claim (that is Batch 2.5).

T4/T4b build a real `.security/feedback.json`-shaped record and run
Batch 1's actual `eligibility.decide_reuse` to decide what may be
offered to Jev as reusable intelligence -- the test file (not the
package) is allowed to import tools.feedback_store.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

from .. import jev_adapter, orchestrator, producer
from ..domains import Fact
from ..validator import Classification
from .jev_fakes import CountingFactory, FakeJevClient, answer_payload, ok

FAKE_TOKEN = "fake-test-token-not-a-real-credential"


def _high(value=True) -> Fact:
    return Fact(value=value, confidence="HIGH", source="CODE_EVIDENCE")


# ------------------------------------------------------------------ T4 / T4b intelligence


def _report_download_record(stale: bool):
    """A Batch 1 feedback record for the report-download occurrence; the
    caller (this harness) runs the REAL eligibility check to decide
    whether it may be offered to Jev."""
    from tools.feedback_store import eligibility, schema as fschema, store as fstore

    rec = fschema.new_rejection_record(
        record_id="rec-report-ownership",
        category="BOLA/IDOR",
        suspicion_pattern="object reference from caller-supplied ID with no visible check at the sink",
        safety_pattern="ReportService.GetReport enforces report.OwnerUserId == currentUserId",
        reachability_path=[
            {"path": "src/Controllers/ReportsController.cs", "qualifiedSymbol": "MyApp.Controllers.ReportsController.GetReport(int)"},
            {"path": "src/Services/ReportService.cs", "qualifiedSymbol": "MyApp.Services.ReportService.GetReport(int, int)"},
            {"path": "src/Repositories/ReportRepository.cs", "qualifiedSymbol": "MyApp.Repositories.ReportRepository.FindById(int)"},
        ],
        rejection_reason="cross-file ownership check present in ReportService.GetReport",
        evidence={"path": "src/Repositories/ReportRepository.cs", "observation": "no check at sink; enforced by caller"},
        scope="this path only",
        trace_confidence="HIGH",
        last_validation={"timestamp": "2026-09-23T00:00:00Z", "commit": None, "validatedBy": "code_reviewer_subagent"},
    )
    s = fstore.empty_store()
    fstore.append_rejection_record(s, rec)
    if stale:
        fstore.mark_stale(s, rec["recordId"], reason="central authorization bootstrap changed")
    stored = s["rejectionRecords"][rec["recordId"]]
    decision = eligibility.decide_reuse(
        record=stored,
        candidate_category="BOLA/IDOR",
        candidate_evidence_path="src/Repositories/ReportRepository.cs",
        candidate_reachability_path=stored["candidateShape"]["reachabilityPath"],
        candidate_trace_confidence="HIGH",
        pattern_and_scope_match=True,
        known_condition_states={},
        # T4's change is a NEW caller file (an export action) that reuses
        # the recorded, still-intact Controller->Service->Repository
        # path -- none of the record's own dependencies changed, so
        # check (c) holds. (Touching a recorded dependency would, and
        # must, make the record NOT reusable -- see T4b for the stale
        # variant.)
        changed_files=["src/Controllers/ReportExportController.cs"],
        hop_controls_confirmed={eligibility.hop_key(e["path"], e["qualifiedSymbol"]): True for e in stored["candidateShape"]["reachabilityPath"]},
    )
    offered = ()
    if decision.reusable:
        offered = (jev_adapter.ReusableRecordSummary(stored["recordId"], stored["candidateShape"]["category"], stored["evidence"]["path"]),)
    return offered, decision


# ------------------------------------------------------------------ task definitions


def _deep_facts_for_fixture_pair() -> Dict[str, Fact]:
    """cross_file_object_authz_unsafe + cross_file_sql_unsafe: an ASP.NET
    JSON API (controllers -> services -> repositories over SQL) with no
    server-rendered pages, browser script, redirects or CORS
    registration, and no archive handling. Everything else is UNKNOWN
    (fail open toward applicability). Section 3a therefore rules out
    web-security only -> a 9-domain floor, a real floor to test Jev
    against (not "all ten")."""
    return {
        "no_html_or_script_ever_rendered": _high(),
        "never_uses_cookie_or_ambient_auth_for_state_change": _high(),
        "no_browser_page_produced": _high(),
        "no_browser_side_script_shipped": _high(),
        "no_user_influenced_redirect_issued": _high(),
        "no_cors_headers_or_cross_origin_registration": _high(),
        "no_archive_extraction_or_creation": _high(),
    }


TASKS: Dict[str, Dict[str, Any]] = {
    "T1": dict(
        purpose="NONE-sensitivity interface/no-op case: no Jev call, empty-domain manifest",
        kwargs=dict(review_mode="TARGETED", target_change_files=["styles/main.css"],
                    classification=Classification(sensitivity="NONE", implicated_domains=frozenset()),
                    diff_summary="changes a CSS color"),
        jev=None,
    ),
    "T2": dict(
        purpose="MODERATE, single domain (EF Core query shape)",
        kwargs=dict(review_mode="TARGETED", target_change_files=["Repositories/UserRepository.cs"],
                    classification=Classification(sensitivity="MODERATE", implicated_domains=frozenset({"code-review"})),
                    diff_summary="adds an EF Core FromSqlRaw query with a parameter", tech_stack=("aspnet-core", "ef-core")),
        jev=dict(yes_domains={"code-review", "data-security"}, review_budget="ELEVATED", sensitivity="MODERATE",
                 priorities={"data-security": 3.0, "code-review": 2.0}),
    ),
    "T3": dict(
        purpose="HIGH, single domain (authentication middleware)",
        kwargs=dict(review_mode="TARGETED", target_change_files=["Startup.cs"],
                    classification=Classification(sensitivity="HIGH", implicated_domains=frozenset({"authentication"})),
                    diff_summary="rewrites the authentication middleware registration", tech_stack=("aspnet-core",)),
        jev=dict(yes_domains={"authentication"}, review_budget="FOCUSED", budget_factor="Reversibility", sensitivity="HIGH"),
    ),
    "T4": dict(
        purpose="HIGH with an EXISTING, FRESH reusable Feedback record",
        kwargs=dict(review_mode="TARGETED", target_change_files=["src/Controllers/ReportExportController.cs"],
                    classification=Classification(sensitivity="HIGH", implicated_domains=frozenset({"authorization"})),
                    diff_summary="adds a report export controller reusing ReportService.GetReport"),
        intelligence="fresh",
        jev=dict(yes_domains={"authorization"}, review_budget="ELEVATED", sensitivity="HIGH", reuse_yes={"rec-report-ownership"}),
    ),
    "T4b": dict(
        purpose="same shape as T4 but the record is STALE -> cold/full re-derivation",
        kwargs=dict(review_mode="TARGETED", target_change_files=["src/Controllers/ReportExportController.cs"],
                    classification=Classification(sensitivity="HIGH", implicated_domains=frozenset({"authorization"})),
                    diff_summary="adds a report export controller reusing ReportService.GetReport"),
        intelligence="stale",
        jev=dict(yes_domains={"authorization"}, review_budget="ELEVATED", sensitivity="HIGH", reuse_yes={"rec-report-ownership"}),
    ),
    "T5": dict(
        purpose="HIGH, CROSS-DOMAIN floor stress (authorization + file-security)",
        kwargs=dict(review_mode="TARGETED", target_change_files=["Controllers/ReportsController.cs"],
                    classification=Classification(sensitivity="HIGH", implicated_domains=frozenset({"authorization", "file-security"})),
                    diff_summary="adds an endpoint downloading machine reports by filename"),
        jev=dict(yes_domains={"authorization", "file-security"}, review_budget="AUDIT", sensitivity="HIGH",
                 priorities={"file-security": 3.0, "authorization": 3.0}),
    ),
    "DEEP-fixture-pair": dict(
        purpose="explicit DEEP over cross_file_object_authz_unsafe + cross_file_sql_unsafe; section 3a floor (9 domains)",
        kwargs=dict(review_mode="DEEP", target_change_files=[
            "tests/fixtures/cross_file_object_authz_unsafe/ReportsController.cs",
            "tests/fixtures/cross_file_object_authz_unsafe/ReportService.cs",
            "tests/fixtures/cross_file_object_authz_unsafe/ReportRepository.cs",
            "tests/fixtures/cross_file_sql_unsafe/UsersController.cs",
            "tests/fixtures/cross_file_sql_unsafe/UserSearchService.cs",
            "tests/fixtures/cross_file_sql_unsafe/UserRepository.cs",
        ], baseline_facts=_deep_facts_for_fixture_pair(), tech_stack=("aspnet-core", "sql")),
        jev=dict(yes_domains=None, review_budget="AUDIT", priorities={"authorization": 3.0, "data-security": 3.0, "api-security": 2.0}),
    ),
    "DEEP-fixture-pair-below-floor": dict(
        purpose="same DEEP sample; Jev omits one section-3a-required domain -> below_floor + fallback",
        kwargs=dict(review_mode="DEEP", target_change_files=["tests/fixtures/cross_file_object_authz_unsafe/ReportsController.cs"],
                    baseline_facts=_deep_facts_for_fixture_pair()),
        jev=dict(yes_domains="floor-minus-authorization", review_budget="AUDIT"),
    ),
}


def run_task(name: str) -> Dict[str, Any]:
    task = TASKS[name]
    kwargs = dict(task["kwargs"])
    if task.get("intelligence"):
        offered, decision = _report_download_record(stale=(task["intelligence"] == "stale"))
        kwargs["reusable_records"] = offered
    else:
        decision = None

    # Floor, computed once here for reporting (the orchestrator recomputes its own).
    if kwargs["review_mode"] == "DEEP":
        floor = Classification.for_deep(kwargs["baseline_facts"])
    else:
        floor = kwargs["classification"]

    built_in = orchestrator.produce_manifest(token_provider=lambda: None, **kwargs)

    jev_spec = task["jev"]
    if jev_spec is None:
        client = FakeJevClient(responder=lambda s, q: ok({}))  # must never be reached
        factory = CountingFactory(client)
        jev = orchestrator.produce_manifest(token_provider=lambda: FAKE_TOKEN, client_factory=factory, **kwargs)
    else:
        spec = dict(jev_spec)
        yes = spec.pop("yes_domains")
        if yes is None:
            yes = set(floor.implicated_domains)
        elif yes == "floor-minus-authorization":
            yes = set(floor.implicated_domains) - {"authorization"}

        def respond(state, questions, yes=yes, spec=spec):
            return ok(answer_payload(jev_adapter.JevRequest(state, questions), yes_domains=yes, **spec))

        client = FakeJevClient(responder=respond)
        factory = CountingFactory(client)
        jev = orchestrator.produce_manifest(token_provider=lambda: FAKE_TOKEN, client_factory=factory, **kwargs)

    bm, jm = built_in.manifest, jev.manifest
    diff = {k: (bm.get(k), jm.get(k)) for k in ("sensitivity", "domains", "reviewBudget", "priorityOrder", "intelligenceConsulted", "scannersSelected", "factorsEvidence") if bm.get(k) != jm.get(k)}
    return {
        "task": name,
        "purpose": task["purpose"],
        "floor_domains": sorted(floor.implicated_domains),
        "floor_sensitivity": floor.sensitivity,
        "built_in": {k: bm.get(k) for k in ("sensitivity", "domains", "reviewBudget", "priorityOrder", "intelligenceConsulted", "scannersSelected", "degradation")},
        "jev_path": {k: jm.get(k) for k in ("producedBy", "sensitivity", "domains", "reviewBudget", "priorityOrder", "intelligenceConsulted", "scannersSelected", "degradation")},
        "jev_outcome": jev.jev_outcome,
        "fallback_used": jm["degradation"]["fallbackUsed"],
        "jev_client_calls": len(client.calls),
        "manifest_validation": {"built_in": bm["validity"]["passed"], "jev_path": jm["validity"]["passed"]},
        "domains_superset_of_built_in": set(jm["domains"]) >= set(bm["domains"]),
        "difference": diff,
        "reuse_decision": None if decision is None else {"reusable": decision.reusable, "reasons": decision.reasons},
    }


def run_all() -> List[Dict[str, Any]]:
    return [run_task(n) for n in TASKS]


if __name__ == "__main__":
    json.dump(run_all(), sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
