"""Targeted tests for the Batch 2 independent-review fixes on the Jev
path (fake clients only -- no network, no token consumed):

  #1  a secret-shaped key never reaches fallbackReason / audit / manifest
  #2/#3 (decision B2) the budget gate compares against the CALLER-ADJUSTED
      budget; low confidence (budget OR Factor) may never lower it
  #7  every injected seam's unexpected output is contained
  #8  choice must be the unique argmax of a complete, finite distribution
  #9  reusable records are de-duplicated; conflicting duplicates refused

Secret assertions never print the fixture secret on failure.
"""

from __future__ import annotations

import json
import math
import unittest
from unittest import mock

from .. import jev_adapter, jev_client, orchestrator, producer
from ..domains import Fact
from ..validator import Classification
from .jev_fakes import CountingFactory, FakeJevClient, _choice, answer_payload, ok

FAKE_TOKEN = "fake-test-token-not-a-real-credential"
SECRET = 'client_secret="Zx9Qw8Er7Ty6Ui5Op4"'
SECRET_TAIL = "Zx9Qw8Er7Ty6Ui5Op4"
FLOOR = Classification(sensitivity="HIGH", implicated_domains=frozenset({"authorization", "file-security"}))
GROUP_1 = {"code-review", "configuration-security", "dependency-security"}


def _responder(*, budget_conf=0.97, factor_conf=None, **decisions):
    """Like answer_payload, but review_budget and budget_factor may carry
    DIFFERENT confidences (the real model's are independent)."""
    defaults = dict(yes_domains=set(FLOOR.implicated_domains), review_budget="ELEVATED", sensitivity="HIGH")
    defaults.update(decisions)

    def respond(state, questions):
        req = jev_adapter.JevRequest(state=state, questions=questions)
        payload = answer_payload(req, confidence=budget_conf, **defaults)
        if factor_conf is not None:
            payload["answers"]["budget_factor"] = _choice(
                questions["budget_factor"]["criteria"], defaults.get("budget_factor", "none"), factor_conf)
        return ok(payload)

    return respond


def _run(responder=None, *, client=None, token=FAKE_TOKEN, **kw):
    kwargs = dict(review_mode="TARGETED", target_change_files=["Controllers/ReportsController.cs"],
                  classification=FLOOR, diff_summary="adds a report download endpoint")
    kwargs.update(kw)
    if client is None and responder is not None:
        client = FakeJevClient(responder=responder)
    factory = CountingFactory(client) if client is not None else None
    return orchestrator.produce_manifest(token_provider=lambda: token, client_factory=factory, **kwargs), factory


def _blob(result) -> str:
    return json.dumps(result.manifest, default=str) + json.dumps(result.audit, default=str)


# ------------------------------------------------------------------ B2 gate


class BudgetGateTests(unittest.TestCase):
    """TARGETED/HIGH: starting point ELEVATED, legal range FOCUSED..AUDIT.
    factor_adjustment=+1 -> caller-adjusted AUDIT."""

    UP = dict(factor_adjustment=1, factors_evidence=("External exposure",))

    def test_state_tells_jev_the_caller_adjusted_budget(self):
        req = jev_adapter.build_request(jev_adapter.AllowedInput(
            review_mode="TARGETED", target_files=("a.cs",), domain_floor=FLOOR.implicated_domains,
            sensitivity_floor="HIGH", factor_adjustment=1))
        self.assertEqual(req.state["deterministic_floor"]["review_budget_caller_adjusted"], "AUDIT")
        self.assertNotIn("factor_adjustment", req.questions)  # never asked of Jev

    def _assert_policy_floor_fallback(self, result, expected_budget):
        """Outcome-semantic rule: a COMPLETE candidate below the effective
        floor is below_floor + fallback; the whole candidate is discarded
        (no Jev field survives) and the built-in manifest keeps the
        caller-adjusted budget."""
        self.assertEqual(result.jev_outcome, "below_floor")
        self.assertEqual(result.produced_by, "built_in")
        self.assertEqual(result.manifest["producedBy"], "built_in")
        self.assertTrue(result.manifest["degradation"]["fallbackUsed"])
        self.assertIn("policy_floor", result.manifest["degradation"]["fallbackReason"])
        self.assertEqual(result.audit["stage"], "policy_floor_refused")
        self.assertEqual(result.manifest["reviewBudget"], expected_budget)
        self.assertNotIn("priorityOrder", result.manifest)  # nothing of Jev's is kept
        self.assertTrue(result.manifest["validity"]["passed"])

    def test_caller_audit_jev_elevated_conf_001_keeps_audit(self):
        result, _ = _run(_responder(review_budget="ELEVATED", budget_conf=0.01, budget_factor="Reversibility"), **self.UP)
        self._assert_policy_floor_fallback(result, "AUDIT")
        self.assertIn("caller-adjusted budget AUDIT", result.manifest["degradation"]["fallbackReason"])

    def test_just_below_threshold_keeps_audit(self):
        result, _ = _run(_responder(review_budget="ELEVATED", budget_conf=0.4999, budget_factor="Reversibility"), **self.UP)
        self._assert_policy_floor_fallback(result, "AUDIT")

    def test_next_representable_below_threshold_is_below_floor(self):
        just_below = math.nextafter(jev_adapter.MIN_CONFIDENCE_TO_REDUCE_SCRUTINY, 0.0)
        self.assertLess(just_below, 0.5)
        result, _ = _run(_responder(review_budget="ELEVATED", budget_conf=just_below, budget_factor="Reversibility"), **self.UP)
        self._assert_policy_floor_fallback(result, "AUDIT")
        result, _ = _run(_responder(review_budget="ELEVATED", budget_conf=0.97, factor_conf=just_below,
                                    budget_factor="Reversibility"), **self.UP)
        self._assert_policy_floor_fallback(result, "AUDIT")

    def test_completeness_is_decided_before_the_policy_floor(self):
        # Both defects at once: an unsure lowering AND a missing answer
        # that is parsed AFTER the budget gate (a reuse Noul). The response
        # is not complete, so incomplete_output wins; the gate's refusal is
        # never reported for an incomplete response.
        rec = jev_adapter.ReusableRecordSummary("rec-a", "BOLA/IDOR", "src/A.cs")

        def respond(state, questions):
            payload = answer_payload(jev_adapter.JevRequest(state, questions), yes_domains=set(FLOOR.implicated_domains),
                                     review_budget="ELEVATED", sensitivity="HIGH", budget_factor="Reversibility", confidence=0.01)
            del payload["answers"]["reuse_rec-a"]
            return ok(payload)
        result, _ = _run(respond, reusable_records=[rec], **self.UP)
        self.assertEqual(result.jev_outcome, "incomplete_output")
        self.assertIn("reuse_rec-a", result.manifest["degradation"]["fallbackReason"])
        self.assertNotIn("policy_floor", result.manifest["degradation"]["fallbackReason"])

    def test_output_contract_failures_stay_incomplete_output(self):
        def contradiction(state, questions):
            payload = answer_payload(jev_adapter.JevRequest(state, questions), yes_domains=set(FLOOR.implicated_domains),
                                     review_budget="ELEVATED", sensitivity="HIGH")
            payload["answers"]["review_budget"]["probabilities"] = {"MINIMAL": 0.7, "FOCUSED": 0.1, "ELEVATED": 0.1, "AUDIT": 0.1}
            return ok(payload)

        def wrong_type(state, questions):
            payload = answer_payload(jev_adapter.JevRequest(state, questions), yes_domains=set(FLOOR.implicated_domains),
                                     review_budget="ELEVATED", sensitivity="HIGH")
            payload["answers"]["review_budget"]["type"] = "noul"
            return ok(payload)

        for name, respond, needle in (("choice/probabilities contradiction", contradiction, "highest-probability"),
                                      ("wrong answer type", wrong_type, "type")):
            with self.subTest(case=name):
                result, _ = _run(respond, **self.UP)
                self.assertEqual(result.jev_outcome, "incomplete_output")
                self.assertIn(needle, result.manifest["degradation"]["fallbackReason"])
                self.assertNotIn("policy_floor", result.manifest["degradation"]["fallbackReason"])

    def test_exactly_at_threshold_may_lower(self):
        result, _ = _run(_responder(review_budget="ELEVATED", budget_conf=0.5, factor_conf=0.5,
                                    budget_factor="Reversibility"), **self.UP)
        self.assertEqual(result.jev_outcome, "success")
        self.assertEqual(result.manifest["reviewBudget"], "ELEVATED")
        self.assertEqual(result.manifest["factorsEvidence"], ["External exposure", "Reversibility"])
        self.assertEqual(result.audit["budget_reference"], "AUDIT")

    def test_unsure_factor_may_not_back_a_lowering(self):  # review #2
        result, _ = _run(_responder(review_budget="ELEVATED", budget_conf=0.97, factor_conf=0.4999,
                                    budget_factor="Reversibility"), **self.UP)
        self._assert_policy_floor_fallback(result, "AUDIT")
        self.assertIn("budget_factor confidence", result.manifest["degradation"]["fallbackReason"])
        # the reviewer's exact probe: adjustment 0, FOCUSED at .97, Factor at .01
        result, _ = _run(_responder(review_budget="FOCUSED", budget_conf=0.97, factor_conf=0.01, budget_factor="Reversibility"))
        self._assert_policy_floor_fallback(result, "ELEVATED")

    def test_jev_may_raise_above_the_caller(self):
        result, _ = _run(_responder(review_budget="AUDIT", budget_conf=0.2))  # unsure but MORE scrutiny
        self.assertEqual(result.jev_outcome, "success")
        self.assertEqual(result.manifest["reviewBudget"], "AUDIT")
        self.assertNotIn("factorsEvidence", result.manifest)
        # equal to the caller-adjusted budget with low confidence is not a reduction either
        result, _ = _run(_responder(review_budget="AUDIT", budget_conf=0.01), **self.UP)
        self.assertEqual(result.jev_outcome, "success")

    def test_below_deterministic_floor_is_below_floor(self):
        # Confident, with a confident Factor -> passes the gate, then the
        # unchanged validator rejects MINIMAL as outside FOCUSED..AUDIT.
        result, _ = _run(_responder(review_budget="MINIMAL", budget_factor="Reversibility"))
        self.assertEqual(result.jev_outcome, "below_floor")
        self.assertIn("item7", result.manifest["degradation"]["fallbackReason"])

    def test_forged_factor_adjustment_answer_is_ignored(self):
        def respond(state, questions):
            req = jev_adapter.JevRequest(state=state, questions=questions)
            payload = answer_payload(req, yes_domains=set(FLOOR.implicated_domains), review_budget="AUDIT", sensitivity="HIGH")
            payload["answers"]["factor_adjustment"] = {"type": "choice", "choice": "-2", "confidence": 1.0,
                                                       "probabilities": {"-2": 1.0}}
            return ok(payload)
        result, _ = _run(respond, **self.UP)
        self.assertEqual(result.jev_outcome, "success")
        self.assertIn("factor_adjustment", result.audit["ignored_answer_keys"])
        self.assertEqual(result.audit["budget_reference"], "AUDIT")

    def test_caller_evidence_carried_and_item7_still_enforced(self):
        # Caller moved DOWN (-1 -> FOCUSED) with evidence: Jev FOCUSED at
        # low confidence is not a reduction of the caller's conclusion.
        result, _ = _run(_responder(review_budget="FOCUSED", budget_conf=0.2),
                         factor_adjustment=-1, factors_evidence=("Reversibility",))
        self.assertEqual(result.jev_outcome, "success")
        self.assertEqual(result.manifest["factorsEvidence"], ["Reversibility"])
        # Caller moved down WITHOUT evidence: the Jev candidate fails item 7
        # (below_floor) and the built-in producer itself refuses -> the
        # orchestrator surfaces that instead of fabricating a manifest.
        with self.assertRaises(orchestrator.OrchestrationError):
            _run(_responder(review_budget="FOCUSED"), factor_adjustment=-1)

    def test_factor_adjustment_type_and_single_materialization(self):
        with self.assertRaises(TypeError):
            _run(_responder(), factor_adjustment=True)
        gen = (e for e in ["Reversibility"])
        result, _ = _run(_responder(review_budget="FOCUSED", budget_conf=0.2), factor_adjustment=-1, factors_evidence=gen)
        self.assertEqual(result.manifest["factorsEvidence"], ["Reversibility"])
        gen = (e for e in ["Reversibility"])
        result, _ = _run(token=None, factor_adjustment=-1, factors_evidence=gen)  # built-in path sees it too
        self.assertEqual(result.manifest["factorsEvidence"], ["Reversibility"])


class DeepLowBudgetTests(unittest.TestCase):
    FACTS = {k: Fact(True, "HIGH", "CODE_EVIDENCE") for k in (
        "no_html_or_script_ever_rendered", "never_uses_cookie_or_ambient_auth_for_state_change",
        "no_browser_page_produced", "no_browser_side_script_shipped",
        "no_user_influenced_redirect_issued", "no_cors_headers_or_cross_origin_registration",
    )}

    def _run(self, **decisions):
        floor = Classification.for_deep(self.FACTS)
        decisions.setdefault("yes_domains", set(floor.implicated_domains))
        client = FakeJevClient(responder=_responder(sensitivity=None, **decisions))
        return floor, orchestrator.produce_manifest(review_mode="DEEP", baseline_facts=self.FACTS,
                                                    token_provider=lambda: FAKE_TOKEN, client_factory=CountingFactory(client))

    def test_confident_low_budget_keeps_every_mandatory_activity(self):
        floor, result = self._run(review_budget="MINIMAL", budget_factor="Blast radius")
        self.assertEqual(result.jev_outcome, "success")
        self.assertEqual(result.manifest["reviewBudget"], "MINIMAL")
        self.assertTrue(GROUP_1 <= set(result.manifest["domains"]))
        self.assertEqual(set(result.manifest["domains"]), set(floor.implicated_domains))

    def test_unsure_low_budget_falls_back_to_audit(self):
        _, result = self._run(review_budget="MINIMAL", budget_factor="Blast radius", budget_conf=0.3)
        self.assertEqual(result.jev_outcome, "below_floor")  # complete candidate, below the effective floor
        self.assertEqual(result.audit["stage"], "policy_floor_refused")
        self.assertEqual(result.manifest["reviewBudget"], "AUDIT")

    def test_low_budget_cannot_drop_a_mandatory_activity(self):
        floor, result = self._run(review_budget="MINIMAL", budget_factor="Blast radius",
                                  yes_domains=set(Classification.for_deep(self.FACTS).implicated_domains) - {"code-review"})
        self.assertEqual(result.jev_outcome, "below_floor")
        self.assertIn("code-review", result.manifest["degradation"]["fallbackReason"])
        self.assertTrue(GROUP_1 <= set(result.manifest["domains"]))


# ------------------------------------------------------------------ #8 choice


class ChoiceConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.inp = jev_adapter.AllowedInput(review_mode="TARGETED", target_files=("a.cs",),
                                            domain_floor=FLOOR.implicated_domains, sensitivity_floor="HIGH")
        self.req = jev_adapter.build_request(self.inp)

    def _refused(self, probs=None, choice=None, confidence=None, needle=""):
        payload = answer_payload(self.req, yes_domains=set(FLOOR.implicated_domains), review_budget="ELEVATED", sensitivity="HIGH")
        ans = payload["answers"]["review_budget"]
        if probs is not None:
            ans["probabilities"] = probs
        if choice is not None:
            ans["choice"] = choice
        if confidence is not None:
            ans["confidence"] = confidence
        with self.assertRaises(jev_adapter.AdapterError) as ctx:
            jev_adapter.parse_response(payload, self.inp, self.req)
        self.assertIn(needle, str(ctx.exception))

    def test_choice_must_be_argmax(self):
        self._refused(probs={"MINIMAL": 0.7, "FOCUSED": 0.1, "ELEVATED": 0.1, "AUDIT": 0.1}, needle="highest-probability")

    def test_tie_at_top_refused(self):
        self._refused(probs={"MINIMAL": 0.0, "FOCUSED": 0.0, "ELEVATED": 0.5, "AUDIT": 0.5}, needle="tie")

    def test_non_finite_and_out_of_range_refused(self):
        for bad in (float("nan"), float("inf"), float("-inf"), -0.1, 1.1):
            with self.subTest(bad=bad):
                self._refused(probs={"MINIMAL": bad, "FOCUSED": 0.0, "ELEVATED": 0.9, "AUDIT": 0.1}, needle="finite number")
        self._refused(confidence=float("nan"), needle="confidence")

    def test_missing_option_refused(self):
        self._refused(probs={"ELEVATED": 0.9, "AUDIT": 0.1}, needle="every offered option")

    def test_noul_and_score_nan_refused(self):
        payload = answer_payload(self.req, yes_domains=set(FLOOR.implicated_domains), review_budget="ELEVATED", sensitivity="HIGH")
        payload["answers"]["domain_authorization"]["noul"] = float("nan")
        with self.assertRaises(jev_adapter.AdapterError):
            jev_adapter.parse_response(payload, self.inp, self.req)

    def test_json_nan_literal_through_the_real_client_parse(self):
        # json.loads accepts NaN; the adapter must still refuse it.
        payload = answer_payload(self.req, yes_domains=set(FLOOR.implicated_domains), review_budget="ELEVATED", sensitivity="HIGH")
        raw = json.dumps(payload).replace('"confidence": 0.97', '"confidence": NaN', 1)
        self.assertIn("NaN", raw)
        with self.assertRaises(jev_adapter.AdapterError):
            jev_adapter.parse_response(json.loads(raw), self.inp, self.req)


# ------------------------------------------------------------------ #9 dedupe


class ReusableRecordDedupeTests(unittest.TestCase):
    A = jev_adapter.ReusableRecordSummary("rec-a", "BOLA/IDOR", "src/A.cs")
    B = jev_adapter.ReusableRecordSummary("rec-b", "BOLA/IDOR", "src/B.cs")

    def test_duplicates_collapse_in_deterministic_order(self):
        result, _ = _run(_responder(reuse_yes={"rec-a", "rec-b"}), reusable_records=[self.B, self.A, self.B, self.A])
        self.assertEqual(result.jev_outcome, "success")
        self.assertEqual(result.manifest["intelligenceConsulted"]["feedbackRecordsConsulted"], ["rec-b", "rec-a"])

    def test_request_asks_once_per_record(self):
        req = jev_adapter.build_request(jev_adapter.AllowedInput(
            review_mode="QUICK", target_files=("a.cs",), domain_floor=frozenset({"code-review"}),
            reusable_records=(self.A, self.A)))
        self.assertEqual([k for k in req.questions if k.startswith("reuse_")], ["reuse_rec-a"])
        self.assertEqual(len(req.state["reusable_intelligence"]), 1)

    def test_conflicting_duplicate_refused_without_naming_the_id(self):
        conflict = jev_adapter.ReusableRecordSummary("rec-a", "SQLi", "src/Other.cs")
        client = FakeJevClient(responder=_responder())
        result, factory = _run(client=client, reusable_records=[self.A, conflict])
        self.assertEqual(result.jev_outcome, "incomplete_output")
        self.assertEqual(result.produced_by, "built_in")
        self.assertEqual(client.calls, [])  # no request sent
        reason = result.manifest["degradation"]["fallbackReason"]
        self.assertIn("request_build_failed", reason)
        self.assertIn("reusable_records[0] and reusable_records[1]", reason)
        self.assertNotIn("rec-a", reason)


# ------------------------------------------------------------------ #7 containment


class ExceptionContainmentTests(unittest.TestCase):
    def _assert_safe_fallback(self, result, outcome):
        self.assertEqual(result.jev_outcome, outcome)
        self.assertEqual(result.produced_by, "built_in")
        self.assertTrue(result.manifest["validity"]["passed"])
        reason = result.manifest["degradation"]["fallbackReason"]
        self.assertTrue(isinstance(reason, str) and reason.strip())
        self.assertFalse(FAKE_TOKEN in _blob(result), "token leaked into manifest/audit")

    def test_client_returns_none(self):
        result, _ = _run(client=FakeJevClient(result=None))
        self._assert_safe_fallback(result, "incomplete_output")
        self.assertEqual(result.audit["stage"], "client_contract_violation")

    def test_client_returns_wrong_type(self):
        result, _ = _run(client=FakeJevClient(result={"outcome": "ok"}))
        self._assert_safe_fallback(result, "incomplete_output")

    def test_empty_or_non_string_detail(self):
        cases = (
            (jev_client.ClientResult(outcome=jev_client.AUTH_REJECTED, status=401, detail=""), "invalid_token"),
            (jev_client.ClientResult(outcome=jev_client.AUTH_REJECTED, status=403, detail=None), "invalid_token"),
            (jev_client.ClientResult(outcome=jev_client.TIMEOUT, detail=""), "timeout"),
            (jev_client.ClientResult(outcome=jev_client.TIMEOUT, detail=12345), "timeout"),
            (jev_client.ClientResult(outcome=jev_client.HTTP_ERROR, status=500, detail=""), "incomplete_output"),
            (jev_client.ClientResult(outcome=jev_client.INVALID_JSON, detail=None), "incomplete_output"),
            (jev_client.ClientResult(outcome=object(), detail="x"), "incomplete_output"),
        )
        for res, outcome in cases:
            with self.subTest(outcome=outcome, detail=repr(res.detail)):
                result, _ = _run(client=FakeJevClient(result=res))
                self._assert_safe_fallback(result, outcome)

    def test_auth_rejected_without_401_403_is_not_invalid_token(self):
        for status in (None, 200, 422, 500):
            with self.subTest(status=status):
                res = jev_client.ClientResult(outcome=jev_client.AUTH_REJECTED, status=status, detail="nope")
                result, _ = _run(client=FakeJevClient(result=res))
                self._assert_safe_fallback(result, "incomplete_output")

    def test_detail_with_token_or_secret_is_withheld(self):
        for detail in (f"HTTP 401 for Bearer {FAKE_TOKEN}", f"upstream said {SECRET}", "x" * 20000):
            with self.subTest(n=len(detail)):
                res = jev_client.ClientResult(outcome=jev_client.TIMEOUT, detail=detail)
                result, _ = _run(client=FakeJevClient(result=res))
                self._assert_safe_fallback(result, "timeout")
                reason = result.manifest["degradation"]["fallbackReason"]
                self.assertFalse(SECRET_TAIL in _blob(result), "secret leaked")
                self.assertLess(len(reason), 500)

    def test_int_answer_keys_do_not_crash(self):
        def respond(state, questions):
            payload = answer_payload(jev_adapter.JevRequest(state, questions), yes_domains=set(FLOOR.implicated_domains),
                                     review_budget="ELEVATED", sensitivity="HIGH")
            payload["answers"][7] = {"type": "noul", "noul": 1.0}
            return ok(payload)
        result, _ = _run(respond)
        self.assertEqual(result.jev_outcome, "success")
        self.assertIn(7, result.audit["ignored_answer_keys"])

    def test_adapter_raises_non_adapter_error(self):
        with mock.patch.object(orchestrator.jev_adapter, "parse_response", side_effect=KeyError(SECRET)):
            result, _ = _run(_responder())
        self._assert_safe_fallback(result, "incomplete_output")
        self.assertEqual(result.audit["stage"], "adapter_exception")
        self.assertFalse(SECRET_TAIL in _blob(result), "exception message leaked")

    def test_response_metadata_raising_is_diagnostic_only(self):
        with mock.patch.object(orchestrator.jev_adapter, "response_metadata", side_effect=RuntimeError("x")):
            result, _ = _run(_responder())
        self.assertEqual(result.jev_outcome, "success")
        self.assertEqual(result.audit["metadata_error"], "RuntimeError")

    def test_validator_raises_on_candidate_only(self):
        real = orchestrator.validate_manifest
        calls = []

        def flaky(manifest, *, floor):
            calls.append(manifest["producedBy"])
            if manifest["producedBy"] == "jev":
                raise RuntimeError(SECRET)
            return real(manifest, floor=floor)

        with mock.patch.object(orchestrator, "validate_manifest", side_effect=flaky):
            result, _ = _run(_responder())
        self._assert_safe_fallback(result, "below_floor")
        self.assertEqual(result.audit["stage"], "validator_exception")
        self.assertEqual(calls, ["jev", "built_in"])
        self.assertFalse(SECRET_TAIL in _blob(result), "exception message leaked")

    def test_validator_raises_on_everything_is_an_orchestration_error(self):
        with mock.patch.object(orchestrator, "validate_manifest", side_effect=RuntimeError("boom")):
            with self.assertRaises(orchestrator.OrchestrationError):
                _run(_responder())
            with self.assertRaises(orchestrator.OrchestrationError):
                _run(token=None)

    def test_built_in_producer_failure_is_surfaced_never_fabricated(self):
        with mock.patch.object(orchestrator.producer, "build_manifest", side_effect=RuntimeError("boom")):
            with self.assertRaises(orchestrator.OrchestrationError):
                _run(token=None)
            with self.assertRaises(orchestrator.OrchestrationError):
                _run(client=FakeJevClient(result=None))

    def test_token_provider_raises(self):
        factory = CountingFactory(FakeJevClient(responder=_responder()))

        def boom():
            raise OSError("keychain locked")

        result = orchestrator.produce_manifest(review_mode="TARGETED", target_change_files=["a.cs"], classification=FLOOR,
                                               token_provider=boom, client_factory=factory)
        self.assertEqual(result.jev_outcome, "no_token")
        self.assertFalse(result.manifest["degradation"]["jevAttempted"])
        self.assertIn("token provider raised OSError", result.manifest["degradation"]["fallbackReason"])
        self.assertEqual(factory.built, 0)
        self.assertTrue(result.manifest["validity"]["passed"])


# ------------------------------------------------------------------ #1 end to end


class SecretKeyNeverReachesOutputsTests(unittest.TestCase):
    def test_secret_record_id_is_refused_with_redacted_path(self):
        rec = jev_adapter.ReusableRecordSummary(SECRET, "BOLA/IDOR", "a/R.cs")
        client = FakeJevClient(responder=_responder())
        result, _ = _run(client=client, reusable_records=[rec])
        self.assertEqual(result.jev_outcome, "incomplete_output")
        self.assertEqual(client.calls, [])
        reason = result.manifest["degradation"]["fallbackReason"]
        self.assertIn("request_redaction_refused", reason)
        self.assertIn("<redacted-key>", reason)
        self.assertFalse(SECRET_TAIL in _blob(result), "secret leaked into manifest/audit")


if __name__ == "__main__":
    unittest.main()
