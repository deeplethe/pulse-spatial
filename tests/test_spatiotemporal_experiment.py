import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pulse_spatial.experiments.ibtracs import Track, TrackPoint
from pulse_spatial.experiments.spatiotemporal import _dateline_audit, run_experiment


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
        self.assertEqual(
            result["workload"]["eventTransitionZonePairs"]
            + result["workload"]["nonEventTransitionZonePairs"],
            20,
        )
        self.assertEqual(len(result["workload"]["byRegion"]), 5)
        self.assertEqual(result["workload"]["sustainedEvents"], 2)
        self.assertIn("datelineAudit", result)

    def test_dateline_audit_keeps_latitude_bands_seam_free(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        track = Track(
            "wrapped",
            "wrapped",
            2026,
            "WP",
            (
                TrackPoint(start, 20.0, -179.6),
                TrackPoint(start + timedelta(hours=6), 20.0, 180.0),
            ),
        )
        audit = _dateline_audit((track,))
        self.assertEqual(audit["wrappedTransitions"], 1)
        self.assertEqual(audit["tracksWithWrappedTransitions"], 1)
        self.assertEqual(audit["latitudeBandSeamOnlyChanges"], 0)
        self.assertEqual(
            audit["membershipChangesOnWrappedTransitions"]["NorthernTropics"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
