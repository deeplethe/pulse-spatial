import unittest
from pathlib import Path

from pulse_spatial.experiments.end_to_end import run_end_to_end


DATASET = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "ibtracs"
    / "snapshots"
    / "ibtracs-last3years-main-2026-07-16.csv"
)


class EndToEndExperimentTests(unittest.TestCase):
    def test_real_track_exercises_all_four_modes_and_projection(self) -> None:
        result = run_end_to_end(DATASET)
        self.assertTrue(result["summary"]["allChecksPass"])
        self.assertEqual(result["trace"]["finalState"], "AtRisk")
        self.assertEqual(result["trace"]["stateChanges"], 1)
        self.assertTrue(result["projection"]["crossViewMatches"])
        self.assertEqual(
            result["modalExecution"]["observations"],
            result["dataset"]["points"],
        )


if __name__ == "__main__":
    unittest.main()
