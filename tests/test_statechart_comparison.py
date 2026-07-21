import unittest

from pulse_spatial.experiments.statechart_comparison import (
    run_statechart_comparison,
)


class StatechartComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_statechart_comparison()

    def test_independent_statechart_matches_pulse_on_the_baseline(self) -> None:
        baseline = self.result["baseline"]
        self.assertTrue(baseline["shaclConforms"])
        self.assertTrue(baseline["exactOutcomeMatch"])
        self.assertEqual(
            baseline["pulseOutcome"],
            baseline["rdfStatechartOutcome"],
        )

    def test_all_faults_are_located_in_each_contract_configuration(self) -> None:
        summary = self.result["summary"]
        self.assertEqual(summary["faultCount"], 4)
        self.assertEqual(summary["pulsePreventedOrDetected"], 4)
        self.assertEqual(summary["unprofiledDetectedByOracle"], 4)
        self.assertEqual(summary["profiledPreventedOrDetected"], 4)

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
