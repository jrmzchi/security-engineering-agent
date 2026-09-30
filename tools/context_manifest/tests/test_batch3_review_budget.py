"""V4 Batch 3 -- review-budget merged entry point, kit-level.

Batch 3 acceptance (implementation-batches.md, "Batch 3"; waiver of the
Batch 2.5 gate recorded there, 2026-09-25): every existing case in
tests/validation/v3-review-budget-test-cases.md re-verified against the one
entry point (tools/context_manifest/budget.py compute_review_budget, as
plays/review-budget.md's "The single entry point" defines it), including
7/7b's uncapped downward movement; new cases for a built-in manifest and a
Jev-driven manifest requesting a budget through that entry point, for
TARGETED and an explicit mode; single-entry routing shown on every
applicable path; no second computation anywhere.

The case document is a manual/LLM-traced suite. Its cases split into
(a) level assertions, re-executed here against the entry point AND the
built-in producer, and (b) prose-only guarantees (no live review for
NONE/LOW; loading/activity/validation floors; the ELEVATED cross-domain
neighbour), which no function computes -- those are re-traced by hand
against the edited plays in work/v4-planning/batch3-verification-log.md
and are listed here as MANUAL so the inventory stays complete.
"""

from __future__ import annotations

import os
import re
import unittest
from unittest.mock import patch

from .. import budget, jev_client, orchestrator, producer
from ..domains import Fact
from ..validator import Classification, validate_manifest
from .jev_fakes import CountingFactory, FakeJevClient, answer_payload, ok
from .. import jev_adapter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CASES_DOC = os.path.join(REPO, "tests", "validation", "v3-review-budget-test-cases.md")
FAKE_TOKEN = "fake-test-token-not-a-real-credential"

# case id -> (mode, sensitivity, factor_adjustment, expected level) for level assertions, or ("MANUAL", reason)
CASES = {
    "1": ("MANUAL", "NONE: no live review -- Applicability matrix (no computation is ever reached)"),
    "2": ("MANUAL", "LOW: no live review unless escalated -- Applicability matrix"),
    "3": ("TARGETED", "MODERATE", 0, "FOCUSED"),
    "4": ("TARGETED", "HIGH", 0, "ELEVATED"),
    "5": ("TARGETED", "HIGH", +1, "AUDIT"),          # Changed attack-surface centrality moves one level up
    "6": ("TARGETED", "MODERATE", +1, "ELEVATED"),   # Baseline confidence (UNKNOWN auth state) moves one level up
    "7": ("DEEP", None, -3, "MINIMAL"),              # explicit DEEP, nothing sensitive: uncapped down to MINIMAL
    "7b": ("DEEP", None, -3, "MINIMAL"),             # same level; the activity guarantee is MANUAL (see log)
    "8": ("TARGETED", "HIGH", 0, "ELEVATED"),        # the validation/gate floor itself is MANUAL (see log)
    "9": ("QUICK", None, 0, "FOCUSED"),
    "10": ("STANDARD", None, 0, "FOCUSED"),
    "11": ("DEEP", None, 0, "AUDIT"),
    "12": ("TARGETED", "MODERATE", 0, "FOCUSED"),
    "13": ("TARGETED", "HIGH", 0, "ELEVATED"),
    "14": ("TARGETED", "HIGH", 0, "ELEVATED"),       # setup computes ELEVATED; the neighbour handling is MANUAL (see log)
    "15": ("MANUAL", "NONE: no step reaches 'Determine review budget'"),
    "16": ("MANUAL", "LOW, nothing escalates: no budget computation occurs"),
}
_BASELINE = {"authentication": Fact(value=True, confidence="HIGH", source="CODE_EVIDENCE")}


def _document_case_ids():
    text = open(CASES_DOC, encoding="utf-8").read()
    ids = set(re.findall(r"^\| (\d+b?) \|", text, flags=re.M)) | set(re.findall(r"^### Case (\d+b?):", text, flags=re.M))
    return ids


def _classification(sensitivity, domains=("code-review",)):
    return Classification(sensitivity=sensitivity or "HIGH", implicated_domains=frozenset(domains))


def _built_in(mode, sensitivity, adj):
    kw = dict(review_mode=mode, factor_adjustment=adj,
              factors_evidence=["Security-boundary change: none; Blast radius: localized"] if adj < 0 else ())
    if mode == "DEEP":
        kw["baseline_facts"] = _BASELINE
    else:
        kw["classification"] = _classification(sensitivity)
        kw["target_change_files"] = ["src/Data/UserRepository.cs"] if mode == "TARGETED" else []
    return producer.build_manifest(**kw)


class CaseInventoryTests(unittest.TestCase):
    def test_the_actual_case_list_is_the_one_verified_here(self):
        ids = _document_case_ids()
        self.assertEqual(ids, set(CASES), "a case was added to or removed from the case document; update CASES and the log")
        self.assertEqual(len(ids), 17)  # 1..16 plus 7b -- the planning documents' "17" counts 7b

    def test_every_level_case_through_the_entry_point_and_the_built_in_producer(self):
        for cid, spec in CASES.items():
            if spec[0] == "MANUAL":
                continue
            mode, sens, adj, expected = spec
            with self.subTest(case=cid):
                self.assertEqual(budget.compute_review_budget(mode, sens, factor_adjustment=adj), expected)
                m = _built_in(mode, sens, adj)
                self.assertEqual(m["reviewBudget"], expected)
                floor = Classification.for_deep(_BASELINE) if mode == "DEEP" else _classification(sens)
                v = validate_manifest(m, floor=floor)                       # the validator's own legal-range check
                self.assertTrue(v.passed, v.failed_checks)

    def test_7_7b_downward_movement_is_uncapped_only_for_explicit_modes(self):
        self.assertEqual(budget.compute_review_budget("DEEP", None, factor_adjustment=-3), "MINIMAL")
        self.assertEqual(budget.compute_review_budget("STANDARD", None, factor_adjustment=-1), "MINIMAL")
        self.assertEqual(budget.compute_review_budget("TARGETED", "HIGH", factor_adjustment=-3), "FOCUSED")    # capped at one level
        self.assertEqual(budget.compute_review_budget("TARGETED", "MODERATE", factor_adjustment=+3), "ELEVATED")
        self.assertTrue(budget.is_within_floor("DEEP", None, "MINIMAL"))
        self.assertFalse(budget.is_within_floor("TARGETED", "HIGH", "MINIMAL"))
        with self.assertRaises(ValueError):                         # downward movement must name its Factors
            producer.build_manifest(review_mode="DEEP", baseline_facts=_BASELINE, factor_adjustment=-3)

    def test_12_13_are_a_level_discriminating_pair(self):
        self.assertNotEqual(_built_in("TARGETED", "MODERATE", 0)["reviewBudget"], _built_in("TARGETED", "HIGH", 0)["reviewBudget"])


class SingleEntryRoutingTests(unittest.TestCase):
    """Every applicable code path obtains the level from budget.py's one function."""

    def test_the_built_in_producer_calls_the_entry_point(self):
        with patch.object(budget, "compute_review_budget", wraps=budget.compute_review_budget) as spy:
            m = _built_in("TARGETED", "HIGH", 0)
            self.assertEqual(spy.call_count, 1)
            self.assertEqual(m["reviewBudget"], budget.compute_review_budget("TARGETED", "HIGH"))
            spy.reset_mock()
            _built_in("STANDARD", None, 0)
            self.assertEqual(spy.call_count, 1)

    def test_the_jev_path_calls_the_entry_point_and_the_validator_its_legal_range(self):
        client = FakeJevClient(responder=_responder(review_budget="ELEVATED"))
        with patch.object(budget, "compute_review_budget", wraps=budget.compute_review_budget) as spy, \
             patch.object(budget, "is_within_floor", wraps=budget.is_within_floor) as floor:
            r = _jev_run(client, "TARGETED", "HIGH")
        self.assertEqual(r.produced_by, "jev", r.manifest.get("degradation"))
        self.assertEqual(spy.call_count, 2)       # request build + answer check: the caller-adjusted value the Jev answer is held to
        self.assertGreaterEqual(floor.call_count, 1)               # the manifest validator's legal-range check

    def test_no_second_computation_in_code(self):
        pkg = os.path.join(REPO, "tools", "context_manifest")
        table = re.compile(r"""["']MODERATE["']\s*:\s*["']FOCUSED["']|["']HIGH["']\s*:\s*["']ELEVATED["']""")
        for fn in sorted(os.listdir(pkg)):
            if fn.endswith(".py") and fn != "budget.py":
                with self.subTest(module=fn):
                    self.assertIsNone(table.search(open(os.path.join(pkg, fn), encoding="utf-8").read()))

    def test_the_play_is_the_only_prose_authority_and_every_call_site_points_at_it(self):
        play = open(os.path.join(REPO, "plays", "review-budget.md"), encoding="utf-8").read()
        self.assertIn("## The single entry point", play)
        self.assertIn("compute_review_budget(", play)
        rows = re.compile(r"(NONE|LOW|MODERATE|HIGH) sensitivity\s+->|(QUICK|STANDARD|DEEP) \(explicit\)\s+->")
        self.assertTrue(rows.search(play))
        for rel in ("plays/secure-development-workflow.md", "skills/security-review/SKILL.md", "AGENTS.md"):
            text = open(os.path.join(REPO, *rel.split("/")), encoding="utf-8").read()
            with self.subTest(call_site=rel):
                self.assertIsNone(rows.search(text), "a call site restates the starting-point table")
                self.assertIn("single entry point", text)
                self.assertNotIn("compute it directly per that play", text)
                self.assertNotIn("computed here, defined in", text)


def _responder(**decisions):
    defaults = dict(yes_domains={"code-review"}, review_budget="ELEVATED", sensitivity="HIGH")
    defaults.update(decisions)

    def respond(state, questions):
        return ok(answer_payload(jev_adapter.JevRequest(state=state, questions=questions), **defaults))
    return respond


def _jev_run(client, mode, sensitivity, token=FAKE_TOKEN, adj=0):
    kw = dict(review_mode=mode, factor_adjustment=adj, diff_summary="adds a repository query method")
    if mode == "DEEP":
        kw["baseline_facts"] = _BASELINE
    else:
        kw["classification"] = _classification(sensitivity)
        kw["target_change_files"] = ["src/Data/UserRepository.cs"] if mode == "TARGETED" else []
    factory = CountingFactory(client) if client is not None else None
    return orchestrator.produce_manifest(token_provider=lambda: token, client_factory=factory, **kw)


class NewBatch3CasesTests(unittest.TestCase):
    """New cases (Batch 3 criterion 2): a built-in manifest and a Jev-driven manifest each requesting a budget
    through the entry point, for TARGETED and an explicit mode; plus the degraded (no-token / bad-response) modes."""

    def test_built_in_manifest_targeted_and_explicit(self):
        for mode, sens, expected in (("TARGETED", "HIGH", "ELEVATED"), ("STANDARD", None, "FOCUSED"), ("DEEP", None, "AUDIT")):
            with self.subTest(mode=mode):
                r = _jev_run(None, mode, sens, token=None)             # no token: the built-in producer, by construction
                self.assertEqual((r.produced_by, r.jev_outcome), ("built_in", "no_token"))
                self.assertEqual(r.manifest["reviewBudget"], budget.compute_review_budget(mode, sens))
                self.assertEqual(r.manifest["reviewBudget"], expected)
                self.assertTrue(r.manifest["validity"]["passed"])

    def test_jev_manifest_targeted_accepts_a_budget_within_the_legal_range(self):
        r = _jev_run(FakeJevClient(responder=_responder(review_budget="ELEVATED")), "TARGETED", "HIGH")
        self.assertEqual(r.produced_by, "jev")
        self.assertEqual(r.manifest["reviewBudget"], budget.compute_review_budget("TARGETED", "HIGH"))
        r_up = _jev_run(FakeJevClient(responder=_responder(review_budget="AUDIT")), "TARGETED", "HIGH")
        self.assertEqual(r_up.manifest["reviewBudget"], "AUDIT")             # raising is free, within the cap
        self.assertTrue(budget.is_within_floor("TARGETED", "HIGH", r_up.manifest["reviewBudget"]))

    def test_jev_manifest_explicit_mode_is_bounded_by_the_entry_point(self):
        # the Jev level is Jev's own choice (it is NOT computed by the entry point), accepted only inside the
        # entry point's legal range -- for an explicit mode the range is uncapped, so any level is accepted
        for chosen, factor in (("FOCUSED", "none"), ("AUDIT", "none"), ("MINIMAL", "Attacker control")):
            with self.subTest(chosen=chosen):
                r = _jev_run(FakeJevClient(responder=_responder(review_budget=chosen, budget_factor=factor, sensitivity=None)), "STANDARD", None)
                self.assertEqual((r.produced_by, r.manifest["reviewBudget"]), ("jev", chosen), r.manifest.get("degradation"))
                self.assertTrue(budget.is_within_floor("STANDARD", None, chosen))
                self.assertTrue(r.manifest["validity"]["passed"])

    def test_jev_lowering_needs_a_named_factor_and_stays_inside_the_cap(self):
        entry = budget.compute_review_budget("TARGETED", "HIGH")                                        # ELEVATED
        r = _jev_run(FakeJevClient(responder=_responder(review_budget="FOCUSED", budget_factor="none")), "TARGETED", "HIGH")
        self.assertEqual((r.produced_by, r.jev_outcome, r.manifest["reviewBudget"]), ("built_in", "below_floor", entry))
        r2 = _jev_run(FakeJevClient(responder=_responder(review_budget="FOCUSED", budget_factor="Attacker control")), "TARGETED", "HIGH")
        self.assertEqual((r2.produced_by, r2.manifest["reviewBudget"]), ("jev", "FOCUSED"))               # below the entry point, allowed
        self.assertTrue(budget.is_within_floor("TARGETED", "HIGH", "FOCUSED"))
        r3 = _jev_run(FakeJevClient(responder=_responder(review_budget="MINIMAL", budget_factor="Attacker control")), "TARGETED", "HIGH")
        self.assertEqual((r3.produced_by, r3.manifest["reviewBudget"]), ("built_in", entry))              # outside the cap: refused

    def test_degraded_jev_falls_back_to_the_same_entry_point_result(self):
        bad = FakeJevClient(jev_client.ClientResult(outcome=jev_client.INVALID_JSON, status=200, detail="2xx body is not valid JSON"))
        for mode, sens in (("TARGETED", "HIGH"), ("STANDARD", None)):
            with self.subTest(mode=mode):
                r = _jev_run(bad, mode, sens)
                self.assertEqual(r.produced_by, "built_in")
                self.assertTrue(r.manifest["degradation"]["fallbackUsed"])
                self.assertEqual(r.manifest["reviewBudget"], budget.compute_review_budget(mode, sens))


if __name__ == "__main__":
    unittest.main()
