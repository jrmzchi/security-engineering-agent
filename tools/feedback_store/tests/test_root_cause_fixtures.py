"""Four representative fixtures, one per root-cause layer -- v4-design.md
section 3.4, implementation-batches.md Batch 1 acceptance criterion 3:
"each correctly attributed to its own layer... not just 'a miss was
logged,' but logged against the CORRECT one of the four, proving the
attribution actually discriminates."

`cross_file_flow` and `reasoning` are grounded in already-documented
traps in EXISTING fixtures (`tests/fixtures/cross_file_sql_unsafe/` and
`tests/fixtures/csrf_samesite_lax_deceptive.cs`, both already named in
`tests/validation/expected-results.md`'s own "Trap being tested"
column) -- read fresh here, not assumed. `routing` and `attack_surface`
are about the classification/mapping steps THEMSELVES failing, which
have no dedicated pre-existing "this was a routing/mapping miss"
fixture in this repo to point at (those steps are agent reasoning, not
code with its own fixture suite the way finding-validation is) --
these two are DISCLOSED, minimal, representative constructed scenarios,
per explicit instruction's own "使用代表性fixture或最小新增案例"
permission, not claimed to be pre-existing V3 fixtures.
"""

from __future__ import annotations

import os
import unittest

from .. import attribution

FIXTURES_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "tests", "fixtures"))


def _read(relative_path: str) -> str:
    with open(os.path.join(FIXTURES_ROOT, *relative_path.split("/")), encoding="utf-8") as f:
        return f.read()


class RoutingMissTests(unittest.TestCase):
    """[DISCLOSED, representative constructed scenario -- no dedicated
    pre-existing fixture] a change introduces
    tests/fixtures/cross_file_object_authz_unsafe/'s missing-ownership-
    check shape, but item 0's own sensitivity/domain classification
    never selects "authorization" at all for this diff (e.g. it is
    misclassified as an ordinary database-read, one of
    plays/security-change-detection.md's own MODERATE examples,
    because the diff's surface signal alone -- a GET endpoint reading
    by ID -- resembles that category more than "authorization" without
    deeper inspection). The routing gate itself is where this fails;
    no downstream gate is even reached."""

    def test_attributed_to_routing_not_a_later_layer(self):
        rec = attribution.record_miss(
            record_id="miss-routing-1",
            routing_correct=False,
            observed_miss="missing object-ownership check in ReportRepository.FindById's call chain",
            expected_finding="CONFIRMED HIGH BOLA/IDOR",
            evidence={
                "path": "tests/fixtures/cross_file_object_authz_unsafe/ReportsController.cs",
                "observation": (
                    "item 0's own recorded domain set for this diff was {'code-review'} only -- "
                    "'authorization' was never selected, so plays/authorization.md's IDOR/BOLA "
                    "three-question trace was never even loaded for this review"
                ),
            },
            remediation=(
                "review plays/security-change-detection.md's MODERATE/HIGH lists for whether "
                "'new endpoint reading an object by caller-supplied ID' should route to "
                "authorization by default, not just when [Authorize] itself changes"
            ),
            scope="endpoints reading a caller-supplied object ID with no [Authorize]-change signal",
            human_confirmed_by="example-reviewer",
            created_at="2026-09-23T00:00:00Z",
        )
        self.assertEqual(rec["layer"], "routing")
        self.assertEqual(rec["priorLayersPassed"], [])


class AttackSurfaceMissTests(unittest.TestCase):
    """[DISCLOSED, representative constructed scenario] domain
    ("api-security") is correctly selected, but
    .security/attack-surface.json has no node for a newly-added
    outbound webhook-callback endpoint at all -- the map was simply
    never refreshed to include it, so nothing downstream had an entry
    point to trace from."""

    def test_attributed_to_attack_surface_not_flow_or_reasoning(self):
        rec = attribution.record_miss(
            record_id="miss-surface-1",
            routing_correct=True,
            attack_surface_complete=False,
            observed_miss="SSRF via a new outbound webhook-callback endpoint with no allowlist",
            expected_finding="CONFIRMED HIGH SSRF",
            evidence={
                "path": ".security/attack-surface.json",
                "observation": (
                    "no ENTRY_POINT or SERVICE node exists for this endpoint at all -- "
                    "the map predates this endpoint's addition and was not refreshed before this review"
                ),
            },
            remediation="ensure attack-surface refresh is triggered for any diff adding a new route, per plays/attack-surface-mapping.md",
            scope="new outbound-call endpoints added since the last map refresh",
            human_confirmed_by="example-reviewer",
            created_at="2026-09-23T00:00:00Z",
        )
        self.assertEqual(rec["layer"], "attack_surface")
        self.assertEqual(rec["priorLayersPassed"], ["routing"])


class CrossFileFlowMissTests(unittest.TestCase):
    """Grounded in tests/fixtures/cross_file_sql_unsafe/'s own
    documented trap (expected-results.md: "reviewer confirms from
    UserRepository.cs's sink alone, without tracing that query is
    attacker-controlled all the way from UsersController.cs"). Domain
    correctly selected (code-review); the attack surface has both the
    controller entry point and the repository sink as separate,
    already-mapped nodes; but the reviewer's own trace stopped at the
    sink without connecting the 3-hop chain plays/cross-file-data-
    flow.md requires."""

    def test_attributed_to_cross_file_flow_grounded_in_real_fixture(self):
        sink_text = _read("cross_file_sql_unsafe/UserRepository.cs")
        self.assertIn("VULNERABLE", sink_text)
        controller_text = _read("cross_file_sql_unsafe/UsersController.cs") if os.path.exists(
            os.path.join(FIXTURES_ROOT, "cross_file_sql_unsafe", "UsersController.cs")
        ) else None
        # Confirms the 3-file chain this scenario depends on actually
        # exists in the fixture directory (not assumed).
        self.assertTrue(os.path.exists(os.path.join(FIXTURES_ROOT, "cross_file_sql_unsafe", "UsersController.cs")))

        rec = attribution.record_miss(
            record_id="miss-flow-1",
            routing_correct=True,
            attack_surface_complete=True,
            cross_file_flow_connected=False,
            observed_miss="SQL injection in UserRepository.FindByNameLike, missed because the trace stopped at the sink",
            expected_finding="CONFIRMED CRITICAL/HIGH SQL injection (per expected-results.md)",
            evidence={
                "path": "tests/fixtures/cross_file_sql_unsafe/UserRepository.cs",
                "observation": (
                    "the reviewer confirmed the sink alone (string-interpolated SqlCommand) but never "
                    "traced 'query' back through UserSearchService.SearchUsers to UsersController.cs's "
                    "unvalidated request parameter, so the finding was reported as NEEDS_VERIFICATION "
                    "('reachability unconfirmed') instead of CONFIRMED"
                ),
            },
            remediation="apply plays/cross-file-data-flow.md's explicit multi-hop procedure instead of stopping at the sink file",
            scope="any candidate whose sink is reached across file boundaries",
            human_confirmed_by="example-reviewer",
            created_at="2026-09-23T00:00:00Z",
        )
        self.assertEqual(rec["layer"], "cross_file_flow")
        self.assertEqual(rec["priorLayersPassed"], ["routing", "attack_surface"])


class ReasoningMissTests(unittest.TestCase):
    """Grounded in the already-existing csrf_samesite_lax_deceptive.cs
    fixture's own documented trap (expected-results.md: "'SameSite=Lax'
    cookie config, presented as if it were sufficient -- it does not
    cover top-level GET navigation"). Domain correctly selected
    (web-security); attack surface and flow are both trivially correct
    (single-file, no cross-file hop); but the manual semantic analysis
    step itself accepted SameSite=Lax as sufficient mitigation without
    checking the top-level-GET-navigation exception
    plays/web-security.md's CSRF section requires."""

    def test_attributed_to_reasoning_grounded_in_real_fixture(self):
        text = _read("csrf_samesite_lax_deceptive.cs") if os.path.exists(
            os.path.join(FIXTURES_ROOT, "csrf_samesite_lax_deceptive.cs")
        ) else None
        exists = os.path.exists(os.path.join(FIXTURES_ROOT, "csrf_samesite_lax_deceptive.cs"))
        self.assertTrue(exists, "expected-results.md names this fixture; confirm it is actually present before grounding this case in it")
        if exists:
            self.assertIn("SameSite", text if text is not None else _read("csrf_samesite_lax_deceptive.cs"))

        rec = attribution.record_miss(
            record_id="miss-reasoning-1",
            routing_correct=True,
            attack_surface_complete=True,
            cross_file_flow_connected=True,
            reasoning_would_catch_it=False,
            observed_miss="CSRF via top-level GET navigation despite SameSite=Lax",
            expected_finding="CONFIRMED HIGH CSRF (per expected-results.md)",
            evidence={
                "path": "tests/fixtures/csrf_samesite_lax_deceptive.cs",
                "observation": (
                    "domain (web-security), single-file attack surface, and (trivial, single-hop) flow "
                    "were all correctly identified; the manual semantic analysis step accepted "
                    "SameSite=Lax as sufficient without checking plays/web-security.md's own "
                    "top-level-GET-navigation exception to that mitigation"
                ),
            },
            remediation="re-check plays/web-security.md's CSRF section's SameSite=Lax caveat explicitly during manual analysis, not just note the attribute's presence",
            scope="any SameSite=Lax cookie config presented as a CSRF mitigation",
            human_confirmed_by="example-reviewer",
            created_at="2026-09-23T00:00:00Z",
        )
        self.assertEqual(rec["layer"], "reasoning")
        self.assertEqual(rec["priorLayersPassed"], ["routing", "attack_surface", "cross_file_flow"])


class DiscriminationAcrossAllFourTests(unittest.TestCase):
    """A single assertion that all four constructed cases above
    actually landed on four DIFFERENT layers -- not just that each
    individually looks right, but that the mechanism as a whole
    discriminates between them (the acceptance criterion's actual
    concern)."""

    def test_four_fixtures_map_to_four_distinct_layers(self):
        layers = set()
        layers.add(attribution.attribute_layer(routing_correct=False)[0])
        layers.add(attribution.attribute_layer(routing_correct=True, attack_surface_complete=False)[0])
        layers.add(attribution.attribute_layer(routing_correct=True, attack_surface_complete=True, cross_file_flow_connected=False)[0])
        layers.add(attribution.attribute_layer(
            routing_correct=True, attack_surface_complete=True,
            cross_file_flow_connected=True, reasoning_would_catch_it=False,
        )[0])
        self.assertEqual(layers, {"routing", "attack_surface", "cross_file_flow", "reasoning"})


if __name__ == "__main__":
    unittest.main()
