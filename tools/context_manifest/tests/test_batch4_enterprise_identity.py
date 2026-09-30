"""V4 Batch 4 -- enterprise identity (AD/SSO) integration check.

Batch 4 (implementation-batches.md, "Batch 4"; waiver of the Batch 2.5 gate
recorded there, 2026-09-25; protocol scope and placement decided in
v4-design.md section 6): plays/enterprise-identity-security.md, routed inside
the existing `authentication` domain, first-version protocols OIDC/OAuth 2.0 +
JWT, direct LDAP/LDAPS and Windows Integrated Authentication.

Whether a reviewer reaches the right verdict on a fixture is a semantic
judgment: it is traced by hand in
tests/validation/v4-enterprise-identity-test-cases.md, not asserted here.
This file checks the structure that the trace depends on, so it cannot
drift silently: every fixture exists and has an expected result; every
fixture pair is complete; the set stays out of the V3 corpus counts; every
Scope item has its section; routing rows point at the play; there is one
copy of the signal list; the Context Manifest contract is unchanged (no new
domain); and the no-token and Jev-degraded paths still yield the
`authentication` domain through which the play is reached.
"""

from __future__ import annotations

import os
import re
import unittest

from .. import orchestrator, schema
from ..domains import ALL_DOMAINS
from ..validator import Classification
from .jev_fakes import CountingFactory, FakeJevClient, answer_payload, ok
from .. import jev_adapter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PLAY = os.path.join(REPO, "plays", "enterprise-identity-security.md")
FIXTURE_DIR = os.path.join(REPO, "tests", "fixtures", "enterprise_identity")
CASES_DOC = os.path.join(REPO, "tests", "validation", "v4-enterprise-identity-test-cases.md")
FAKE_TOKEN = "fake-test-token-not-a-real-credential"
PLAY_REF = "plays/enterprise-identity-security.md"


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as fh:
        return fh.read()


def _fixtures_on_disk():
    return {n for n in os.listdir(FIXTURE_DIR) if not n.startswith(".")}


def _batch4_expected():
    return _read("tests", "validation", "v4-enterprise-identity-expected-results.md")


def _code_block_after(text, heading):
    section = text.split(heading, 1)[1]
    return section.split("```text", 1)[1].split("```", 1)[0]


class PlayStructureTests(unittest.TestCase):
    def setUp(self):
        self.text = _read("plays", "enterprise-identity-security.md")

    def test_every_scope_item_has_its_own_section(self):
        items = [ln.strip() for ln in _code_block_after(self.text, "## Scope").splitlines() if ln.strip()]
        self.assertEqual(len(items), 6, items)
        headings = set(re.findall(r"^## (.+)$", self.text, flags=re.M))
        for item in items:
            with self.subTest(item=item):
                self.assertIn(item, headings)

    def test_first_version_protocols_and_boundaries_are_stated(self):
        for needle in ("OIDC / OAuth 2.0", "LDAP / LDAPS", "Windows Integrated",
                       "It is not an audit of the enterprise AD / Entra environment",
                       "SAML 2.0 and WS-Federation are not covered in this version",
                       "No live validation is implied"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_rules_added_by_the_independent_review_stay_present(self):
        # batch4-verification-log.md section 7: CSRF for the ambient Negotiate credential, app-only tokens
        # (scp/roles), NUL in an LDAP bind password, protections that are off by default stated as "enabled"
        for needle in ("Ambient        the browser sends Negotiate/NTLM automatically",
                       "anti-forgery token or custom header (plays/web-security.md's\n                 CSRF section)",
                       "delegated scope (scp) or the app role (roles)",
                       "or one containing a NUL\n                 character",
                       "ENABLED (IIS tokenChecking Allow/Require; its default is\n                 None)",
                       "LdapConnection: SessionOptions.Signing/Sealing\n               set, default off"):
            with self.subTest(needle=needle[:40]):
                self.assertIn(needle, self.text)

    def test_generic_rules_are_referenced_not_copied(self):
        # the generic authentication/authorization procedures stay in their own plays
        for ref in ("plays/authentication.md", "plays/authorization.md", "plays/finding-validation.md",
                    "plays/code-review.md"):
            self.assertIn(ref, self.text)
        for generic_heading in ("## Session fixation", "## Insecure password reset", "## IDOR / BOLA"):
            self.assertNotIn(generic_heading, self.text)


class FixtureInventoryTests(unittest.TestCase):
    def test_disk_expected_results_and_case_doc_name_the_same_fixtures(self):
        on_disk = _fixtures_on_disk()
        section = _batch4_expected()
        expected = set(re.findall(r"^\| `([^`]+\.cs)` \|", section, flags=re.M))
        doc = set(re.findall(r"`([a-z_]+_(?:safe|unsafe|deceptive)\.cs)`", _read("tests", "validation",
                                                                                   "v4-enterprise-identity-test-cases.md")))
        self.assertEqual(len(on_disk), 13, sorted(on_disk))
        self.assertEqual(on_disk, expected)
        self.assertEqual(on_disk, doc)

    def test_every_check_row_is_a_complete_pair(self):
        doc = _read("tests", "validation", "v4-enterprise-identity-test-cases.md")
        section_a = doc.split("## A.", 1)[1].split("### Traces", 1)[0]
        rows = [r for r in section_a.splitlines() if re.match(r"^\| \d+[a-z]? \|", r)]
        self.assertEqual([r.split("|")[1].strip() for r in rows], ["1", "1w", "2", "3", "4", "4c", "5"])
        for row in rows:
            names = re.findall(r"`([a-z_]+\.cs)`", row)
            with self.subTest(row=row.split("|")[1].strip()):
                if row.startswith("| 5 |"):
                    self.assertEqual([n for n in names if n.endswith("_deceptive.cs")], names)
                    self.assertEqual(len(names), 1)
                else:
                    self.assertEqual(len(names), 2)
                    self.assertTrue(names[0].endswith("_unsafe.cs") and names[1].endswith("_safe.cs"), names)

    def test_every_fixture_has_a_hand_trace(self):
        doc = _read("tests", "validation", "v4-enterprise-identity-test-cases.md")
        traces = doc.split("### Traces", 1)[1].split("## B.", 1)[0]
        traced = set(re.findall(r"^\| T\d+ \| `([^`]+)` \|", traces, flags=re.M))
        self.assertEqual(traced, _fixtures_on_disk())

    def test_summary_counts_match_the_table(self):
        section = _batch4_expected()
        rows = re.findall(r"^\| `([^`]+\.cs)` \| ([^|]+) \|", section, flags=re.M)
        confirmed = [n for n, outcome in rows if outcome.strip().startswith("CONFIRMED")]
        clean = [n for n, outcome in rows if outcome.strip().startswith("No confirmed finding")]
        self.assertEqual((len(confirmed), len(clean)), (7, 6))
        self.assertTrue(all(n.endswith(("_unsafe.cs", "_deceptive.cs")) for n in confirmed), confirmed)
        self.assertTrue(all(n.endswith("_safe.cs") for n in clean), clean)
        self.assertIn("must produce a CONFIRMED finding:     7", section)
        self.assertIn("must NOT produce a CONFIRMED finding: 6", section)

    def test_the_set_stays_out_of_the_v3_corpus(self):
        # the V3 corpus table (read as such by tools/batch25_measurement/recall_groups.py) keeps its 39 rows,
        # none of them for this set, and its summary counts are unchanged
        v3 = _read("tests", "validation", "expected-results.md")
        v3_rows = [ln for ln in v3.splitlines() if ln.startswith("| `")]
        self.assertEqual(len(v3_rows), 39)
        batch4_names = _fixtures_on_disk()
        self.assertFalse([ln for ln in v3_rows if any(n in ln for n in batch4_names) or "enterprise_identity" in ln])
        self.assertIn("Must produce a CONFIRMED finding:      20", v3)
        self.assertIn("Must NOT produce a CONFIRMED finding:  18", v3)
        self.assertIn("tests/validation/v4-enterprise-identity-expected-results.md", v3)   # pointer, not rows
        self.assertIn("exclude\n   `tests/fixtures/enterprise_identity/`", _read("tests", "validation", "README.md"))

    def test_fixture_headers_state_their_expected_outcome(self):
        for name in sorted(_fixtures_on_disk()):
            with self.subTest(name=name):
                head = open(os.path.join(FIXTURE_DIR, name), encoding="utf-8").read(1500)
                self.assertIn("Expected review outcome:", head)
                self.assertIn(PLAY_REF, head)
                if name.endswith("_safe.cs"):
                    self.assertIn("no confirmed finding", head)
                else:
                    self.assertIn("CONFIRMED", head)


class RoutingTests(unittest.TestCase):
    def test_review_domain_table_and_quick_reference_route_to_the_play(self):
        skill = _read("skills", "security-review", "SKILL.md")
        row = [ln for ln in skill.splitlines() if ln.startswith("| Enterprise identity integration")]
        self.assertEqual(len(row), 1)
        self.assertIn(PLAY_REF, row[0])
        self.assertIn("`authentication` domain", row[0])
        quick = _read("skills", "security-review", "references", "quick-reference.md")
        self.assertTrue(any(PLAY_REF in ln and "LdapConnection" in ln for ln in quick.splitlines()))

    def test_design_activation_list_routes_to_the_play(self):
        design = _read("skills", "security-design", "SKILL.md")
        activation = _code_block_after(design, "## When to use")
        self.assertIn("enterprise identity integration (SSO/OIDC, AD/LDAP, Windows Integrated Authentication)", activation)
        self.assertIn(PLAY_REF, design)

    def test_change_detection_classifies_identity_integration_high_and_points_at_the_one_signal_list(self):
        detection = _read("plays", "security-change-detection.md")
        high = _code_block_after(detection, "### HIGH")
        self.assertIn("enterprise\nidentity integration", high)
        self.assertIn("plays/enterprise-identity-security.md's \"When this\n  play applies\"", detection)
        # one copy of the signal list: the play's own tokens are not repeated in the detection play
        signals = _code_block_after(_read("plays", "enterprise-identity-security.md"), "## When this play applies")
        for token in ("AddNegotiate", "LdapConnection", "DirectoryEntry", "PrincipalContext", "AddOpenIdConnect",
                      "ldap3", "ldapjs", "openid-client"):
            with self.subTest(token=token):
                self.assertIn(token, signals)
                self.assertNotIn(token, detection)

    def test_authentication_play_points_at_the_new_play(self):
        self.assertIn(PLAY_REF, _read("plays", "authentication.md"))


class ContractTests(unittest.TestCase):
    """D2: the play lives inside the existing `authentication` domain -- no manifest contract change."""

    def test_no_new_domain_and_manifest_version_unchanged(self):
        self.assertIn("authentication", ALL_DOMAINS)
        self.assertEqual(len(ALL_DOMAINS), 10)
        self.assertFalse([d for d in ALL_DOMAINS if "identity" in d or "enterprise" in d or "sso" in d])
        self.assertEqual(schema.MANIFEST_VERSION, "1.0")


def _identity_classification():
    return Classification(sensitivity="HIGH", implicated_domains=frozenset({"authentication", "authorization"}))


def _responder(yes_domains):
    def respond(state, questions):
        return ok(answer_payload(jev_adapter.JevRequest(state=state, questions=questions),
                                 yes_domains=yes_domains, review_budget="ELEVATED", sensitivity="HIGH"))
    return respond


def _run(client, token=FAKE_TOKEN):
    factory = CountingFactory(client) if client is not None else None
    return orchestrator.produce_manifest(
        review_mode="TARGETED",
        classification=_identity_classification(),
        target_change_files=["src/Identity/DirectoryLoginController.cs"],
        diff_summary="adds an LDAPS bind-based login and a group-membership authorization handler",
        token_provider=lambda: token,
        client_factory=factory,
    )


class DegradedModeTests(unittest.TestCase):
    """The play is reached through the `authentication` domain on every producer path."""

    def test_no_token_built_in_manifest_carries_the_authentication_domain(self):
        r = _run(None, token=None)
        self.assertEqual((r.produced_by, r.jev_outcome), ("built_in", "no_token"))
        self.assertTrue(r.manifest["validity"]["passed"])
        self.assertTrue({"authentication", "authorization"} <= set(r.manifest["domains"]))
        self.assertEqual(r.manifest["sensitivity"], "HIGH")

    def test_jev_dropping_the_authentication_domain_falls_back_to_the_floor(self):
        r = _run(FakeJevClient(responder=_responder({"code-review", "authorization"})))
        self.assertEqual((r.produced_by, r.jev_outcome), ("built_in", "below_floor"))
        self.assertTrue(r.manifest["degradation"]["fallbackUsed"])
        self.assertIn("authentication", r.manifest["domains"])

    def test_jev_keeping_the_floor_is_accepted_and_still_routes_to_the_domain(self):
        r = _run(FakeJevClient(responder=_responder({"authentication", "authorization"})))
        self.assertEqual(r.produced_by, "jev")
        self.assertTrue({"authentication", "authorization"} <= set(r.manifest["domains"]))
        self.assertTrue(r.manifest["validity"]["passed"])


if __name__ == "__main__":
    unittest.main()
