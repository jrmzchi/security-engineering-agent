"""orchestrator.py -- the six fixed outcomes and the adversarial extras,
all with injected fake clients (no network, no token consumed)."""

from __future__ import annotations

import copy
import json
import unittest

from .. import jev_adapter, jev_client, orchestrator, producer, schema
from ..domains import Fact
from ..validator import Classification, validate_manifest
from .jev_fakes import CountingFactory, FakeJevClient, answer_payload, ok

FAKE_TOKEN = "fake-test-token-not-a-real-credential"
SECRET = 'client_secret="Zx9Qw8Er7Ty6Ui5Op4"'


def _targeted_kwargs(**overrides):
    kwargs = dict(
        review_mode="TARGETED",
        target_change_files=["Controllers/ReportsController.cs"],
        classification=Classification(sensitivity="HIGH", implicated_domains=frozenset({"authorization", "file-security"})),
        diff_summary="adds a report download endpoint",
    )
    kwargs.update(overrides)
    return kwargs


_PRODUCER_KEYS = {"review_mode", "target_change_files", "classification", "baseline_facts", "factor_adjustment",
                  "factors_evidence", "scanner_selection", "review_id", "produced_at"}


def _plain_built_in(**overrides):
    """The built-in producer alone, for comparison -- only its own arguments."""
    return producer.build_manifest(**{k: v for k, v in _targeted_kwargs(**overrides).items() if k in _PRODUCER_KEYS})


def _responder(**decisions):
    defaults = dict(yes_domains={"authorization", "file-security"}, review_budget="ELEVATED", sensitivity="HIGH")
    defaults.update(decisions)

    def respond(state, questions):
        req = jev_adapter.JevRequest(state=state, questions=questions)
        return ok(answer_payload(req, **defaults))

    return respond


def _run(client=None, token=FAKE_TOKEN, **kw):
    factory = CountingFactory(client) if client is not None else None
    result = orchestrator.produce_manifest(token_provider=lambda: token, client_factory=factory, **_targeted_kwargs(**kw))
    return result, factory


class SixOutcomesTests(unittest.TestCase):
    def _assert_valid_and_fallback(self, result, outcome):
        m = result.manifest
        self.assertEqual(result.jev_outcome, outcome)
        self.assertEqual(result.produced_by, "built_in")
        self.assertEqual(m["producedBy"], "built_in")
        self.assertEqual(m["degradation"]["jevOutcome"], outcome)
        self.assertTrue(m["degradation"]["fallbackUsed"])
        self.assertTrue(m["degradation"]["fallbackReason"])
        self.assertTrue(m["validity"]["passed"], m["validity"])
        # fallback never lowers capability: same floor domains, same budget as a plain built-in run
        plain = _plain_built_in()
        self.assertEqual(m["domains"], plain["domains"])
        self.assertEqual(m["reviewBudget"], plain["reviewBudget"])
        self.assertEqual(m["sensitivity"], plain["sensitivity"])
        self.assertEqual(m["scannersSelected"], plain["scannersSelected"])

    def test_1_no_token_never_calls_jev(self):
        client = FakeJevClient(responder=_responder())
        for token in (None, "", "   "):
            with self.subTest(token=repr(token)):
                result, factory = _run(client=client, token=token)
                self.assertEqual(result.jev_outcome, "no_token")
                self.assertEqual(result.manifest["degradation"], schema.new_degradation_no_jev_attempted() | {})
                self.assertFalse(result.manifest["degradation"]["jevAttempted"])
                self.assertEqual(factory.built, 0)
                self.assertEqual(client.calls, [])
                self._assert_valid_and_fallback(result, "no_token")

    def test_2_invalid_token(self):
        client = FakeJevClient(jev_client.ClientResult(outcome=jev_client.AUTH_REJECTED, status=401, detail="HTTP 401: authentication/authorization rejected by the API"))
        result, factory = _run(client=client)
        self._assert_valid_and_fallback(result, "invalid_token")
        self.assertEqual(factory.built, 1)
        self.assertTrue(result.manifest["degradation"]["jevAttempted"])
        self.assertIn("401", result.manifest["degradation"]["fallbackReason"])

    def test_2b_non_auth_http_errors_are_not_invalid_token(self):
        for status in (400, 422, 429, 500, 529):
            with self.subTest(status=status):
                client = FakeJevClient(jev_client.ClientResult(outcome=jev_client.HTTP_ERROR, status=status, detail=f"HTTP {status}"))
                result, _ = _run(client=client)
                self.assertEqual(result.jev_outcome, "incomplete_output")
                self.assertIn(f"transport_error: HTTP {status}", result.manifest["degradation"]["fallbackReason"])

    def test_3_timeout_bounded_single_attempt(self):
        client = FakeJevClient(jev_client.ClientResult(outcome=jev_client.TIMEOUT, detail="request exceeded the configured timeout of 10.0s"))
        result, _ = _run(client=client)
        self._assert_valid_and_fallback(result, "timeout")
        self.assertEqual(len(client.calls), 1)  # no retry loop

    def test_4_incomplete_output_missing_field_and_wrong_type(self):
        def respond_missing(state, questions):
            payload = answer_payload(jev_adapter.JevRequest(state, questions), yes_domains={"authorization", "file-security"}, review_budget="ELEVATED", sensitivity="HIGH")
            del payload["answers"]["review_budget"]
            return ok(payload)

        result, _ = _run(client=FakeJevClient(responder=respond_missing))
        self._assert_valid_and_fallback(result, "incomplete_output")
        self.assertIn("review_budget", result.manifest["degradation"]["fallbackReason"])

        def respond_wrong_type(state, questions):
            payload = answer_payload(jev_adapter.JevRequest(state, questions), yes_domains={"authorization", "file-security"}, review_budget="ELEVATED", sensitivity="HIGH")
            payload["answers"]["domain_authorization"]["noul"] = "yes"
            return ok(payload)

        result, _ = _run(client=FakeJevClient(responder=respond_wrong_type))
        self._assert_valid_and_fallback(result, "incomplete_output")

    def test_5_below_floor_missing_required_domain(self):
        # Jev says "no" to authorization -- a floor domain. Schema-complete, validator rejects.
        result, _ = _run(client=FakeJevClient(responder=_responder(yes_domains={"file-security"})))
        self._assert_valid_and_fallback(result, "below_floor")
        self.assertIn("item5", result.manifest["degradation"]["fallbackReason"])
        self.assertIn("authorization", result.manifest["degradation"]["fallbackReason"])

    def test_5b_below_floor_sensitivity_and_budget(self):
        result, _ = _run(client=FakeJevClient(responder=_responder(sensitivity="LOW")))
        self.assertEqual(result.jev_outcome, "below_floor")
        self.assertIn("item3", result.manifest["degradation"]["fallbackReason"])
        result, _ = _run(client=FakeJevClient(responder=_responder(review_budget="MINIMAL", budget_factor="Reversibility")))
        self.assertEqual(result.jev_outcome, "below_floor")
        self.assertIn("item7", result.manifest["degradation"]["fallbackReason"])
        # [CHANGED, B2 gate; outcome-semantic correction]: moved down
        # within range but no factor named -> refused by the adapter's
        # budget gate as a POLICY-FLOOR refusal -> below_floor (complete
        # output, below the effective floor); the validator's item 7
        # evidence rule is exercised in test_batch2_review_fixes.
        result, _ = _run(client=FakeJevClient(responder=_responder(review_budget="FOCUSED", budget_factor="none")))
        self._assert_valid_and_fallback(result, "below_floor")
        self.assertIn("policy_floor", result.manifest["degradation"]["fallbackReason"])
        self.assertIn("`none`", result.manifest["degradation"]["fallbackReason"])

    def test_6_success_accepted_as_is_not_rewritten(self):
        client = FakeJevClient(responder=_responder(
            yes_domains={"authorization", "file-security", "web-security"},  # superset of floor
            review_budget="FOCUSED", budget_factor="Reversibility",           # a lawful, DIFFERENT budget
            priorities={"file-security": 3.0, "authorization": 2.0, "web-security": 0.0},
        ))
        result, factory = _run(client=client)
        m = result.manifest
        self.assertEqual(result.jev_outcome, "success")
        self.assertEqual(result.produced_by, "jev")
        self.assertEqual(m["producedBy"], "jev")
        self.assertEqual(m["degradation"], {"jevAttempted": True, "jevOutcome": "success", "fallbackUsed": False, "fallbackReason": None})
        self.assertEqual(m["domains"], ["authorization", "file-security", "web-security"])
        self.assertEqual(m["reviewBudget"], "FOCUSED")
        self.assertEqual(m["factorsEvidence"], ["Reversibility"])
        self.assertEqual(m["priorityOrder"], ["file-security", "authorization", "web-security"])
        self.assertTrue(m["validity"]["passed"])
        # Not silently normalized back to the built-in manifest:
        plain = _plain_built_in()
        self.assertNotEqual(m["reviewBudget"], plain["reviewBudget"])
        self.assertTrue(set(m["domains"]) > set(plain["domains"]))
        self.assertEqual(factory.built, 1)
        self.assertEqual(len(client.calls), 1)


class AdversarialTests(unittest.TestCase):
    def test_malformed_json_body_is_incomplete_output(self):
        client = FakeJevClient(jev_client.ClientResult(outcome=jev_client.INVALID_JSON, status=200, detail="2xx body is not valid JSON (JSONDecodeError)"))
        result, _ = _run(client=client)
        self.assertEqual(result.jev_outcome, "incomplete_output")

    def test_markdown_fenced_response_is_incomplete_output(self):
        # A transport that returns fenced text is INVALID_JSON at the client; if a payload
        # somehow arrived as a string, the adapter refuses it too.
        client = FakeJevClient(jev_client.ClientResult(outcome=jev_client.OK, payload="```json\n{}\n```", status=200))
        result, _ = _run(client=client)
        self.assertEqual(result.jev_outcome, "incomplete_output")

    def test_over_scope_final_verdict_never_enters_manifest(self):
        client = FakeJevClient(responder=lambda s, q: ok(answer_payload(
            jev_adapter.JevRequest(s, q), yes_domains={"authorization", "file-security"}, review_budget="ELEVATED", sensitivity="HIGH",
            extra_answers={"final_verdict": {"type": "choice", "choice": "CONFIRMED", "confidence": 1.0, "probabilities": {"CONFIRMED": 1.0}},
                           "security_gate": {"type": "noul", "noul": 1.0}},
        )))
        result, _ = _run(client=client)
        self.assertEqual(result.jev_outcome, "success")
        blob = json.dumps(result.manifest)
        self.assertNotIn("final_verdict", blob)
        self.assertNotIn("CONFIRMED", blob)
        self.assertNotIn("security_gate", blob)
        self.assertEqual(result.audit["ignored_answer_keys"], ["final_verdict", "security_gate"])

    def test_reuse_of_a_record_not_offered_as_eligible_is_ignored(self):
        # The caller offers rec-ok (eligible); Jev "consults" rec-stale which was never offered.
        client = FakeJevClient(responder=lambda s, q: ok(answer_payload(
            jev_adapter.JevRequest(s, q), yes_domains={"authorization", "file-security"}, review_budget="ELEVATED", sensitivity="HIGH",
            reuse_yes={"rec-ok"}, extra_answers={"reuse_rec-stale": {"type": "noul", "noul": 0.99}},
        )))
        result, _ = _run(client=client, reusable_records=[jev_adapter.ReusableRecordSummary("rec-ok", "BOLA/IDOR", "a/R.cs")])
        self.assertEqual(result.jev_outcome, "success")
        self.assertEqual(result.manifest["intelligenceConsulted"]["feedbackRecordsConsulted"], ["rec-ok"])
        self.assertIn("reuse_rec-stale", result.audit["ignored_answer_keys"])

    def test_request_with_suspected_secret_is_never_sent(self):
        client = FakeJevClient(responder=_responder())
        result, factory = _run(client=client, diff_summary=f"sets {SECRET}")
        self.assertEqual(result.jev_outcome, "incomplete_output")
        self.assertEqual(client.calls, [])
        self.assertEqual(factory.built, 0)
        reason = result.manifest["degradation"]["fallbackReason"]
        self.assertIn("request_redaction_refused", reason)
        self.assertIn("no request sent", reason)
        self.assertNotIn("Zx9Qw8Er7Ty6Ui5Op4", reason)
        self.assertTrue(result.manifest["degradation"]["jevAttempted"])
        self.assertTrue(result.manifest["validity"]["passed"])

    def test_client_raising_unexpected_exception_falls_back(self):
        client = FakeJevClient(raise_exc=RuntimeError("boom"))
        result, _ = _run(client=client)
        self.assertEqual(result.jev_outcome, "incomplete_output")
        self.assertIn("transport_error", result.manifest["degradation"]["fallbackReason"])
        self.assertTrue(result.manifest["validity"]["passed"])

    def test_client_factory_raising_falls_back(self):
        def bad_factory(token):
            raise ValueError("cannot build")
        result = orchestrator.produce_manifest(token_provider=lambda: FAKE_TOKEN, client_factory=bad_factory, **_targeted_kwargs())
        self.assertEqual(result.jev_outcome, "incomplete_output")

    def test_validator_crash_is_not_success(self):
        client = FakeJevClient(responder=_responder())
        original = orchestrator.validate_manifest
        calls = {"n": 0}

        def crashing(manifest, *, floor):
            calls["n"] += 1
            if manifest.get("producedBy") == "jev":
                raise RuntimeError("validator bug")
            return original(manifest, floor=floor)

        orchestrator.validate_manifest = crashing
        try:
            result, _ = _run(client=client)
        finally:
            orchestrator.validate_manifest = original
        self.assertEqual(result.jev_outcome, "below_floor")
        self.assertEqual(result.produced_by, "built_in")
        self.assertIn("validator raised", result.manifest["degradation"]["fallbackReason"])

    def test_built_in_failure_is_never_a_fabricated_manifest(self):
        client = FakeJevClient(jev_client.ClientResult(outcome=jev_client.TIMEOUT, detail="t"))
        original = orchestrator.producer.build_manifest
        orchestrator.producer.build_manifest = lambda **kw: (_ for _ in ()).throw(RuntimeError("producer down"))
        try:
            with self.assertRaises(orchestrator.OrchestrationError):
                _run(client=client)
        finally:
            orchestrator.producer.build_manifest = original

    def test_token_never_appears_in_manifest_or_audit(self):
        client = FakeJevClient(responder=_responder())
        result, _ = _run(client=client)
        self.assertNotIn(FAKE_TOKEN, json.dumps(result.manifest))
        self.assertNotIn(FAKE_TOKEN, json.dumps(result.audit, default=str))
        # and the fallback reason path never mentions it either
        client = FakeJevClient(jev_client.ClientResult(outcome=jev_client.AUTH_REJECTED, status=401, detail="HTTP 401"))
        result, _ = _run(client=client)
        self.assertNotIn(FAKE_TOKEN, json.dumps(result.manifest))

    def test_no_partial_mixing_jev_fields_absent_from_fallback(self):
        # A Jev candidate with priorityOrder + intelligenceConsulted that fails the floor must leave NO trace.
        client = FakeJevClient(responder=_responder(yes_domains={"file-security"}, priorities={"file-security": 3.0}, reuse_yes={"rec-ok"}))
        result, _ = _run(client=client, reusable_records=[jev_adapter.ReusableRecordSummary("rec-ok", "BOLA/IDOR", "a/R.cs")])
        self.assertEqual(result.jev_outcome, "below_floor")
        self.assertNotIn("priorityOrder", result.manifest)
        self.assertNotIn("intelligenceConsulted", result.manifest)
        self.assertEqual(result.manifest["producedBy"], "built_in")

    def test_every_outcome_manifest_passes_the_same_validator(self):
        scenarios = {
            "no_token": (None, FakeJevClient(responder=_responder())),
            "invalid_token": (FAKE_TOKEN, FakeJevClient(jev_client.ClientResult(outcome=jev_client.AUTH_REJECTED, status=401, detail="x"))),
            "timeout": (FAKE_TOKEN, FakeJevClient(jev_client.ClientResult(outcome=jev_client.TIMEOUT, detail="x"))),
            "incomplete_output": (FAKE_TOKEN, FakeJevClient(jev_client.ClientResult(outcome=jev_client.INVALID_JSON, status=200, detail="x"))),
            "below_floor": (FAKE_TOKEN, FakeJevClient(responder=_responder(yes_domains={"file-security"}))),
            "success": (FAKE_TOKEN, FakeJevClient(responder=_responder())),
        }
        floor = _targeted_kwargs()["classification"]
        for outcome, (token, client) in scenarios.items():
            with self.subTest(outcome=outcome):
                result, _ = _run(client=client, token=token)
                self.assertEqual(result.jev_outcome, outcome)
                revalidated = validate_manifest({k: v for k, v in result.manifest.items() if k != "validity"}, floor=floor)
                self.assertTrue(revalidated.passed, revalidated.failed_checks)


class DeepModeTests(unittest.TestCase):
    def test_deep_uses_section_3a_floor_for_jev_too(self):
        # Rule out every web-security Scope item (Case 2's shape) -> a 9-domain floor.
        facts = {k: Fact(True, "HIGH", "CODE_EVIDENCE") for k in (
            "no_html_or_script_ever_rendered", "never_uses_cookie_or_ambient_auth_for_state_change",
            "no_browser_page_produced", "no_browser_side_script_shipped",
            "no_user_influenced_redirect_issued", "no_cors_headers_or_cross_origin_registration",
        )}
        floor = Classification.for_deep(facts)
        self.assertNotIn("web-security", floor.implicated_domains)  # not all 10 -> a real floor to test against
        client = FakeJevClient(responder=lambda s, q: ok(answer_payload(
            jev_adapter.JevRequest(s, q), yes_domains=set(floor.implicated_domains) - {"authorization"}, review_budget="AUDIT",
        )))
        result = orchestrator.produce_manifest(review_mode="DEEP", baseline_facts=facts, token_provider=lambda: FAKE_TOKEN, client_factory=CountingFactory(client))
        self.assertEqual(result.jev_outcome, "below_floor")
        self.assertIn("authorization", result.manifest["degradation"]["fallbackReason"])
        self.assertEqual(set(result.manifest["domains"]), set(floor.implicated_domains))


if __name__ == "__main__":
    unittest.main()
