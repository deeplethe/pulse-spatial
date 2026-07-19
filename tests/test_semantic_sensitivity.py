import unittest

from pulse_spatial.experiments.semantic_sensitivity import run_sensitivity


class SemanticSensitivityTests(unittest.TestCase):
    def test_all_declared_policy_alternatives_change_an_observable(self) -> None:
        result = run_sensitivity()
        summary = result["summary"]
        self.assertEqual(summary["policies"], 6)
        self.assertEqual(summary["distinguishedAlternatives"], 6)
        self.assertTrue(summary["allAlternativesChangeObservableOutcome"])


if __name__ == "__main__":
    unittest.main()
