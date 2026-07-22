import unittest

from pulse_spatial.experiments.lean_trace_bridge import (
    compare_with_lean,
    generated_python_traces,
)


class LeanTraceBridgeTests(unittest.TestCase):
    def test_all_generated_observable_traces_match_exactly(self) -> None:
        result = compare_with_lean()
        self.assertEqual(result["leanCaseCount"], 32)
        self.assertEqual(result["pythonCaseCount"], 32)
        self.assertEqual(result["exactMatches"], 32)
        self.assertEqual(result["mismatchIndexes"], [])
        self.assertTrue(result["allExact"])
        self.assertIn("not a general refinement theorem", result["claimBoundary"])

    def test_equal_deadlines_are_ordered_by_ground_declaration_rank(self) -> None:
        cases = generated_python_traces()["cases"]
        case = next(
            candidate
            for candidate in cases
            if candidate["initialInside"]
            and not candidate["firstInside"]
            and not candidate["secondInside"]
            and not candidate["immediate"]
            and candidate["dualRule"]
        )
        sustained = [
            event for event in case["trace"] if event["kind"] == "sustained"
        ]
        self.assertEqual([event["subject"] for event in sustained], [0, 1])
        self.assertEqual(
            [(event["effectiveAt"], event["emittedAt"]) for event in sustained],
            [(3, 4), (3, 4)],
        )


if __name__ == "__main__":
    unittest.main()
