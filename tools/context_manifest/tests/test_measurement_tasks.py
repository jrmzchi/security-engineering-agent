"""Invariants over measurement_tasks.py's T1-T5/T4b and the explicit
DEEP case (implementation-batches.md Batch 2 criteria 3, 4, 5)."""

from __future__ import annotations

import unittest

from .measurement_tasks import TASKS, run_task


class RepresentativeTaskSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = {name: run_task(name) for name in TASKS}

    def test_every_manifest_on_both_paths_validates(self):
        for name, r in self.results.items():
            with self.subTest(task=name):
                self.assertTrue(r["manifest_validation"]["built_in"])
                self.assertTrue(r["manifest_validation"]["jev_path"])

    def test_criterion_4_domains_never_below_built_in(self):
        for name, r in self.results.items():
            with self.subTest(task=name):
                self.assertTrue(r["domains_superset_of_built_in"], r)
                self.assertTrue(set(r["jev_path"]["domains"]) >= set(r["floor_domains"]))

    def test_t1_no_jev_call_and_empty_domains(self):
        r = self.results["T1"]
        self.assertEqual(r["jev_client_calls"], 0)
        self.assertEqual(r["jev_path"]["domains"], [])
        self.assertEqual(r["jev_outcome"], "no_token")
        self.assertFalse(r["jev_path"]["degradation"]["jevAttempted"])
        self.assertIn("Jev not invoked", r["jev_path"]["degradation"]["fallbackReason"])

    def test_criterion_3_discernible_effect_without_domain_reduction(self):
        # T3: same domains, lawful lower budget with a named Factor.
        t3 = self.results["T3"]
        self.assertEqual(t3["jev_outcome"], "success")
        self.assertEqual(t3["jev_path"]["domains"], t3["built_in"]["domains"])
        self.assertNotEqual(t3["jev_path"]["reviewBudget"], t3["built_in"]["reviewBudget"])
        self.assertEqual(t3["jev_path"]["reviewBudget"], "FOCUSED")
        # T2: superset domains + higher budget + priority order.
        t2 = self.results["T2"]
        self.assertEqual(t2["jev_outcome"], "success")
        self.assertTrue(set(t2["jev_path"]["domains"]) > set(t2["built_in"]["domains"]))
        self.assertEqual(t2["jev_path"]["priorityOrder"][0], "data-security")
        # T5: identical domains (cross-domain floor computed identically), budget/priority differ.
        t5 = self.results["T5"]
        self.assertEqual(t5["jev_outcome"], "success")
        self.assertEqual(t5["jev_path"]["domains"], t5["built_in"]["domains"])
        self.assertEqual(t5["jev_path"]["reviewBudget"], "AUDIT")
        self.assertIsNotNone(t5["jev_path"]["priorityOrder"])
        self.assertIsNone(t5["built_in"]["priorityOrder"])

    def test_t4_fresh_record_consulted_only_after_real_eligibility(self):
        t4 = self.results["T4"]
        self.assertTrue(t4["reuse_decision"]["reusable"])
        self.assertEqual(t4["jev_outcome"], "success")
        self.assertEqual(t4["jev_path"]["intelligenceConsulted"]["feedbackRecordsConsulted"], ["rec-report-ownership"])
        self.assertIsNone(t4["built_in"]["intelligenceConsulted"])

    def test_t4b_stale_record_is_cold(self):
        t4b = self.results["T4b"]
        self.assertFalse(t4b["reuse_decision"]["reusable"])
        self.assertIn("RECORD_STALE", t4b["reuse_decision"]["reasons"])
        self.assertEqual(t4b["jev_outcome"], "success")
        self.assertIsNone(t4b["jev_path"]["intelligenceConsulted"])  # nothing offered, nothing consulted
        # Everything else equals T4 -- the ONLY difference is the missing reuse.
        t4 = self.results["T4"]
        self.assertEqual(t4b["jev_path"]["domains"], t4["jev_path"]["domains"])
        self.assertEqual(t4b["jev_path"]["reviewBudget"], t4["jev_path"]["reviewBudget"])

    def test_criterion_5_explicit_deep(self):
        ok_case = self.results["DEEP-fixture-pair"]
        self.assertEqual(len(ok_case["floor_domains"]), 9)
        self.assertNotIn("web-security", ok_case["floor_domains"])
        self.assertEqual(ok_case["jev_outcome"], "success")
        self.assertEqual(ok_case["jev_path"]["domains"], ok_case["floor_domains"])
        self.assertEqual(ok_case["jev_path"]["reviewBudget"], "AUDIT")
        # DEEP mandatory activity coverage: every scanner the floor domains map to is selected
        self.assertEqual(set(ok_case["jev_path"]["scannersSelected"]), set(ok_case["built_in"]["scannersSelected"]))
        below = self.results["DEEP-fixture-pair-below-floor"]
        self.assertEqual(below["jev_outcome"], "below_floor")
        self.assertTrue(below["fallback_used"])
        self.assertEqual(below["jev_path"]["domains"], below["floor_domains"])
        self.assertIn("authorization", below["jev_path"]["degradation"]["fallbackReason"])

    def test_fallback_never_lowers_capability(self):
        for name in ("DEEP-fixture-pair-below-floor",):
            r = self.results[name]
            self.assertEqual(r["jev_path"]["domains"], r["built_in"]["domains"])
            self.assertEqual(r["jev_path"]["reviewBudget"], r["built_in"]["reviewBudget"])
            self.assertEqual(r["jev_path"]["scannersSelected"], r["built_in"]["scannersSelected"])


if __name__ == "__main__":
    unittest.main()
