"""V4 release -- the out-of-scope-caller rule (plays/finding-validation.md) and its caller-scope case set.

Whether a reviewer reaches the right verdict on a fixture is a semantic judgment made by a review run over
tests/fixtures/ (tests/validation/v4-caller-scope-expected-results.md); it is not asserted here. This file pins
the rule text that verdict depends on, so it cannot drift silently:

- the rule is split by vulnerability class; the "attacker-controlled parameter" presumption is limited to the
  injection class and to sinks whose unsafe behaviour and data flow are evidenced directly;
- an authorization-class sink is never CONFIRMED from "public" or "unseen caller" alone: in-scope paths and their
  checks decide, and an undecidable caller/control gives NEEDS_VERIFICATION;
- a separately unsafe in-scope path is never erased by unseen or other safe callers;
- the wording the release review found unsafe (an in-scope caller never makes a candidate REJECTED, without a class
  limit) is gone;
- the case set exists on disk, matches its expected-results table, covers required behaviours 1-5, and stays out of
  the V3 corpus.
"""

from __future__ import annotations

import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FIXTURE_DIR = os.path.join(REPO, "tests", "fixtures", "caller_scope")
RULE_HEADING = "**Rule — a sink whose callers are outside the review scope.**"


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as fh:
        return fh.read()


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _rule():
    play = _read("plays", "finding-validation.md")
    assert play.count(RULE_HEADING) == 1
    section = play.split(RULE_HEADING, 1)[1].split("\n## ", 1)[0]
    return section


def _block(rule, starts_with):
    """The paragraph of the rule's text block that starts with `starts_with` (up to the next blank line)."""
    code = rule.split("```text", 1)[1].split("```", 1)[0]
    for para in code.split("\n\n"):
        if para.strip().startswith(starts_with):
            return _flat(para)
    raise AssertionError(f"no rule branch starting with {starts_with!r}")


class RuleTextTests(unittest.TestCase):
    def setUp(self):
        self.rule = _rule()
        self.flat = _flat(self.rule)

    def test_injection_presumption_is_limited_by_class_and_evidence(self):
        inj = _block(self.rule, "Injection-class sink")
        self.assertIn("ONLY when ALL three are shown directly from the code", inj)
        self.assertIn("evidenced AT the sink", inj)
        self.assertIn("not inferred from a name or type", inj)
        self.assertIn("treat that parameter as attacker-controlled: result CONFIRMED", inj)
        self.assertIn("if any of the three cannot be shown, the presumption does not apply", inj)
        for word in ("SQL", "path traversal"):
            self.assertIn(word, inj)
        for word in ("IDOR", "BOLA", "authorization"):
            self.assertNotIn(word, inj)

    def test_authorization_is_never_confirmed_from_public_or_unseen_callers(self):
        authz = _block(self.rule, "Authorization-class sink")
        for word in ("BOLA", "IDOR", "function-level"):
            self.assertIn(word, authz)
        self.assertIn("NOT evidence of a missing control", authz)
        self.assertIn("never CONFIRMED because the method is public or because a caller is unseen", authz)
        self.assertIn("no presumption applies", authz)
        self.assertIn("with no such check is CONFIRMED on that path's own evidence", authz)
        self.assertIn("NEEDS_VERIFICATION, naming the missing caller or control", authz)

    def test_a_role_check_does_not_satisfy_object_level_authorization(self):
        # adversarial case chosen with Jev (release cycle 2): an in-scope caller that checks the role but never the
        # object's owner must not make an object-level candidate REJECTED
        authz = _block(self.rule, "Authorization-class sink")
        self.assertIn("object-level: an ownership or tenant check on THIS object", authz)
        self.assertIn("a role check or authentication alone does not satisfy it", authz)

    def test_injection_presumption_survives_a_caller_that_escapes_and_needs_evidence_not_names(self):
        # adversarial cases chosen with Jev: sanitising only in the in-scope caller does not clear a public sink; a
        # raw-query-looking name whose body binds parameters is not evidence; a helper that contains the path itself
        # is not a flow "with nothing in between"
        inj = _block(self.rule, "Injection-class sink")
        self.assertIn("an in-scope caller that happens to pass a safe value does not make it REJECTED", inj)
        self.assertIn("not inferred from a name or type", inj)
        self.assertIn("sanitizes, validates, encodes, contains or parameterizes it", inj)

    def test_other_classes_get_no_presumption(self):
        other = _block(self.rule, "Every other class")
        self.assertIn("no presumption applies", other)

    def test_an_unsafe_in_scope_path_is_never_erased(self):
        anyc = _block(self.rule, "Any class")
        self.assertIn("never erase the evidence of a separately unsafe in-scope path", anyc)
        self.assertIn("one unsafe path is enough to CONFIRM", anyc)
        self.assertIn("callers that provably constrain the value make it REJECTED", anyc)

    def test_the_wording_the_release_review_rejected_is_gone(self):
        # 67908c0's unconditional "an in-scope caller ... never makes the candidate REJECTED on its own" (no class
        # limit) let an authorization sink controlled in its caller read as CONFIRMED.
        self.assertNotIn("it never makes the candidate REJECTED on its own", self.flat)
        self.assertNotIn("the method's own signature is the trust boundary", self.flat)

    def test_closing_paragraph_states_both_directions(self):
        self.assertIn("never make an authorization-class sink CONFIRMED", self.flat)
        self.assertIn("Unseen callers alone never make an injection-class sink NEEDS_VERIFICATION", self.flat)

    def test_skill_pointers_reference_the_rule_and_its_class_split(self):
        review = _flat(_read("skills", "security-review", "SKILL.md"))
        self.assertIn("depends on the vulnerability class (injection vs. authorization)", review)
        self.assertIn("Rule — a sink whose callers are outside the review scope", review)
        self.assertIn("out-of-scope-caller rule", _read("skills", "security-validate", "SKILL.md"))


def _cases_on_disk():
    return {n for n in os.listdir(FIXTURE_DIR) if not n.startswith(".")}


def _expected_doc():
    return _read("tests", "validation", "v4-caller-scope-expected-results.md")


class CaseSetTests(unittest.TestCase):
    def test_every_case_on_disk_has_exactly_one_expected_row_and_vice_versa(self):
        doc = _expected_doc()
        rows = [ln for ln in doc.split("## How the rule's", 1)[0].splitlines() if ln.startswith("| `")]
        named = {re.match(r"\| `([^`]+)`", ln).group(1).rstrip("/") for ln in rows}
        self.assertEqual(named, _cases_on_disk())
        self.assertEqual(len(rows), len(_cases_on_disk()))

    def test_summary_counts_match_the_table(self):
        doc = _expected_doc()
        rows = [ln for ln in doc.split("## How the rule's", 1)[0].splitlines() if ln.startswith("| `")]
        confirmed = [ln for ln in rows if "| CONFIRMED" in ln]
        self.assertIn(f"must produce a CONFIRMED finding:     {len(confirmed)}", doc)
        self.assertIn(f"must NOT produce a CONFIRMED finding: {len(rows) - len(confirmed)}", doc)

    def test_required_behaviours_1_to_5_each_name_an_existing_case(self):
        doc = _expected_doc().split("## How the rule's", 1)[1]
        rows = [ln for ln in doc.splitlines() if re.match(r"\| [1-5] \|", ln)]
        self.assertEqual([r.split("|")[1].strip() for r in rows], ["1", "2", "3", "4", "5"])
        for r in rows:
            names = [n for n in re.findall(r"`([^`]+)`", r.split("|")[3]) if n.endswith("/") or re.search(r"\.\w+$", n)]
            self.assertTrue(names, r)
            for name in names:
                base = name.rstrip("/")
                with self.subTest(case=name):
                    self.assertTrue(os.path.exists(os.path.join(REPO, "tests", "fixtures", base))
                                    or os.path.exists(os.path.join(FIXTURE_DIR, base)), name)

    def test_the_set_stays_out_of_the_v3_corpus(self):
        v3 = _read("tests", "validation", "expected-results.md")
        v3_rows = [ln for ln in v3.splitlines() if ln.startswith("| `")]
        self.assertEqual(len(v3_rows), 39)
        self.assertFalse([ln for ln in v3_rows if any(n in ln for n in _cases_on_disk()) or "caller_scope" in ln])
        self.assertIn("tests/validation/v4-caller-scope-expected-results.md", v3)
        self.assertIn("`tests/fixtures/caller_scope/`", _read("tests", "validation", "README.md"))

    def test_every_case_header_states_its_expected_outcome(self):
        for name in sorted(_cases_on_disk()):
            path = os.path.join(FIXTURE_DIR, name)
            files = [os.path.join(path, f) for f in sorted(os.listdir(path))] if os.path.isdir(path) else [path]
            with self.subTest(case=name):
                heads = [open(f, encoding="utf-8").read(1500) for f in files]
                self.assertTrue(any("Expected review outcome:" in h for h in heads))


if __name__ == "__main__":
    unittest.main()
