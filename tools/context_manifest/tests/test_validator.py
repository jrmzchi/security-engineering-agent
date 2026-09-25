"""Tests for validator.py + producer.py.

Covers implementation-batches.md Batch 0 acceptance criteria 2, 3, 5,
and (via the validator, not just domains.py directly) 6 -- the DEEP
Case 1/1b/2/3 worked examples resolving correctly through the FULL
manifest-validity path, not only the underlying domain-applicability
function.
"""

from __future__ import annotations

import unittest

from .. import producer, schema
from ..domains import Fact
from ..validator import Classification, ValidationResult, attach_validity, validate_manifest


def high(value=True, source="CODE_EVIDENCE") -> Fact:
    return Fact(value=value, confidence="HIGH", source=source)


class SixFixedCaseManifestsPassByConstruction(unittest.TestCase):
    """implementation-batches.md Batch 0 acceptance criterion 2: the
    manifest validity check, run against the built-in layer's own
    output, always passes (it IS the floor) -- demonstrated on the six
    fixed-case shapes used throughout V3/V3 Slim."""

    def _assert_passes(self, manifest):
        floor = Classification(
            sensitivity=manifest["sensitivity"] if manifest["reviewMode"] == "TARGETED" else None,
            implicated_domains=frozenset(manifest["domains"]),
        )
        result = validate_manifest(manifest, floor=floor)
        self.assertTrue(result.passed, result.failed_checks)
        return result

    def test_css_color_change(self):
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            target_change_files=["styles/main.css"],
            classification=Classification(sensitivity="NONE", implicated_domains=frozenset()),
        )
        self.assertEqual(manifest["domains"], [])
        self._assert_passes(manifest)

    def test_authorize_removal(self):
        # The canonical file-download-without-[Authorize] shape --
        # domains include BOTH file-security and authorization, per
        # criterion 5's own corrected-version-passes half.
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            target_change_files=["Controllers/ReportsController.cs"],
            classification=Classification(
                sensitivity="HIGH", implicated_domains=frozenset({"authorization", "file-security"})
            ),
        )
        self._assert_passes(manifest)

    def test_authenticated_file_download(self):
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            target_change_files=["Controllers/DownloadController.cs"],
            classification=Classification(
                sensitivity="HIGH", implicated_domains=frozenset({"authorization", "file-security"})
            ),
        )
        self._assert_passes(manifest)

    def test_ef_core_query(self):
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            target_change_files=["Repositories/UserRepository.cs"],
            classification=Classification(sensitivity="MODERATE", implicated_domains=frozenset({"code-review"})),
        )
        self._assert_passes(manifest)

    def test_new_dependency(self):
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            target_change_files=["package.json"],
            classification=Classification(
                sensitivity="MODERATE", implicated_domains=frozenset({"dependency-security"})
            ),
        )
        self._assert_passes(manifest)

    def test_auth_middleware_rewrite(self):
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            target_change_files=["Startup.cs"],
            classification=Classification(sensitivity="HIGH", implicated_domains=frozenset({"authentication"})),
        )
        result = self._assert_passes(manifest)
        # Case 5's own Factors-driven AUDIT movement is a judgment call
        # this module does not make -- confirm the *default* (no
        # factor_adjustment) ELEVATED value is itself legal, which is
        # the part this module owns.
        self.assertEqual(manifest["reviewBudget"], "ELEVATED")
        self.assertTrue(result.passed)


class DegradationPathTest(unittest.TestCase):
    def test_no_jev_attempted_is_recorded_honestly(self):
        manifest = producer.build_manifest(
            review_mode="QUICK",
            classification=Classification(sensitivity=None, implicated_domains=frozenset()),
        )
        self.assertEqual(
            manifest["degradation"],
            {
                "jevAttempted": False,
                "jevOutcome": "no_token",
                "fallbackUsed": True,
                "fallbackReason": "no Jev token configured",
            },
        )
        floor = Classification(sensitivity=None, implicated_domains=frozenset(manifest["domains"]))
        result = validate_manifest(manifest, floor=floor)
        self.assertTrue(result.passed, result.failed_checks)


class DomainFloorNegativePositiveSet(unittest.TestCase):
    """criterion 5: the file-download-without-[Authorize] shape declaring
    only ["file-security"] is REJECTED; the corrected version including
    "authorization" PASSES; a genuinely non-security-relevant manifest
    with an empty domain list PASSES."""

    def test_file_security_only_is_rejected(self):
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            target_change_files=["Controllers/ReportsController.cs"],
            classification=Classification(sensitivity="HIGH", implicated_domains=frozenset({"file-security"})),
        )
        floor = Classification(sensitivity="HIGH", implicated_domains=frozenset({"authorization", "file-security"}))
        result = validate_manifest(manifest, floor=floor)
        self.assertFalse(result.passed)
        self.assertTrue(any("item5" in c and "authorization" in c for c in result.failed_checks), result.failed_checks)

    def test_corrected_version_with_authorization_passes(self):
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            target_change_files=["Controllers/ReportsController.cs"],
            classification=Classification(
                sensitivity="HIGH", implicated_domains=frozenset({"authorization", "file-security"})
            ),
        )
        floor = Classification(sensitivity="HIGH", implicated_domains=frozenset({"authorization", "file-security"}))
        result = validate_manifest(manifest, floor=floor)
        self.assertTrue(result.passed, result.failed_checks)

    def test_none_sensitivity_empty_domains_passes(self):
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            classification=Classification(sensitivity="NONE", implicated_domains=frozenset()),
        )
        floor = Classification(sensitivity="NONE", implicated_domains=frozenset())
        result = validate_manifest(manifest, floor=floor)
        self.assertTrue(result.passed, result.failed_checks)


class Group2CounterexamplesRejectExclusion(unittest.TestCase):
    """A manifest that excludes authentication/authorization/secrets-security
    on the "no mechanism was found" grounds (i.e. omits them from
    `domains` when the floor still requires them) is REJECTED by the
    validator -- this is the acceptance bar, distinct from domains.py's
    own direct test of the same rule."""

    def test_excluding_authentication_on_no_mechanism_found_is_rejected(self):
        floor = Classification.for_deep({})  # nothing confirmed -> all Group 2 domains in the floor
        self.assertIn("authentication", floor.implicated_domains)
        manifest = producer.build_manifest(
            review_mode="DEEP",
            baseline_facts={"invoked_only_by_trusted_or_authenticated_caller": Fact()},
        )
        # Simulate a producer that wrongly dropped authentication despite
        # the floor requiring it (e.g. a hypothetical buggy producer, or
        # Jev's future output in Batch 2) -- the validator must catch this
        # regardless of who produced the manifest.
        wrong = dict(manifest)
        wrong["domains"] = sorted(set(manifest["domains"]) - {"authentication"})
        result = validate_manifest(wrong, floor=floor)
        self.assertFalse(result.passed)
        self.assertTrue(any("authentication" in c for c in result.failed_checks), result.failed_checks)

    def test_excluding_authorization_is_rejected(self):
        floor = Classification.for_deep({})
        manifest = producer.build_manifest(review_mode="DEEP", baseline_facts={})
        wrong = dict(manifest)
        wrong["domains"] = sorted(set(manifest["domains"]) - {"authorization"})
        result = validate_manifest(wrong, floor=floor)
        self.assertFalse(result.passed)

    def test_excluding_secrets_security_is_rejected(self):
        floor = Classification.for_deep({})
        manifest = producer.build_manifest(review_mode="DEEP", baseline_facts={})
        wrong = dict(manifest)
        wrong["domains"] = sorted(set(manifest["domains"]) - {"secrets-security"})
        result = validate_manifest(wrong, floor=floor)
        self.assertFalse(result.passed)


class DeepCasesThroughFullValidationPath(unittest.TestCase):
    """The same Case 1/1b/2/3 premises as tools/context_manifest/tests/
    test_domains.py, but exercised end to end: build_manifest() ->
    validate_manifest() -> attach_validity(), proving the full pipeline
    (not just compute_deep_domains() in isolation) resolves correctly."""

    def _build_and_validate(self, baseline_facts):
        manifest = producer.build_manifest(review_mode="DEEP", baseline_facts=baseline_facts)
        floor = Classification.for_deep(baseline_facts)
        result = validate_manifest(manifest, floor=floor)
        final = attach_validity(manifest, result)
        return final, result

    def test_case_1_passes_with_3_domains(self):
        facts = {
            "invoked_only_by_trusted_or_authenticated_caller": high(),
            "externally_invoked_trusted_input_only": high(),
            "no_identity_distinction_code": high(),
            "no_restricted_object_or_operation": high(),
            "no_credential_anywhere_in_scope": high(),
            "no_cryptographic_operations": high(),
            "no_sensitive_data_flagged": high(),
            "no_security_relevant_random_generation": high(),
            "no_outbound_tls_connections": high(),
            "no_deserialization_or_xml_parsing": high(),
            "no_attacker_influenced_paths_or_content": high(),
            "temp_files_none_or_path_unpredictable": high(),
            "temp_files_none_or_private_and_cleaned_up": high(),
            "storage_location_not_attacker_influenced": high(),
            "no_archive_extraction_or_creation": high(),
            "no_html_or_script_ever_rendered": high(),
            "never_uses_cookie_or_ambient_auth_for_state_change": high(),
            "no_browser_page_produced": high(),
            "no_browser_side_script_shipped": high(),
            "no_user_influenced_redirect_issued": high(),
            "no_cors_headers_or_cross_origin_registration": high(),
            "no_api_or_outbound_call_surface": high(),
            "no_raw_http_request_framing": high(),
        }
        final, result = self._build_and_validate(facts)
        self.assertTrue(result.passed, result.failed_checks)
        self.assertEqual(len(final["domains"]), 3)
        self.assertTrue(final["validity"]["passed"])
        self.assertEqual(final["validity"]["checkedBy"], "deterministic_validator")

    def test_case_1b_passes_with_6_domains(self):
        facts = {
            "no_identity_distinction_code": high(),
            "no_restricted_object_or_operation": high(),
            "no_credential_anywhere_in_scope": high(),
            "no_cryptographic_operations": high(),
            "no_sensitive_data_flagged": high(),
            "no_security_relevant_random_generation": high(),
            "no_outbound_tls_connections": high(),
            "no_deserialization_or_xml_parsing": high(),
            "no_attacker_influenced_paths_or_content": high(),
            "temp_files_none_or_path_unpredictable": high(),
            "temp_files_none_or_private_and_cleaned_up": high(),
            "storage_location_not_attacker_influenced": high(),
            "no_archive_extraction_or_creation": high(),
            "no_html_or_script_ever_rendered": high(),
            "never_uses_cookie_or_ambient_auth_for_state_change": high(),
            "no_browser_page_produced": high(),
            "no_browser_side_script_shipped": high(),
            "no_user_influenced_redirect_issued": high(),
            "no_cors_headers_or_cross_origin_registration": high(),
            "no_api_or_outbound_call_surface": high(),
            "no_raw_http_request_framing": high(),
        }
        final, result = self._build_and_validate(facts)
        self.assertTrue(result.passed, result.failed_checks)
        self.assertEqual(len(final["domains"]), 6)

    def test_case_2_passes_with_9_domains(self):
        facts = {
            "no_html_or_script_ever_rendered": high(),
            "never_uses_cookie_or_ambient_auth_for_state_change": high(),
            "no_browser_page_produced": high(),
            "no_browser_side_script_shipped": high(),
            "no_user_influenced_redirect_issued": high(),
            "no_cors_headers_or_cross_origin_registration": high(),
        }
        final, result = self._build_and_validate(facts)
        self.assertTrue(result.passed, result.failed_checks)
        self.assertEqual(len(final["domains"]), 9)
        self.assertNotIn("web-security", final["domains"])

    def test_case_3_passes_with_all_10_domains(self):
        final, result = self._build_and_validate({})
        self.assertTrue(result.passed, result.failed_checks)
        self.assertEqual(len(final["domains"]), 10)


class SchemaAndEnumFailures(unittest.TestCase):
    def _minimal_manifest(self, **overrides):
        m = {
            "manifestVersion": "1.0",
            "producedBy": "built_in",
            "targetChange": {"files": []},
            "reviewMode": "TARGETED",
            "sensitivity": "NONE",
            "domains": [],
            "reviewBudget": "MINIMAL",
            "scannersSelected": [],
            "scannersSkipped": [],
            "coverageGaps": [],
            "degradation": schema.new_degradation_no_jev_attempted(),
        }
        m.update(overrides)
        return m

    def test_missing_required_field_fails_item1(self):
        m = self._minimal_manifest()
        del m["reviewBudget"]
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item1" in c for c in result.failed_checks))

    def test_none_manifest_fails_cleanly_instead_of_raising(self):
        result = validate_manifest(None, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)

    def test_scanners_skipped_as_list_of_strings_fails_item1_not_typeerror(self):
        """[FIXED, per independent review Major]: `["gitleaks"]` instead
        of `[{"tool": "gitleaks", "reason": "..."}]` used to raise an
        uncaught TypeError out of item 6 -- must fail item1 instead."""
        m = self._minimal_manifest(scannersSkipped=["gitleaks"])
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item1" in c for c in result.failed_checks), result.failed_checks)

    def test_degradation_as_none_fails_item1_not_typeerror(self):
        m = self._minimal_manifest(degradation=None)
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item1" in c for c in result.failed_checks), result.failed_checks)

    def test_target_change_as_none_fails_item1_not_typeerror(self):
        m = self._minimal_manifest(targetChange=None)
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item1" in c for c in result.failed_checks), result.failed_checks)

    def test_domains_containing_a_dict_fails_item1(self):
        m = self._minimal_manifest(domains=[{"not": "a string"}])
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item1" in c for c in result.failed_checks), result.failed_checks)

    def test_fallback_used_as_string_fails_item1_not_silently_accepted(self):
        """[FIXED, per independent review Major]: `fallbackUsed: "false"`
        (a truthy non-empty string) used to be silently accepted by
        item 8's own boolean-ish check."""
        m = self._minimal_manifest(
            degradation={
                "jevAttempted": False,
                "jevOutcome": "timeout",
                "fallbackUsed": "false",
                "fallbackReason": None,
            }
        )
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item1" in c for c in result.failed_checks), result.failed_checks)

    def test_target_change_files_as_string_fails_item1(self):
        m = self._minimal_manifest(targetChange={"files": "a.py"})
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item1" in c for c in result.failed_checks), result.failed_checks)

    def test_malformed_factors_evidence_fails_item1(self):
        """[FIXED, per a round-2 independent review Minor]: [""], [None],
        True, and a dict used to all pass silently in this field."""
        for bad_value in ([""], [None], True, {"a": 1}, "x"):
            with self.subTest(bad_value=bad_value):
                m = self._minimal_manifest(
                    sensitivity="HIGH", reviewBudget="FOCUSED", factorsEvidence=bad_value
                )
                result = validate_manifest(
                    m, floor=Classification(sensitivity="HIGH", implicated_domains=frozenset())
                )
                self.assertFalse(result.passed)
                self.assertTrue(any("item1" in c for c in result.failed_checks), result.failed_checks)

    def test_unrecognized_manifest_version_fails_item2(self):
        m = self._minimal_manifest(manifestVersion="99.0")
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item2" in c for c in result.failed_checks), result.failed_checks)

    def test_no_token_with_jev_attempted_true_fails_item8(self):
        """[FIXED, per independent review Minor]: `jevAttempted: true`
        with `jevOutcome: "no_token"` used to pass -- "no token" means
        no call was ever made, so jevAttempted must be false."""
        m = self._minimal_manifest(
            degradation={"jevAttempted": True, "jevOutcome": "no_token", "fallbackUsed": True, "fallbackReason": "x"}
        )
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item8" in c for c in result.failed_checks), result.failed_checks)

    def test_success_with_jev_attempted_false_fails_item8(self):
        m = self._minimal_manifest(
            producedBy="jev",
            degradation={"jevAttempted": False, "jevOutcome": "success", "fallbackUsed": False, "fallbackReason": None},
        )
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item8" in c for c in result.failed_checks), result.failed_checks)

    def test_targeted_with_no_floor_sensitivity_fails_item3_not_silently_skipped(self):
        """[FIXED, per independent review Minor]: TARGETED with
        floor.sensitivity=None used to silently skip item 3 entirely
        (fail open) instead of failing closed."""
        m = self._minimal_manifest()
        result = validate_manifest(m, floor=Classification(sensitivity=None, implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item3" in c for c in result.failed_checks), result.failed_checks)

    def test_invalid_enum_fails_item2(self):
        m = self._minimal_manifest(reviewBudget="SUPER_AUDIT")
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item2" in c for c in result.failed_checks))

    def test_targeted_with_na_sensitivity_fails_item2a(self):
        m = self._minimal_manifest(sensitivity="N/A")
        result = validate_manifest(m, floor=Classification(sensitivity=None, implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item2a" in c for c in result.failed_checks))

    def test_quick_with_non_na_sensitivity_fails_item2a(self):
        m = self._minimal_manifest(reviewMode="QUICK", sensitivity="HIGH", reviewBudget="FOCUSED")
        result = validate_manifest(m, floor=Classification(sensitivity=None, implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item2a" in c for c in result.failed_checks))

    def test_budget_below_floor_fails_item7(self):
        m = self._minimal_manifest(sensitivity="HIGH", reviewBudget="MINIMAL")
        result = validate_manifest(m, floor=Classification(sensitivity="HIGH", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item7" in c for c in result.failed_checks))

    def test_movement_with_no_factors_evidence_fails_item7(self):
        """[FIXED, per independent review Major]: TARGETED/HIGH declaring
        FOCUSED (one level below the ELEVATED starting point, legal per
        the movement cap) used to pass with zero recorded Factors
        evidence -- plays/review-budget.md's own "if the Factors
        genuinely support it" condition on movement was unenforced."""
        m = self._minimal_manifest(sensitivity="HIGH", reviewBudget="FOCUSED")
        result = validate_manifest(m, floor=Classification(sensitivity="HIGH", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item7" in c for c in result.failed_checks), result.failed_checks)

    def test_movement_with_factors_evidence_passes_item7(self):
        m = self._minimal_manifest(
            sensitivity="HIGH", reviewBudget="FOCUSED",
            factorsEvidence=["internal-only admin tool", "strong baseline confidence"],
        )
        result = validate_manifest(m, floor=Classification(sensitivity="HIGH", implicated_domains=frozenset()))
        self.assertTrue(result.passed, result.failed_checks)

    def test_upward_movement_with_no_evidence_passes_item7(self):
        """[FIXED, per a round-2 independent review Minor]: TARGETED/
        MODERATE declaring ELEVATED (one level UP from the FOCUSED
        starting point, more scrutiny) must not require evidence --
        only downward movement does."""
        m = self._minimal_manifest(sensitivity="MODERATE", reviewBudget="ELEVATED")
        result = validate_manifest(m, floor=Classification(sensitivity="MODERATE", implicated_domains=frozenset()))
        self.assertTrue(result.passed, result.failed_checks)

    def test_explicit_deep_minimal_with_no_evidence_fails_item7(self):
        """[FIXED, per independent review Major]: an explicit DEEP
        request declaring MINIMAL (uncapped, so legal per the movement
        range alone) used to pass with zero evidence."""
        m = self._minimal_manifest(reviewMode="DEEP", sensitivity="N/A", reviewBudget="MINIMAL")
        result = validate_manifest(m, floor=Classification(sensitivity=None, implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item7" in c for c in result.failed_checks), result.failed_checks)

    def test_producer_requires_evidence_when_moving_down(self):
        with self.assertRaises(ValueError):
            producer.build_manifest(
                review_mode="TARGETED",
                classification=Classification(sensitivity="HIGH", implicated_domains=frozenset()),
                factor_adjustment=-1,
            )

    def test_producer_does_not_require_evidence_when_moving_up(self):
        """[FIXED, per a round-2 independent review Minor]: moving the
        budget UP (more scrutiny) from its starting point never needs
        Factors evidence, matching validator.py item 7's "not below"
        framing -- only downward movement does."""
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            classification=Classification(sensitivity="HIGH", implicated_domains=frozenset({"authentication"})),
            factor_adjustment=1,
        )
        self.assertEqual(manifest["reviewBudget"], "AUDIT")
        floor = Classification(sensitivity="HIGH", implicated_domains=frozenset({"authentication"}))
        result = validate_manifest(manifest, floor=floor)
        self.assertTrue(result.passed, result.failed_checks)

    def test_producer_rejects_bare_string_factors_evidence(self):
        with self.assertRaises(TypeError):
            producer.build_manifest(
                review_mode="TARGETED",
                classification=Classification(sensitivity="HIGH", implicated_domains=frozenset()),
                factor_adjustment=-1,
                factors_evidence="internal tool",
            )

    def test_producer_records_factors_evidence_and_passes_validation(self):
        manifest = producer.build_manifest(
            review_mode="TARGETED",
            classification=Classification(sensitivity="HIGH", implicated_domains=frozenset({"authentication"})),
            factor_adjustment=1,
            factors_evidence=["shared authentication middleware (attack-surface centrality)"],
        )
        self.assertEqual(manifest["reviewBudget"], "AUDIT")
        self.assertEqual(manifest["factorsEvidence"], ["shared authentication middleware (attack-surface centrality)"])
        floor = Classification(sensitivity="HIGH", implicated_domains=frozenset({"authentication"}))
        result = validate_manifest(manifest, floor=floor)
        self.assertTrue(result.passed, result.failed_checks)

    def test_degradation_inconsistency_fails_item8(self):
        m = self._minimal_manifest(
            degradation={"jevAttempted": True, "jevOutcome": "timeout", "fallbackUsed": False, "fallbackReason": None}
        )
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item8" in c for c in result.failed_checks))

    def test_producedby_jev_with_fallback_fails_item8(self):
        m = self._minimal_manifest(
            producedBy="jev",
            degradation={"jevAttempted": True, "jevOutcome": "below_floor", "fallbackUsed": True, "fallbackReason": "x"},
        )
        result = validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertFalse(result.passed)
        self.assertTrue(any("item8" in c for c in result.failed_checks))

    def test_scanner_domain_inconsistency_fails_item6(self):
        m = self._minimal_manifest(domains=["secrets-security"])
        result = validate_manifest(
            m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset({"secrets-security"}))
        )
        self.assertFalse(result.passed)
        self.assertTrue(any("item6" in c for c in result.failed_checks))

    def test_never_partially_repairs_a_failing_manifest(self):
        """validate_manifest must never mutate its input."""
        m = self._minimal_manifest(reviewBudget="SUPER_AUDIT")
        original = dict(m)
        validate_manifest(m, floor=Classification(sensitivity="NONE", implicated_domains=frozenset()))
        self.assertEqual(m, original)


if __name__ == "__main__":
    unittest.main()
