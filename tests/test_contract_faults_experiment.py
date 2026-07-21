import unittest

from pulse_spatial.experiments.contract_faults import run_contract_faults


class ContractFaultExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_contract_faults()

    def test_generated_corpus_matches_and_kills_all_operators(self) -> None:
        summary = self.result["summary"]
        self.assertEqual(summary["generatedTraceCount"], 37_440)
        self.assertEqual(summary["pulseMatchesReference"], 37_440)
        self.assertEqual(summary["pulseReferenceMismatches"], 0)
        self.assertEqual(summary["mutationOperatorCount"], 10)
        self.assertEqual(summary["mutantsKilled"], 10)

    def test_each_operator_is_single_field_and_has_a_witness(self) -> None:
        covered_fields = set()
        for operator in self.result["operators"]:
            self.assertTrue(operator["killed"])
            self.assertGreater(operator["tracesDistinguished"], 0)
            self.assertTrue(operator["changedSemanticField"])
            covered_fields.add(operator["changedSemanticField"])
            self.assertIsNotNone(operator["firstWitness"])
            self.assertTrue(operator["firstWitness"]["changedOutcomeFields"])
        self.assertEqual(len(covered_fields), 9)
        self.assertIn("declared finite trace grid", self.result["claimBoundary"])


if __name__ == "__main__":
    unittest.main()
