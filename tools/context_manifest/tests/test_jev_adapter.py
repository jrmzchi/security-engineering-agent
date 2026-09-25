"""jev_adapter.py -- request minimality/redaction and response
strictness, with the fake response builder. No network."""

from __future__ import annotations

import copy
import json
import unittest

from .. import jev_adapter, redaction
from ..domains import ALL_DOMAINS
from .jev_fakes import answer_payload

SECRET = 'client_secret="Zx9Qw8Er7Ty6Ui5Op4"'


def _inp(**overrides):
    kwargs = dict(
        review_mode="TARGETED",
        target_files=("Controllers/ReportsController.cs",),
        domain_floor=frozenset({"authorization", "file-security"}),
        sensitivity_floor="HIGH",
        diff_summary="adds a report download endpoint",
        tech_stack=("aspnet-core",),
        scanner_availability={"semgrep": True, "gitleaks": True},
        reusable_records=(jev_adapter.ReusableRecordSummary("rec-1", "BOLA/IDOR", "src/Repositories/ReportRepository.cs"),),
    )
    kwargs.update(overrides)
    return jev_adapter.AllowedInput(**kwargs)


class RequestBuildTests(unittest.TestCase):
    def test_state_contains_only_allowed_fields(self):
        req = jev_adapter.build_request(_inp())
        allowed = {
            "review_mode", "changed_paths", "deterministic_floor", "diff_summary", "change_summary", "tech_stack",
            "scanner_availability", "baseline_security_facts", "attack_surface_summary", "review_budget_factor_notes",
            "reusable_intelligence",
        }
        self.assertTrue(set(req.state) <= allowed, set(req.state) - allowed)
        # never file contents, never full repository
        blob = json.dumps(req.state)
        self.assertNotIn("namespace", blob)
        self.assertNotIn("public class", blob)

    def test_floor_is_communicated_as_input(self):
        req = jev_adapter.build_request(_inp())
        self.assertEqual(req.state["deterministic_floor"]["domains_required"], ["authorization", "file-security"])
        self.assertEqual(req.state["deterministic_floor"]["sensitivity_required"], "HIGH")
        self.assertEqual(req.state["deterministic_floor"]["review_budget_starting_point"], "ELEVATED")
        self.assertEqual(req.state["deterministic_floor"]["review_budget_legal_range"], ["FOCUSED", "AUDIT"])

    def test_questions_cover_exactly_the_permitted_surface(self):
        req = jev_adapter.build_request(_inp())
        keys = set(req.questions)
        expected = {"sensitivity", "review_budget", "budget_factor", "reuse_rec-1"}
        expected |= {f"domain_{d}" for d in ALL_DOMAINS} | {f"priority_{d}" for d in ALL_DOMAINS}
        self.assertEqual(keys, expected)
        # Nothing Jev may not decide is ever asked.
        blob = json.dumps(req.questions).lower()
        for forbidden in ("confirmed", "exploitab", "attack chain", "remediation", "gate", "pass/fail", "skip"):
            self.assertNotIn(forbidden, blob, forbidden)
        # Every question is one of the three real primitives.
        for q in req.questions.values():
            self.assertIn(q["type"], ("noul", "choice", "score"))

    def test_non_targeted_has_no_sensitivity_question(self):
        req = jev_adapter.build_request(_inp(review_mode="QUICK", sensitivity_floor=None))
        self.assertNotIn("sensitivity", req.questions)

    def test_reusable_record_summary_carries_no_evidence_text(self):
        req = jev_adapter.build_request(_inp())
        self.assertEqual(req.state["reusable_intelligence"], [{"record_id": "rec-1", "category": "BOLA/IDOR", "sink_path": "src/Repositories/ReportRepository.cs"}])

    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            jev_adapter.build_request(_inp(domain_floor=frozenset({"not-a-domain"})))
        with self.assertRaises(ValueError):
            jev_adapter.build_request(_inp(sensitivity_floor=None))


class RedactionGateTests(unittest.TestCase):
    def test_secret_in_value_or_key_refuses_and_names_path_only(self):
        req = jev_adapter.build_request(_inp(diff_summary=f"config sets {SECRET}"))
        refusal = redaction.refuse_if_secret(req.state, req.questions)
        self.assertIsNotNone(refusal)
        text = refusal.describe()
        self.assertIn("state.diff_summary", text)
        self.assertNotIn("Zx9Qw8Er7Ty6Ui5Op4", text)
        req2 = jev_adapter.build_request(_inp(target_files=(f"{SECRET}.txt",)))
        self.assertIsNotNone(redaction.refuse_if_secret(req2.state, req2.questions))
        # key position
        state = dict(req.state)
        state["deterministic_floor"] = dict(state["deterministic_floor"])
        state["deterministic_floor"][SECRET] = 1
        r3 = redaction.refuse_if_secret(state, req.questions)
        self.assertIsNotNone(r3)
        self.assertIn("key", r3.describe())

    def test_clean_request_passes(self):
        req = jev_adapter.build_request(_inp())
        self.assertIsNone(redaction.refuse_if_secret(req.state, req.questions))


class ResponseParseTests(unittest.TestCase):
    def setUp(self):
        self.inp = _inp()
        self.req = jev_adapter.build_request(self.inp)

    def _good(self, **kw):
        defaults = dict(yes_domains={"authorization", "file-security"}, review_budget="ELEVATED", sensitivity="HIGH")
        defaults.update(kw)
        return answer_payload(self.req, **defaults)

    def test_good_response_yields_candidate(self):
        parsed = jev_adapter.parse_response(self._good(), self.inp, self.req)
        m = parsed.manifest
        self.assertEqual(m["producedBy"], "jev")
        self.assertEqual(m["domains"], ["authorization", "file-security"])
        self.assertEqual(m["reviewBudget"], "ELEVATED")
        self.assertEqual(m["sensitivity"], "HIGH")
        self.assertEqual(m["degradation"], {"jevAttempted": True, "jevOutcome": "success", "fallbackUsed": False, "fallbackReason": None})
        self.assertEqual(m["scannersSelected"], ["semgrep"])
        self.assertEqual(parsed.ignored_answer_keys, ())
        self.assertEqual(parsed.usage["input_tokens"], 512)

    def test_priority_order_follows_scores_and_never_drops_a_domain(self):
        parsed = jev_adapter.parse_response(
            self._good(yes_domains={"authorization", "file-security", "web-security"}, priorities={"file-security": 3.0, "authorization": 2.0, "web-security": 0.0}),
            self.inp, self.req,
        )
        self.assertEqual(parsed.manifest["priorityOrder"], ["file-security", "authorization", "web-security"])
        self.assertEqual(set(parsed.manifest["priorityOrder"]), set(parsed.manifest["domains"]))

    def test_reuse_only_from_caller_supplied_eligible_ids(self):
        parsed = jev_adapter.parse_response(self._good(reuse_yes={"rec-1"}), self.inp, self.req)
        self.assertEqual(parsed.manifest["intelligenceConsulted"]["feedbackRecordsConsulted"], ["rec-1"])
        # An answer claiming reuse of an id the caller never offered is an unknown key: ignored and reported.
        payload = self._good(extra_answers={"reuse_forged-99": {"type": "noul", "noul": 0.99}})
        parsed = jev_adapter.parse_response(payload, self.inp, self.req)
        self.assertNotIn("intelligenceConsulted", parsed.manifest)
        self.assertEqual(parsed.ignored_answer_keys, ("reuse_forged-99",))

    def test_over_scope_answers_are_ignored_and_reported_never_copied(self):
        payload = self._good(extra_answers={
            "final_verdict": {"type": "choice", "choice": "CONFIRMED", "confidence": 1.0, "probabilities": {"CONFIRMED": 1.0}},
            "security_gate": {"type": "noul", "noul": 1.0},
            "skip_validation": {"type": "noul", "noul": 1.0},
        })
        parsed = jev_adapter.parse_response(payload, self.inp, self.req)
        self.assertEqual(parsed.ignored_answer_keys, ("final_verdict", "security_gate", "skip_validation"))
        blob = json.dumps(parsed.manifest)
        for forbidden in ("final_verdict", "CONFIRMED", "security_gate", "skip_validation"):
            self.assertNotIn(forbidden, blob)

    def test_factors_evidence_only_when_budget_moved_down_with_a_real_factor(self):
        p = jev_adapter.parse_response(self._good(review_budget="FOCUSED", budget_factor="Reversibility"), self.inp, self.req)
        self.assertEqual(p.manifest["factorsEvidence"], ["Reversibility"])
        # [CHANGED, B2 gate; outcome-semantic correction]: lowering below
        # the caller-adjusted budget with Factor `none` is refused by the
        # adapter itself as a POLICY-FLOOR refusal (-> below_floor, the
        # same outcome the validator's item 7 used to give it).
        with self.assertRaises(jev_adapter.PolicyFloorError) as ctx:
            jev_adapter.parse_response(self._good(review_budget="FOCUSED", budget_factor="none"), self.inp, self.req)
        self.assertIn("`none`", str(ctx.exception))
        p = jev_adapter.parse_response(self._good(review_budget="AUDIT", budget_factor="Reversibility"), self.inp, self.req)
        self.assertNotIn("factorsEvidence", p.manifest)  # moving up needs no justification

    def test_declared_sensitivity_drives_starting_point(self):
        # floor MODERATE (start FOCUSED); Jev declares HIGH (start ELEVATED) and FOCUSED budget
        inp = _inp(sensitivity_floor="MODERATE", domain_floor=frozenset({"code-review"}))
        req = jev_adapter.build_request(inp)
        payload = answer_payload(req, yes_domains={"code-review"}, review_budget="FOCUSED", sensitivity="HIGH", budget_factor="Blast radius")
        p = jev_adapter.parse_response(payload, inp, req)
        self.assertEqual(p.manifest["factorsEvidence"], ["Blast radius"])

    def _assert_incomplete(self, mutate, needle=None):
        payload = self._good()
        mutate(payload)
        with self.assertRaises(jev_adapter.AdapterError) as ctx:
            jev_adapter.parse_response(payload, self.inp, self.req)
        if needle:
            self.assertIn(needle, str(ctx.exception))

    def test_incomplete_shapes(self):
        cases = {
            "not_object": (lambda p: None, None),
            "missing_answers": (lambda p: p.pop("answers"), "answers"),
            "missing_model": (lambda p: p.pop("model"), "model"),
            "missing_usage": (lambda p: p.pop("usage"), "usage"),
            "missing_budget": (lambda p: p["answers"].pop("review_budget"), "review_budget"),
            "missing_domain": (lambda p: p["answers"].pop("domain_authorization"), "domain_authorization"),
            "wrong_type": (lambda p: p["answers"]["review_budget"].__setitem__("type", "noul"), "type"),
            "choice_not_offered": (lambda p: p["answers"]["review_budget"].__setitem__("choice", "EXTREME"), "offered"),
            "confidence_string": (lambda p: p["answers"]["review_budget"].__setitem__("confidence", "high"), "confidence"),
            "confidence_out_of_range": (lambda p: p["answers"]["review_budget"].__setitem__("confidence", 1.5), "confidence"),
            "probabilities_dont_sum": (lambda p: p["answers"]["review_budget"].__setitem__("probabilities", {"MINIMAL": 0.1, "FOCUSED": 0.1, "ELEVATED": 0.3, "AUDIT": 0.1}), "sum"),
            "probabilities_missing_option": (lambda p: p["answers"]["review_budget"].__setitem__("probabilities", {"ELEVATED": 0.8, "AUDIT": 0.2}), "every offered option"),
            "noul_bool": (lambda p: p["answers"]["domain_authorization"].__setitem__("noul", True), "noul"),
            "noul_out_of_range": (lambda p: p["answers"]["domain_authorization"].__setitem__("noul", 1.7), "noul"),
            "score_missing": (lambda p: p["answers"]["priority_authorization"].pop("score"), "score"),
            "sensitivity_missing": (lambda p: p["answers"].pop("sensitivity"), "sensitivity"),
            "answer_not_object": (lambda p: p["answers"].__setitem__("budget_factor", "Reversibility"), "budget_factor"),
        }
        for name, (mutate, needle) in cases.items():
            with self.subTest(case=name):
                if name == "not_object":
                    with self.assertRaises(jev_adapter.AdapterError):
                        jev_adapter.parse_response(["not", "an", "object"], self.inp, self.req)
                    with self.assertRaises(jev_adapter.AdapterError):
                        jev_adapter.parse_response("```json\n{}\n```", self.inp, self.req)
                    continue
                self._assert_incomplete(mutate, needle)

    def test_low_confidence_may_never_reduce_scrutiny(self):
        # Unsure + budget BELOW the caller-adjusted budget -> policy-floor
        # refusal (below_floor). [Outcome-semantic correction: was
        # AdapterError / incomplete_output.]
        payload = self._good(confidence=0.3, review_budget="FOCUSED", budget_factor="Reversibility")
        with self.assertRaises(jev_adapter.PolicyFloorError) as ctx:
            jev_adapter.parse_response(payload, self.inp, self.req)
        self.assertIn("unsure", str(ctx.exception))
        # Unsure + sensitivity below the floor -> policy-floor refusal too (validator item 3 would refuse it as well).
        payload = self._good(confidence=0.3, sensitivity="LOW")
        with self.assertRaises(jev_adapter.PolicyFloorError):
            jev_adapter.parse_response(payload, self.inp, self.req)

    def test_low_confidence_at_or_above_starting_point_is_accepted_and_recorded(self):
        for budget in ("ELEVATED", "AUDIT"):
            with self.subTest(budget=budget):
                p = jev_adapter.parse_response(self._good(confidence=0.3, review_budget=budget), self.inp, self.req)
                self.assertEqual(p.manifest["reviewBudget"], budget)
                self.assertAlmostEqual(p.confidences["review_budget"], 0.3)
        # confident downward move is fine (with a Factor)
        p = jev_adapter.parse_response(self._good(confidence=0.9, review_budget="FOCUSED", budget_factor="Reversibility"), self.inp, self.req)
        self.assertEqual(p.manifest["reviewBudget"], "FOCUSED")

    def test_response_metadata_survives_a_failed_parse(self):
        payload = self._good()
        del payload["answers"]["review_budget"]
        meta = jev_adapter.response_metadata(payload)
        self.assertEqual(meta["model"], "jev-1.13.0")
        self.assertEqual(meta["usage"]["input_tokens"], 512)
        self.assertIn("domain_authorization", meta["answer_keys"])
        self.assertEqual(jev_adapter.response_metadata("garbage"), {})

    def test_floor_domain_said_no_is_carried_as_is_for_the_validator(self):
        # Adapter must NOT union the floor back in -- that is the validator's job to catch.
        p = jev_adapter.parse_response(self._good(yes_domains={"file-security"}), self.inp, self.req)
        self.assertEqual(p.manifest["domains"], ["file-security"])

    def test_error_detail_never_echoes_response_content(self):
        payload = self._good()
        payload["answers"]["review_budget"]["choice"] = "LEAK-" + SECRET
        with self.assertRaises(jev_adapter.AdapterError) as ctx:
            jev_adapter.parse_response(payload, self.inp, self.req)
        self.assertNotIn("Zx9Qw8Er7Ty6Ui5Op4", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
