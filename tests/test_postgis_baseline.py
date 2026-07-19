import unittest
from datetime import UTC, datetime, timedelta

from pulse_spatial.experiments.ibtracs import Track, TrackPoint
from pulse_spatial.experiments.postgis_baseline import (
    _plan_uses_index,
    trace_from_memberships,
)
from pulse_spatial.experiments.spatiotemporal import STUDY_ZONES


class PostgisBaselineTests(unittest.TestCase):
    def test_membership_rows_drive_events_and_durations(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        track = Track(
            "T1",
            "fixture",
            2026,
            "NA",
            (
                TrackPoint(start, 0.0, 0.0),
                TrackPoint(start + timedelta(hours=1), 0.0, 1.0),
                TrackPoint(start + timedelta(hours=8), 0.0, 2.0),
            ),
        )
        region = STUDY_ZONES[0][0]
        positive = {("T1", 1, region), ("T1", 2, region)}
        trace = trace_from_memberships((track,), positive)
        events = [event for event in trace.instantaneous if event.region == region]
        sustained = [event for event in trace.sustained if event.region == region]
        self.assertEqual(len(trace.memberships), 10)
        self.assertEqual([event.kind for event in events], ["enters"])
        self.assertEqual([event.duration_seconds for event in sustained], [21600])

    def test_plan_index_detection_is_structural(self) -> None:
        plan = [{"Plan": {"Plans": [{"Index Name": "samples_geom_gix"}]}}]
        self.assertTrue(_plan_uses_index(plan, "samples_geom_gix"))
        self.assertFalse(_plan_uses_index(plan, "other_index"))


if __name__ == "__main__":
    unittest.main()
