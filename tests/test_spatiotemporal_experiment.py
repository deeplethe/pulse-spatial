import unittest
from pathlib import Path

from pulse_spatial.experiments.spatiotemporal import run_experiment


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "ibtracs"
    / "synthetic-format-fixture.csv"
)


class SpatiotemporalExperimentTests(unittest.TestCase):
    def test_fixture_has_exact_three_layer_parity(self) -> None:
        result = run_experiment(FIXTURE, repetitions=1)
        self.assertTrue(result["parity"]["matches"])
        self.assertEqual(result["parity"]["membershipMismatches"], 0)
        self.assertEqual(
            result["parity"]["instantaneousEventMismatches"],
            0,
        )
        self.assertEqual(result["parity"]["sustainedEventMismatches"], 0)
        self.assertEqual(result["workload"]["transitionZonePairs"], 20)
        self.assertEqual(result["workload"]["sustainedEvents"], 2)


if __name__ == "__main__":
    unittest.main()
