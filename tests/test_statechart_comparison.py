import unittest

from pulse_spatial.experiments.statechart_comparison import (
    run_statechart_comparison,
)


class StatechartComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_statechart_comparison()

    def test_researcher_authored_statechart_matches_pulse_on_baseline(self) -> None:
        baseline = self.result["baseline"]
        self.assertTrue(baseline["shaclConforms"])
        self.assertTrue(baseline["exactOutcomeMatch"])
        self.assertEqual(
            baseline["pulseOutcome"],
            baseline["rdfStatechartOutcome"],
        )

    def test_all_faults_are_located_in_each_contract_configuration(self) -> None:
        summary = self.result["summary"]
        self.assertEqual(summary["faultCount"], 6)
        self.assertEqual(summary["pulsePreventedOrDetected"], 6)
        self.assertEqual(summary["unprofiledDetectedByOracle"], 6)
        self.assertEqual(summary["profiledPreventedOrDetected"], 6)

        fault_ids = {fault["id"] for fault in self.result["faults"]}
        self.assertIn("F-OBSERVATION-OVERWRITE", fault_ids)
        self.assertIn("F-MONITOR-START-GUARD", fault_ids)

    def test_unprofiled_composition_requires_an_outcome_or_source_oracle(self) -> None:
        oracle_stages = {"outcome-oracle", "source-state-oracle"}
        for fault in self.result["faults"]:
            self.assertIn(
                fault["unprofiledRdfStatechart"]["stage"],
                oracle_stages,
            )
        self.assertIn("not a usability", self.result["claimBoundary"])


if __name__ == "__main__":
    unittest.main()
