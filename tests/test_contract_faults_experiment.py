import unittest

from pulse_spatial.experiments.contract_faults import run_contract_faults


class ContractFaultExperimentTests(unittest.TestCase):
    def test_all_selected_contracts_and_mutation_oracles_hold(self) -> None:
        result = run_contract_faults()
        summary = result["summary"]
        self.assertEqual(summary["caseCount"], 4)
        self.assertEqual(summary["pulseContractsHeld"], 4)
        self.assertEqual(summary["workflowMutantsEscapingArtifactValidation"], 4)
        self.assertEqual(summary["workflowMutantsCaughtByExternalOracle"], 4)

    def test_each_case_reports_enforcement_and_claim_boundary(self) -> None:
        result = run_contract_faults()
        for case in result["cases"]:
            self.assertTrue(case["pulse"]["contractHeld"])
            self.assertTrue(
                case["standardsWorkflowMutant"][
                    "unchangedRdfShaclInputConforms"
                ]
            )
            self.assertTrue(
                case["standardsWorkflowMutant"]["externalOracleCaught"]
            )
        self.assertIn("does not establish", result["claimBoundary"])


if __name__ == "__main__":
    unittest.main()
