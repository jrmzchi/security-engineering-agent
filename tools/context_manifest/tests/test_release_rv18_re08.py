"""RV-18 and RE-08 regressions (V4 release, protocol revision 8).

RV-18 (`csrf_samesite_lax_deceptive.cs`, expected CONFIRMED CSRF): in revisions 6 and 7 item 0 left out web-security.
The revision-7 runner read only the listed domains' plays and missed the CSRF. The fix:
- signal_floor.py adds web-security whenever the scope shows an ambient browser credential together with a
  state-changing endpoint;
- produce_manifest() applies that floor to both producers;
- SKILL step 5 states that `domains` is a minimum that must be read, not a boundary on findings.

RE-08 (`group_lookup_fail_closed_safe.cs`, expected safe): a review CONFIRMED "authorization keyed to a mutable DN".
The case has no attacker path to that value (work/v4-release/re08-group-identifier-evidence.md). The play's
stable-identifier rule now decides by trust boundary and attacker privilege, not by field name.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO)
from tools.context_manifest import orchestrator, producer, signal_floor  # noqa: E402
from tools.context_manifest.validator import Classification, validate_manifest  # noqa: E402

FIX = os.path.join(REPO, "tests", "fixtures")
RV18 = os.path.join(FIX, "csrf_samesite_lax_deceptive.cs")
RE08 = os.path.join(FIX, "enterprise_identity", "group_lookup_fail_closed_safe.cs")


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as fh:
        return fh.read()


def _code(path):
    """The file as a reviewer of the case sees it: comment lines removed."""
    with open(path, encoding="utf-8") as fh:
        return "\n".join(ln for ln in fh.read().splitlines() if not ln.lstrip().startswith(("//", "#")))


def _case_texts(fixture):
    path = os.path.join(FIX, fixture)
    if os.path.isdir(path):
        return {f: _code(os.path.join(path, f)) for f in sorted(os.listdir(path))}
    return {os.path.basename(path): _code(path)}


def _flat(text):
    return re.sub(r"\s+", " ", text)


class SignalFloorTests(unittest.TestCase):
    def test_rv18_requires_web_security(self):
        r = signal_floor.required_domains({"case.cs": _code(RV18)})
        self.assertEqual(r.domains, frozenset({"web-security"}))
        self.assertEqual(len(r.reasons), 1)
        self.assertTrue(r.reasons[0].startswith("CSRF-AMBIENT:"))

    def test_both_halves_are_needed(self):
        code = _code(RV18)
        no_cookie = code.replace("services.ConfigureApplicationCookie(", "services.Configure(")
        self.assertEqual(signal_floor.required_domains({"a.cs": no_cookie}).domains, frozenset())
        read_only = code.replace('[HttpGet("delete")]', '[HttpGet("profile")]')
        self.assertEqual(signal_floor.required_domains({"a.cs": read_only}).domains, frozenset())
        self.assertEqual(signal_floor.required_domains({}).domains, frozenset())

    def test_the_halves_may_sit_in_different_files_of_one_scope(self):
        r = signal_floor.required_domains({"Startup.cs": "services.AddAuthentication().AddCookie();",
                                           "AccountController.cs": '[HttpPost("transfer")] public IActionResult T() => Ok();'})
        self.assertEqual(r.domains, frozenset({"web-security"}))

    def test_the_rule_is_general_not_an_rv18_special_case(self):
        cases = {
            "express session + POST": ("const session = require('express-session');\napp.post('/pay', h);", True),
            "flask session + POST": ("from flask import Flask, session\n@app.route('/x', methods=['POST'])", True),
            "windows auth + MapDelete": ("builder.Services.AddAuthentication(NegotiateDefaults.AuthenticationScheme)"
                                          ".AddNegotiate();\napp.MapDelete(\"/items/{id}\", h);", True),
            "cookie + GET delete via router": ("const s = require('cookie-session');\nrouter.get('/account/delete', h);", True),
            "bearer token API + POST": ("services.AddAuthentication().AddJwtBearer();\n[HttpPost] public IActionResult P() => Ok();", False),
            "cookie + read-only GET": ("services.ConfigureApplicationCookie(o => {});\n[HttpGet(\"report\")] public IActionResult R() => Ok();", False),
        }
        for name, (text, fires) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(signal_floor.required_domains({"f": text}).domains == {"web-security"}, fires)

    def test_across_the_release_corpus_the_floor_fires_only_on_the_signal_pair(self):
        manifest = json.loads(_read("tests", "validation", "v4-release-corpus-v5-manifest.json"))
        fired = set()
        for row in manifest["rows"]:
            if signal_floor.required_domains(_case_texts(row["fixture"])).domains:
                fired.add(row["caseId"])
        for f in sorted(os.listdir(os.path.join(FIX, "enterprise_identity"))):
            if signal_floor.required_domains(_case_texts(os.path.join("enterprise_identity", f))).domains:
                fired.add(f)
        self.assertEqual(fired, {"RV-18", "RV-28", "windows_auth_header_trust_unsafe.cs", "windows_auth_negotiate_safe.cs",
                                 "ldap_bind_empty_password_deceptive.cs"})

    def test_bad_input_is_rejected(self):
        for bad in (["a"], {"a": 1}, {1: "x"}):
            with self.subTest(bad=bad), self.assertRaises(TypeError):
                signal_floor.required_domains(bad)


class ProduceManifestFloorTests(unittest.TestCase):
    NARROW = Classification(sensitivity=None, implicated_domains=frozenset({"authentication", "authorization"}))

    def produce(self, **kw):
        return orchestrator.produce_manifest(review_mode="STANDARD", classification=self.NARROW,
                                             target_change_files=["case_15.cs"], token_provider=lambda: None, **kw)

    def test_the_floor_adds_web_security_to_item_0s_domains(self):
        res = self.produce(scope_texts={"case_15.cs": _code(RV18)})
        self.assertEqual(set(res.manifest["domains"]), {"authentication", "authorization", "web-security"})
        self.assertTrue(res.manifest["validity"]["passed"])
        self.assertEqual(len(res.audit["signalFloor"]), 1)

    def test_without_scope_texts_or_signals_nothing_changes(self):
        self.assertEqual(set(self.produce().manifest["domains"]), {"authentication", "authorization"})
        res = self.produce(scope_texts={"case.cs": _code(RE08)})
        self.assertEqual(set(res.manifest["domains"]), {"authentication", "authorization"})
        self.assertNotIn("signalFloor", res.audit)

    def test_the_floor_never_removes_a_domain(self):
        wide = Classification(sensitivity=None, implicated_domains=frozenset({"file-security", "api-security"}))
        res = orchestrator.produce_manifest(review_mode="STANDARD", classification=wide, target_change_files=["x"],
                                            scope_texts={"x": _code(RV18)}, token_provider=lambda: None)
        self.assertEqual(set(res.manifest["domains"]), {"file-security", "api-security", "web-security"})

    def test_a_manifest_without_the_floor_domain_fails_validation(self):
        narrow = producer.build_manifest(review_mode="STANDARD", target_change_files=["case_15.cs"],
                                         classification=self.NARROW)
        widened = Classification(sensitivity=None, implicated_domains=self.NARROW.implicated_domains | {"web-security"})
        self.assertFalse(validate_manifest(narrow, floor=widened).passed)


class GuidanceTests(unittest.TestCase):
    def test_skill_states_domains_are_a_minimum_and_step_1_passes_scope_texts(self):
        skill = _flat(_read("skills", "security-review", "SKILL.md"))
        step5 = skill.split("5. **Manual semantic analysis.**", 1)[1].split("6. **Potential findings.**", 1)[0]
        self.assertIn("**`domains` is the minimum, not a boundary.**", step5)
        self.assertIn("Do not dismiss it as outside the reviewed domains.", step5)
        self.assertIn("This adds the one play the candidate needs, not every play.", step5)
        self.assertIn("Reading each selected domain's play is not optional.", step5)
        self.assertIn("Pass the texts of the files in scope as `scope_texts`", skill)

    def test_budget_and_change_detection_agree(self):
        self.assertIn("That set is a minimum, not a boundary on findings.", _flat(_read("plays", "review-budget.md")))
        cd = _flat(_read("plays", "security-change-detection.md"))
        self.assertIn("## Domains a signal pair requires", cd)
        self.assertIn("-> web-security (CSRF", cd)
        self.assertIn("`tools/context_manifest/signal_floor.py` applies the same rule", cd)

    def test_the_web_security_play_decides_rv18(self):
        web = _flat(_read("plays", "web-security.md"))
        self.assertIn("**`SameSite=Lax` does not protect a state-changing GET endpoint.**", web)


class Re08TrustBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.code = _code(RE08)

    def test_the_group_dn_is_a_constant_and_the_identity_is_the_authenticated_principal(self):
        self.assertRegex(self.code, r'private const string ApproversGroupDn = "CN=Finance Approvers,OU=Groups,DC=corp,DC=example";')
        self.assertIn("var upn = context.User.Identity?.Name;", self.code)
        self.assertIn("await _groups.IsMemberAsync(upn, ApproversGroupDn, cts.Token)", self.code)
        self.assertNotRegex(self.code, r"Request\.|Query|Headers|FromBody|FromQuery|Claims\.First")

    def test_success_only_on_membership_and_failure_denies(self):
        self.assertEqual(self.code.count("context.Succeed(requirement);"), 1)
        catch = self.code.split("catch (Exception ex)", 1)[1]
        self.assertNotIn("Succeed", catch)
        self.assertIn("if (upn is null)", self.code)

    def test_the_rule_decides_by_trust_boundary_not_field_name(self):
        play = _flat(_read("plays", "enterprise-identity-security.md"))
        self.assertIn("a display name is neither unique nor a security identity key. An authorization decision keyed "
                      "on one is a finding.", play)
        self.assertIn("(sAMAccountName, a distinguished name): decide from the case's actual trust boundary and "
                      "attacker privileges, never from the field name alone.", play)
        self.assertIn("(fail-closed): an availability / configuration risk, recorded in the notes. Not a security finding.", play)
        self.assertIn("an environment fact (directory permissions), recorded as an assumption", play)
        self.assertIn("a security finding only when the code in scope shows one of these: an ambiguous match across "
                      "scopes", play)
        for kept in ('"Any signed-in domain / tenant user" used as the gate', "Group-claim overage ignored",
                     "catch around token validation, bind or group lookup"):
            self.assertIn(kept, play)


if __name__ == "__main__":
    unittest.main()
