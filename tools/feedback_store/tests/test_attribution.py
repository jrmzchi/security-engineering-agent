from __future__ import annotations

import unittest

from .. import attribution


class AttributeLayerTests(unittest.TestCase):
    def test_routing_layer(self):
        layer, prior = attribution.attribute_layer(routing_correct=False)
        self.assertEqual(layer, "routing")
        self.assertEqual(prior, [])

    def test_attack_surface_layer(self):
        layer, prior = attribution.attribute_layer(
            routing_correct=True, attack_surface_complete=False,
        )
        self.assertEqual(layer, "attack_surface")
        self.assertEqual(prior, ["routing"])

    def test_cross_file_flow_layer(self):
        layer, prior = attribution.attribute_layer(
            routing_correct=True, attack_surface_complete=True, cross_file_flow_connected=False,
        )
        self.assertEqual(layer, "cross_file_flow")
        self.assertEqual(prior, ["routing", "attack_surface"])

    def test_reasoning_layer(self):
        layer, prior = attribution.attribute_layer(
            routing_correct=True, attack_surface_complete=True,
            cross_file_flow_connected=True, reasoning_would_catch_it=False,
        )
        self.assertEqual(layer, "reasoning")
        self.assertEqual(prior, ["routing", "attack_surface", "cross_file_flow"])

    def test_missing_evidence_for_next_gate_refuses_not_defaults(self):
        # routing passed, but attack_surface has no evidence -- must
        # refuse, not silently default to "reasoning" or any other
        # bucket.
        with self.assertRaises(attribution.AttributionError):
            attribution.attribute_layer(routing_correct=True)

    def test_missing_evidence_for_routing_itself_refuses(self):
        with self.assertRaises(attribution.AttributionError):
            attribution.attribute_layer(routing_correct=None)

    def test_all_gates_passed_refuses_not_a_miss(self):
        with self.assertRaises(attribution.AttributionError):
            attribution.attribute_layer(
                routing_correct=True, attack_surface_complete=True,
                cross_file_flow_connected=True, reasoning_would_catch_it=True,
            )

    def test_non_bool_verdict_is_rejected_not_treated_as_passed(self):
        """[ADDED, per a round-1 independent review Minor]: the
        previous version only special-cased `is False`, so a non-bool
        value like the string "false" or 0 fell through and was
        silently treated as "this gate passed," including being
        recorded in priorLayersPassed."""
        for sneaky_value in ("false", "true", 0, 1, "no"):
            with self.subTest(value=sneaky_value):
                with self.assertRaises(attribution.AttributionError):
                    attribution.attribute_layer(routing_correct=sneaky_value)

    def test_does_not_just_pick_first_non_null(self):
        # A naive "pick the first gate that has ANY value" implementation
        # would wrongly return "routing" here (its value, True, is the
        # first non-None value seen) instead of correctly walking
        # forward to find the actual failing gate.
        layer, prior = attribution.attribute_layer(
            routing_correct=True, attack_surface_complete=True, cross_file_flow_connected=False,
        )
        self.assertEqual(layer, "cross_file_flow")
        self.assertNotEqual(layer, "routing")


class RecordMissTests(unittest.TestCase):
    def test_builds_a_consistent_record(self):
        rec = attribution.record_miss(
            record_id="m1",
            routing_correct=True,
            attack_surface_complete=False,
            observed_miss="missing entry point in map",
            expected_finding="CONFIRMED SSRF",
            evidence={"path": "a/Controller.cs", "observation": "endpoint not in attack-surface.json"},
            remediation="add node for this endpoint",
            scope="this endpoint only",
            human_confirmed_by="reviewer",
            created_at="2026-09-23T00:00:00Z",
        )
        self.assertEqual(rec["layer"], "attack_surface")
        self.assertEqual(rec["priorLayersPassed"], ["routing"])


if __name__ == "__main__":
    unittest.main()
