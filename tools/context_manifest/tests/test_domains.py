"""Tests for tools/context_manifest/domains.py and scope_coverage.py.

Covers implementation-batches.md Batch 0 acceptance criteria 6 and 7:
  - criterion 6(a): Case 1, exactly 3-of-10 (count computed fresh, never
    hardcoded here as a bare literal disconnected from the fact list --
    see test_case_1).
  - criterion 6(b)/(c)/(d): the three required counterexamples.
  - criterion 6(e): Case 1b, exactly 6-of-10.
  - criterion 6(f): Case 2, exactly 9-of-10.
  - criterion 6(g): Case 3, all ten.
  - criterion 7a/7c: live Scope parse vs. this module's rule table,
    symmetric, both directions (test_scope_coverage_matches_live_plays
    and the three mutation tests below it).
  - criterion 7b/7d: per-item isolation, including the three named
    regressions (insecure random generation, request smuggling,
    non-shared-dir temporary files).
"""

from __future__ import annotations

import unittest
from typing import Dict

from .. import domains
from .. import scope_coverage
from ..domains import Fact, compute_deep_domains, fact_from_baseline_entry


def high(value=True, source="CODE_EVIDENCE") -> Fact:
    return Fact(value=value, confidence="HIGH", source=source)


class FactGatingTests(unittest.TestCase):
    """[FIXED, per a round-2 independent review Major]: `Fact.is_positive()`'s
    three gating conditions (confidence == HIGH, source in
    SOURCE_POSITIVE, value == expected) had no test that discriminated
    weakening any ONE of them from the others -- four mutations
    (accepting MEDIUM confidence; adding INFERRED to SOURCE_POSITIVE;
    dropping the value comparison; dropping the source check entirely)
    all still passed the full suite, because the only prior tests of
    this property (Group2CounterexampleTests' "weak" fixtures) weakened
    BOTH facts of a two-fact exclusion at once, which a broken
    is_positive() could still correctly leave inconclusive on other
    grounds. Each test below weakens exactly one gating condition on
    exactly one fact while keeping everything else at genuine full
    strength."""

    def test_is_positive_requires_high_confidence(self):
        self.assertTrue(Fact(True, "HIGH", "CODE_EVIDENCE").is_positive())
        for weak_confidence in ("MEDIUM", "LOW", "UNKNOWN"):
            self.assertFalse(Fact(True, weak_confidence, "CODE_EVIDENCE").is_positive())

    def test_is_positive_requires_positive_source(self):
        self.assertTrue(Fact(True, "HIGH", "CODE_EVIDENCE").is_positive())
        for weak_source in ("INFERRED", "NONE"):
            self.assertFalse(Fact(True, "HIGH", weak_source).is_positive())
        # [FIXED, per a round-3 independent review Minor]: SOURCE_POSITIVE
        # must be an explicit allowlist, not "anything except a known
        # bad value" -- a mutation turning it into a blacklist (e.g.
        # `source not in ("INFERRED", "NONE")`) would still pass the
        # two asserts above, since neither uses a source outside both
        # sets. An unrecognized/typo'd source string must also fail.
        self.assertFalse(Fact(True, "HIGH", "GUESS").is_positive())
        self.assertFalse(Fact(True, "HIGH", "not_a_real_source").is_positive())

    def test_is_positive_requires_value_to_equal_expected(self):
        self.assertTrue(Fact(True, "HIGH", "CODE_EVIDENCE").is_positive())
        self.assertFalse(Fact(False, "HIGH", "CODE_EVIDENCE").is_positive())
        self.assertFalse(Fact(None, "HIGH", "CODE_EVIDENCE").is_positive())
        # [FIXED, per a round-3 independent review Minor]: value must be
        # compared by EQUALITY to `expected` (True), not by truthiness --
        # a mutation using `bool(self.value) == bool(expected)` would
        # still pass the three asserts above (False and None are both
        # falsy, matching bool(False)) but would wrongly accept a
        # truthy-but-not-True value, e.g. the string "false" (a truthy
        # Python value despite its name -- exactly the kind of mistake a
        # baseline JSON field could contain).
        self.assertFalse(Fact("false", "HIGH", "CODE_EVIDENCE").is_positive())
        self.assertFalse(Fact("true", "HIGH", "CODE_EVIDENCE").is_positive())

    def test_authentication_exclusion_needs_both_facts_genuinely_strong(self):
        """Domain-level, not just Fact-in-isolation: weaken exactly one
        of authentication's two required facts (confidence, source, or
        value) while the OTHER stays fully strong -- authentication
        must stay applicable in every case, since its exclusion
        requires BOTH facts to independently pass is_positive()."""
        strong = high()
        weakenings = {
            "weak_confidence": Fact(True, "MEDIUM", "CODE_EVIDENCE"),
            "weak_source": Fact(True, "HIGH", "INFERRED"),
            "wrong_value": Fact(False, "HIGH", "CODE_EVIDENCE"),
        }
        for label, weak in weakenings.items():
            with self.subTest(weakening=label, fact="invoked_only..."):
                facts = {
                    "invoked_only_by_trusted_or_authenticated_caller": weak,
                    "no_identity_distinction_code": strong,
                }
                self.assertIn("authentication", compute_deep_domains(facts).domains)
            with self.subTest(weakening=label, fact="no_identity_distinction_code"):
                facts = {
                    "invoked_only_by_trusted_or_authenticated_caller": strong,
                    "no_identity_distinction_code": weak,
                }
                self.assertIn("authentication", compute_deep_domains(facts).domains)


ALL_TEN = frozenset(domains.ALL_DOMAINS)


class Case1And1bTests(unittest.TestCase):
    """context-manifest-schema.md Case 1 / Case 1b, facts (a)-(i) plus
    the externally-invoked/trusted-input-only extension."""

    def _case1_facts(self) -> Dict[str, Fact]:
        return {
            # (a)
            "invoked_only_by_trusted_or_authenticated_caller": high(),
            "externally_invoked_trusted_input_only": high(),
            # (b)
            "no_identity_distinction_code": high(),
            # (c)
            "no_restricted_object_or_operation": high(),
            # (d)
            "no_credential_anywhere_in_scope": high(),
            # (e) -- compound: no crypto operations AND no sensitive data flagged
            "no_cryptographic_operations": high(),
            "no_sensitive_data_flagged": high(),
            # (f)
            "no_security_relevant_random_generation": high(),
            "no_outbound_tls_connections": high(),
            # (g)
            "no_deserialization_or_xml_parsing": high(),
            # (a)+(c): operates only on files the invoking operator
            # already has direct filesystem access to
            "no_attacker_influenced_paths_or_content": high(),
            # (h)
            "temp_files_none_or_path_unpredictable": high(),
            "temp_files_none_or_private_and_cleaned_up": high(),
            "storage_location_not_attacker_influenced": high(),
            # (i)
            "no_archive_extraction_or_creation": high(),
            # no network access / no web framework -- web-security row
            "no_html_or_script_ever_rendered": high(),
            "never_uses_cookie_or_ambient_auth_for_state_change": high(),
            "no_browser_page_produced": high(),
            "no_browser_side_script_shipped": high(),
            "no_user_influenced_redirect_issued": high(),
            "no_cors_headers_or_cross_origin_registration": high(),
            # no API / outbound call surface -- api-security row
            "no_api_or_outbound_call_surface": high(),
            "no_raw_http_request_framing": high(),
        }

    def test_case_1_resolves_to_group1_only(self):
        result = compute_deep_domains(self._case1_facts())
        self.assertEqual(result.domains, domains.GROUP_1)
        self.assertEqual(len(result.domains), 3)

    def test_case_1b_invocation_context_unknown(self):
        facts = dict(self._case1_facts())
        del facts["invoked_only_by_trusted_or_authenticated_caller"]
        del facts["externally_invoked_trusted_input_only"]
        result = compute_deep_domains(facts)
        expected = domains.GROUP_1 | {"authentication", "authorization", "file-security"}
        self.assertEqual(result.domains, expected)
        self.assertEqual(len(result.domains), 6)
        self.assertNotIn("secrets-security", result.domains)
        self.assertNotIn("web-security", result.domains)
        self.assertNotIn("api-security", result.domains)
        self.assertNotIn("data-security", result.domains)


class Case2Tests(unittest.TestCase):
    """ASP.NET file-download app -- exactly 9-of-10, only web-security excluded."""

    def _case2_facts(self) -> Dict[str, Fact]:
        return {
            "no_html_or_script_ever_rendered": high(),  # "renders no HTML" + attachment-disposition, combined
            "never_uses_cookie_or_ambient_auth_for_state_change": high(),  # bearer-token only
            "no_browser_page_produced": high(),
            "no_browser_side_script_shipped": high(),
            "no_user_influenced_redirect_issued": high(),
            "no_cors_headers_or_cross_origin_registration": high(),
            # Deliberately NOT set: api/data/file ruling-out facts, and
            # Group 2 exclusion facts -- Case 2 gives no evidence any of
            # them are absent, so they stay applicable by default.
        }

    def test_case_2_resolves_to_9_of_10(self):
        result = compute_deep_domains(self._case2_facts())
        expected = ALL_TEN - {"web-security"}
        self.assertEqual(result.domains, expected)
        self.assertEqual(len(result.domains), 9)


class Case3Tests(unittest.TestCase):
    """Full-stack cross-domain app -- all ten, with zero facts supplied
    (every Group 2/3 domain defaults to applicable with no evidence)."""

    def test_case_3_resolves_to_all_ten(self):
        result = compute_deep_domains({})
        self.assertEqual(result.domains, ALL_TEN)


class Group2CounterexampleTests(unittest.TestCase):
    """implementation-batches.md criterion 6(b)/(c)/(d)."""

    def test_b_unauthenticated_internal_microservice_keeps_authentication(self):
        # No caller-identity-verification code, AND no positive
        # confirmation that no identity concept applies anywhere --
        # both facts UNKNOWN, not merely fact (i).
        result = compute_deep_domains({})
        self.assertIn("authentication", result.domains)
        # Even a LOW-confidence or INFERRED-source claim must not exclude it.
        weak = {
            "invoked_only_by_trusted_or_authenticated_caller": Fact(True, "MEDIUM", "CODE_EVIDENCE"),
            "no_identity_distinction_code": Fact(True, "HIGH", "INFERRED"),
        }
        result = compute_deep_domains(weak)
        self.assertIn("authentication", result.domains)

    def test_c_object_access_without_ownership_check_keeps_authorization(self):
        result = compute_deep_domains({})
        self.assertIn("authorization", result.domains)
        weak = {
            "invoked_only_by_trusted_or_authenticated_caller": high(),
            "no_restricted_object_or_operation": Fact(True, "LOW", "CODE_EVIDENCE"),
        }
        result = compute_deep_domains(weak)
        self.assertIn("authorization", result.domains)

    def test_d_uncatalogued_hardcoded_credential_keeps_secrets_security(self):
        result = compute_deep_domains({})
        self.assertIn("secrets-security", result.domains)
        weak = {"no_credential_anywhere_in_scope": Fact(True, "UNKNOWN", "NONE")}
        result = compute_deep_domains(weak)
        self.assertIn("secrets-security", result.domains)


class FileDownloadWithoutAuthorizeFloorTests(unittest.TestCase):
    """plays/security-change-detection.md's own worked example: the
    vulnerability IS the missing [Authorize] attribute, so the diff has
    no authorization-related token at all. This test exercises the DEEP
    floor computation directly -- Batch 0's validator (not yet built)
    will use this same floor to REJECT a manifest that declares only
    file-security for this shape."""

    def test_authorization_and_file_security_both_in_the_floor(self):
        # An HTTP-facing, filesystem-touching endpoint, with no positive
        # confirmation of trusted-only invocation or no-restricted-object.
        facts = {
            "no_api_or_outbound_call_surface": Fact(False, "HIGH", "CODE_EVIDENCE"),
        }
        result = compute_deep_domains(facts)
        self.assertIn("authorization", result.domains)
        self.assertIn("file-security", result.domains)


class ScopeCoverageLiveConsistencyTests(unittest.TestCase):
    """criterion 7a/7c: this module's rule-table item labels must match
    each play's live '## Scope' section exactly, symmetrically."""

    def test_no_drift_against_current_plays(self):
        results = scope_coverage.check_all()
        problems = {d: r for d, r in results.items() if not r.ok}
        self.assertEqual(problems, {}, scope_coverage.format_report(results))

    def test_total_item_count_is_42(self):
        results = scope_coverage.check_all()
        total = sum(len(r.live_items) for r in results.values())
        self.assertEqual(total, 42)


class ScopeCoverageMutationTests(unittest.TestCase):
    """The four mutation/negative checks required alongside the normal
    PASS case -- run against a synthetic in-memory play file, never
    against this repository's real plays (which must be restored to
    exactly their original state after any real-file mutation test;
    doing this in-memory instead sidesteps that risk entirely for these
    three)."""

    def _write_play(self, tmp_path, items):
        content = "# Play: Synthetic\n\n## Scope\n\n```text\n" + "\n".join(items) + "\n```\n"
        tmp_path.write_text(content, encoding="utf-8")

    def test_extra_scope_item_with_no_rule_fails(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            play = Path(d) / "synthetic.md"
            items = list(domains.group3_scope_items("web-security")) + ["A Brand New Item"]
            self._write_play(play, items)
            live = scope_coverage.parse_scope_items(play)
            implemented = set(domains.group3_scope_items("web-security"))
            missing = set(live) - implemented
            self.assertEqual(missing, {"A Brand New Item"})

    def test_removed_scope_item_still_in_rule_table_fails(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            play = Path(d) / "synthetic.md"
            items = list(domains.group3_scope_items("web-security"))[:-1]  # drop the last item
            self._write_play(play, items)
            live = scope_coverage.parse_scope_items(play)
            implemented = set(domains.group3_scope_items("web-security"))
            stale = implemented - set(live)
            self.assertEqual(len(stale), 1)

    def test_typo_d_item_text_is_detected_as_both_missing_and_stale(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            play = Path(d) / "synthetic.md"
            items = list(domains.group3_scope_items("web-security"))
            items[0] = items[0] + " (typo'd)"
            self._write_play(play, items)
            live = set(scope_coverage.parse_scope_items(play))
            implemented = set(domains.group3_scope_items("web-security"))
            self.assertTrue(live - implemented)
            self.assertTrue(implemented - live)

    def test_missing_scope_heading_raises_parse_error(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            play = Path(d) / "synthetic.md"
            play.write_text("# Play: no scope section here\n", encoding="utf-8")
            with self.assertRaises(scope_coverage.ScopeParseError):
                scope_coverage.parse_scope_items(play)


# ---------------------------------------------------------------------------
# Per-item isolation tests (criterion 7b/7d)
# ---------------------------------------------------------------------------
#
# For each domain, a "fully ruled out" base fact set (every item in that
# domain positively ruled out) and a per-item override that restores
# exactly one item's applicability. Two assertions per item: (1) the
# base alone excludes the domain; (2) overriding ONLY this item's
# fact(s) brings the domain back -- proving this specific item, and no
# other, is what the domain's presence depends on in that fixture. Items
# that share a single underlying fact (XSS/CSP weaknesses;
# postMessage/DOM operations) are isolated together as a pair, since the
# design's own worked examples never split them into separately
# triggerable facts -- both are documented explicitly below rather than
# silently tested one at a time as if they were independent.

_WEB_BASE = {
    "no_html_or_script_ever_rendered": high(),
    "never_uses_cookie_or_ambient_auth_for_state_change": high(),
    "no_browser_page_produced": high(),
    "no_browser_side_script_shipped": high(),
    "no_user_influenced_redirect_issued": high(),
    "no_cors_headers_or_cross_origin_registration": high(),
}

_API_BASE = {
    "no_api_or_outbound_call_surface": high(),
    "no_raw_http_request_framing": high(),
    "no_deserialization_or_xml_parsing": high(),
}

_DATA_BASE = {
    "no_cryptographic_operations": high(),
    "no_sensitive_data_flagged": high(),
    "no_security_relevant_random_generation": high(),
    "no_outbound_tls_connections": high(),
}

_FILE_BASE = {
    "no_attacker_influenced_paths_or_content": high(),
    "temp_files_none_or_path_unpredictable": high(),
    "temp_files_none_or_private_and_cleaned_up": high(),
    "storage_location_not_attacker_influenced": high(),
    "no_archive_extraction_or_creation": high(),
    # file-security's own disclosed-limitation fact must be pinned
    # confirmed-trusted here, or every "fully ruled out" base below
    # would be overridden back in regardless of the per-item facts.
    "externally_invoked_trusted_input_only": high(),
}

# [FIXED, per independent review Major]: each entry is (domain, base,
# override_fact_keys, expect_items) -- this is the ONLY authored list
# of which items each fact isolates; both the isolation assertions
# AND the coverage-completeness check below iterate this SAME table,
# rather than comparing two independently hand-typed lists that could
# silently drift apart from each other (the previous version's own
# defect: a hand-typed `_COVERED_ITEMS` registry was compared against
# `domains.py`'s rule-table KEYS, which proved the two lists of ITEM
# NAMES agreed, but never actually asserted that overriding a group's
# shared fact flips every item in that group individually -- a mutation
# hardcoding one item's status (e.g. always "ruled out" regardless of
# the fact) or silently reattaching an item to the wrong fact both
# passed all 74 tests undetected). The generic loop below asserts,
# for every item in the domain, not just the ones in `expect_items`:
# ruled_out == True in the base, and == (item in expect_items) after
# the override -- so a hardcoded-constant item or a
# reattached-to-the-wrong-fact item is caught either as "expected to
# flip but didn't" or "not expected to flip but did", in both
# directions.
_ISOLATION_CASES = [
    ("web-security", _WEB_BASE, {"no_html_or_script_ever_rendered"},
     {"XSS (reflected, stored, DOM-based)", "CSP weaknesses"}),
    ("web-security", _WEB_BASE, {"never_uses_cookie_or_ambient_auth_for_state_change"}, {"CSRF"}),
    ("web-security", _WEB_BASE, {"no_browser_page_produced"}, {"Clickjacking"}),
    ("web-security", _WEB_BASE, {"no_browser_side_script_shipped"},
     {"Unsafe postMessage", "Unsafe DOM operations"}),
    ("web-security", _WEB_BASE, {"no_user_influenced_redirect_issued"}, {"Open redirect"}),
    ("web-security", _WEB_BASE, {"no_cors_headers_or_cross_origin_registration"}, {"CORS misconfiguration"}),
    ("api-security", _API_BASE, {"no_api_or_outbound_call_surface"}, {
        "Authentication", "Object authorization", "Function authorization",
        "Rate limits", "Resource consumption", "Mass assignment",
        "Sensitive fields", "Pagination / filtering",
        "External APIs / webhooks", "Error handling", "Versioning", "SSRF",
    }),
    ("api-security", _API_BASE, {"no_deserialization_or_xml_parsing"}, {"Insecure deserialization", "XXE"}),
    # [REGRESSION] must NOT also expose an API surface -- keeps
    # no_api_or_outbound_call_surface True while isolating only the raw
    # HTTP-framing fact, per criterion 7d's corrected wording.
    ("api-security", _API_BASE, {"no_raw_http_request_framing"}, {"Request smuggling indicators"}),
    ("data-security", _DATA_BASE, {"no_cryptographic_operations"}, {
        "Hardcoded encryption keys", "Weak algorithms", "Static IV", "Nonce reuse", "Improper password hashing",
    }),
    # [REGRESSION, per re-adjudicating a disclosed Minor during Batch 0's
    # tests/validation/ re-execution]: the OTHER half of the same
    # compound -- context-manifest-schema.md's own Case 1 premise states
    # fact (e) as "no cryptographic operations AND handles no data the
    # baseline's 'Sensitive data' fact would flag". A target with
    # genuinely sensitive data but zero crypto footprint must NOT have
    # these five items ruled out just because no_cryptographic_operations
    # alone is true -- this is exactly the shape where "sensitive data
    # with no encryption at all" is itself often the actual finding.
    ("data-security", _DATA_BASE, {"no_sensitive_data_flagged"}, {
        "Hardcoded encryption keys", "Weak algorithms", "Static IV", "Nonce reuse", "Improper password hashing",
    }),
    # [REGRESSION] must NOT be coverable by "no_cryptographic_operations"
    # alone -- a non-CSPRNG source is itself evidence this item applies.
    ("data-security", _DATA_BASE, {"no_security_relevant_random_generation"}, {"Insecure random generation"}),
    ("data-security", _DATA_BASE, {"no_outbound_tls_connections"}, {"Certificate validation bypass"}),
    ("file-security", _FILE_BASE, {"no_attacker_influenced_paths_or_content"}, {
        "Uploads", "Downloads", "File deletion", "Directory traversal",
        "Filename generation", "Extension validation", "MIME validation", "Static serving",
    }),
    ("file-security", _FILE_BASE, {"no_archive_extraction_or_creation"}, {"ZIP extraction", "Archive creation"}),
    ("file-security", _FILE_BASE, {"storage_location_not_attacker_influenced"}, {"Storage location"}),
    # [REGRESSION] "Temporary files" is ruled out only when BOTH
    # sub-conditions hold (path unpredictability AND safe
    # location/cleanup) -- per an independent review finding, an
    # earlier version of this test suite only ever removed the
    # cleanup fact, never the path-unpredictability one, so a mutation
    # hardcoding path-unpredictability's own contribution to always
    # "ruled out" would have gone undetected. Both facts now get their
    # own isolation case against the same "Temporary files" item.
    ("file-security", _FILE_BASE, {"temp_files_none_or_private_and_cleaned_up"}, {"Temporary files"}),
    ("file-security", _FILE_BASE, {"temp_files_none_or_path_unpredictable"}, {"Temporary files"}),
]


class Group3IsolationTests(unittest.TestCase):
    def test_isolation_cases(self):
        for domain, base, override, expect_items in _ISOLATION_CASES:
            with self.subTest(domain=domain, override=sorted(override)):
                base_status = compute_deep_domains(base).group3_item_status[domain]
                for item, ruled_out in base_status.items():
                    self.assertTrue(ruled_out, f"{domain}/{item} is not ruled out in the base fixture")

                overridden = dict(base)
                for key in override:
                    overridden.pop(key, None)
                result = compute_deep_domains(overridden)
                status = result.group3_item_status[domain]
                for item, ruled_out in status.items():
                    if item in expect_items:
                        self.assertFalse(
                            ruled_out,
                            f"{domain}/{item} is still ruled out after isolating {sorted(override)} "
                            "-- this item is not actually wired to the fact(s) this case removes",
                        )
                    else:
                        self.assertTrue(
                            ruled_out,
                            f"{domain}/{item} unexpectedly stopped being ruled out when isolating "
                            f"{sorted(override)} for {sorted(expect_items)} -- fixture is not isolated, "
                            "or this item is wrongly wired to one of the removed fact(s)",
                        )
                self.assertIn(domain, result.domains)


class CoverageCompletenessTests(unittest.TestCase):
    """Every item the four Group 3 plays' live Scope sections currently
    list must appear in `_ISOLATION_CASES`' `expect_items` union --
    derived from that single authored table, not compared against a
    second, independently hand-typed registry (see that table's own
    comment for why the previous two-list version missed real defects
    despite "passing")."""

    def test_every_scope_item_has_an_isolation_case(self):
        covered_by_domain: dict = {}
        for domain, _base, _override, expect_items in _ISOLATION_CASES:
            covered_by_domain.setdefault(domain, set()).update(expect_items)
        for domain in domains.GROUP_3:
            implemented = set(domains.group3_scope_items(domain))
            covered = covered_by_domain.get(domain, set())
            self.assertEqual(
                implemented, covered,
                f"{domain}: live/implemented Scope items and _ISOLATION_CASES' covered items have drifted apart",
            )


class NonDiscriminatingFixtureDemonstrationTests(unittest.TestCase):
    """Demonstrates WHY the isolation requirement (criterion 7b, per a
    tenth-round independent review Major) is necessary: a "kitchen
    sink" fixture where two items of the same domain are both
    simultaneously applicable would satisfy a naive, non-isolating
    check for EITHER item even though it proves nothing about either one
    specifically."""

    def test_kitchen_sink_fixture_is_not_discriminating_for_either_item(self):
        kitchen_sink = dict(_API_BASE)
        del kitchen_sink["no_api_or_outbound_call_surface"]  # Authentication et al. apply
        del kitchen_sink["no_raw_http_request_framing"]  # Request smuggling also applies
        result = compute_deep_domains(kitchen_sink)
        self.assertIn("api-security", result.domains)
        # A check that only asked "is api-security in domains" after
        # this fixture would pass for a claimed "Request smuggling"
        # case AND a claimed "Authentication" case alike -- proving
        # nothing about either specifically. This is exactly the
        # failure mode criterion 7b's isolation requirement (removing
        # ONLY the mapped item's evidence must remove the domain) rules
        # out: our actual per-item tests above never leave a second
        # ruling-out fact un-set at the same time, unlike this fixture.
        status = result.group3_item_status["api-security"]
        self.assertFalse(status["Request smuggling indicators"])
        self.assertFalse(status["Authentication"])


class BaselineFreshnessGatingTests(unittest.TestCase):
    """[FIXED, per a round-5 independent review Major]: `compute_deep_domains`
    depends on baseline facts existing and being fresh
    (context-manifest-schema.md section 3a's "No baseline, or a stale
    one" note). `fact_from_baseline_entry` closes one specific way this
    could go wrong: a `status: "STALE"` baseline fact
    (templates/project-security-baseline.md's schema), if converted
    THROUGH this function, can no longer be read as a HIGH-confidence
    positive exclusion. `[DISCLOSED, per a round-7 independent review
    Minor: this docstring previously implied the underlying freshness
    requirement itself was now enforced -- it is not. This function
    covers converting a raw baseline entry; it cannot see or prevent a
    caller hand-building a Fact instead, or a fact derived through
    further reasoning inheriting stale evidence. See
    skills/security-review/SKILL.md step 1's DEEP branch for the full,
    honest scope.]` Six cases below test exactly what this function
    itself does, not the broader requirement."""

    def test_1_missing_status_is_current_and_still_positive(self):
        entry = {"value": True, "confidence": "HIGH", "source": "CODE_EVIDENCE"}
        fact = fact_from_baseline_entry(entry)
        self.assertEqual(fact, Fact(True, "HIGH", "CODE_EVIDENCE"))
        self.assertTrue(fact.is_positive())

    def test_2_stale_becomes_unknown_and_does_not_exclude_domain(self):
        entry = {"value": True, "confidence": "HIGH", "source": "CODE_EVIDENCE", "status": "STALE"}
        fact = fact_from_baseline_entry(entry)
        self.assertEqual(fact, domains.UNKNOWN_FACT)
        facts = {"no_credential_anywhere_in_scope": fact}
        self.assertIn("secrets-security", compute_deep_domains(facts).domains)

    def test_3_stale_with_still_high_confidence_evidence_present_is_not_positive(self):
        # [CORRECTED, per a round-6 independent review Nit: the removed
        # comment claimed a future refactor that checks value/confidence
        # before `status` "would pass test 2" -- empirically false, a
        # monkeypatched version doing exactly that fails test 2 as well
        # (this exact input, fed through compute_deep_domains, no longer
        # keeps secrets-security in). This test's actual purpose is
        # narrower and still real: it asserts directly against
        # is_positive() rather than through compute_deep_domains, so it
        # fails even in a hypothetical future where every OTHER domain's
        # own facts happened to keep the affected domain in for
        # unrelated reasons -- a scenario test 2 alone could not
        # distinguish from a genuine fix.
        entry = {"value": True, "confidence": "HIGH", "source": "CODE_EVIDENCE", "status": "STALE"}
        self.assertFalse(fact_from_baseline_entry(entry).is_positive())

    def test_4_unrecognized_status_fails_closed_not_treated_as_current(self):
        entry = {"value": True, "confidence": "HIGH", "source": "CODE_EVIDENCE", "status": "PENDING_REVIEW"}
        with self.assertRaises(ValueError):
            fact_from_baseline_entry(entry)

    def test_5_malformed_or_missing_fields_are_never_positive(self):
        for entry in ({}, {"value": True}, {"value": True, "confidence": "HIGH"}, None):
            with self.subTest(entry=entry):
                self.assertFalse(fact_from_baseline_entry(entry).is_positive())

    def test_6_stale_group2_and_group3_each_kept_applicable(self):
        # Group 2: secrets-security's sole exclusion condition, stale.
        stale_secret_fact = fact_from_baseline_entry(
            {"value": True, "confidence": "HIGH", "source": "CODE_EVIDENCE", "status": "STALE"}
        )
        self.assertIn(
            "secrets-security",
            compute_deep_domains({"no_credential_anywhere_in_scope": stale_secret_fact}).domains,
        )
        # Group 3: data-security's compound crypto/sensitive-data
        # condition, both halves stale. [CORRECTED, per a round-6
        # independent review Minor: the original version left
        # data-security's other two items (Insecure random generation,
        # Certificate validation bypass) UNKNOWN too, so it stayed
        # applicable regardless of whether the gate worked at all --
        # not discriminating for the gate specifically. Those two are
        # now set to fresh, genuinely-positive facts, so the STALE pair
        # is the only thing keeping data-security applicable; verified
        # this is discriminating: substituting the raw (un-gated) stale
        # values here flips the result to data-security EXCLUDED.]
        stale_crypto_fact = fact_from_baseline_entry(
            {"value": True, "confidence": "HIGH", "source": "CODE_EVIDENCE", "status": "STALE"}
        )
        stale_sensitive_data_fact = fact_from_baseline_entry(
            {"value": True, "confidence": "HIGH", "source": "CODE_EVIDENCE", "status": "STALE"}
        )
        other_data_items_fresh = high()
        self.assertIn(
            "data-security",
            compute_deep_domains(
                {
                    "no_cryptographic_operations": stale_crypto_fact,
                    "no_sensitive_data_flagged": stale_sensitive_data_fact,
                    "no_security_relevant_random_generation": other_data_items_fresh,
                    "no_outbound_tls_connections": other_data_items_fresh,
                }
            ).domains,
        )


if __name__ == "__main__":
    unittest.main()
