import tempfile
import unittest
from pathlib import Path

from pulse_spatial.experiments.ibtracs import (
    _normalize_longitude,
    load_ibtracs,
    run_experiment,
    write_normalized_snapshot,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "ibtracs"
    / "synthetic-format-fixture.csv"
)


class IbtracsExperimentTests(unittest.TestCase):
    def test_wrapped_longitude_has_stable_decimal_representation(self) -> None:
        self.assertEqual(_normalize_longitude(180.4), -179.6)

    def test_fixture_loads_units_row_and_main_tracks(self) -> None:
        dataset = load_ibtracs(FIXTURE)
        self.assertEqual(len(dataset.tracks), 2)
        self.assertEqual(dataset.rows_valid, 6)
        self.assertEqual(dataset.rows_invalid, 1)

    def test_fixture_replay_has_exact_reference_parity(self) -> None:
        result = run_experiment(FIXTURE, repetitions=1)
        self.assertTrue(result["parity"]["matches"])
        self.assertEqual(result["parity"]["transitionMismatches"], 0)
        self.assertEqual(result["parity"]["internalEvents"], {
            "enters": 1,
            "leaves": 1,
        })
        self.assertEqual(result["workload"]["transitions"], 4)

    def test_normalized_snapshot_round_trips(self) -> None:
        dataset = load_ibtracs(FIXTURE)
        with tempfile.TemporaryDirectory() as directory:
            snapshot = write_normalized_snapshot(
                dataset,
                Path(directory) / "snapshot.csv",
            )
            reloaded = load_ibtracs(snapshot)
        self.assertEqual(reloaded.tracks, dataset.tracks)


if __name__ == "__main__":
    unittest.main()
