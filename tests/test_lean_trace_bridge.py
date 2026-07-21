import unittest

from pulse_spatial.experiments.lean_trace_bridge import compare_with_lean


class LeanTraceBridgeTests(unittest.TestCase):
    def test_all_generated_observable_traces_match_exactly(self) -> None:
        result = compare_with_lean()
        self.assertEqual(result["leanCaseCount"], 16)
        self.assertEqual(result["pythonCaseCount"], 16)
        self.assertEqual(result["exactMatches"], 16)
        self.assertEqual(result["mismatchIndexes"], [])
        self.assertTrue(result["allExact"])
        self.assertIn("not a general refinement theorem", result["claimBoundary"])


if __name__ == "__main__":
    unittest.main()
