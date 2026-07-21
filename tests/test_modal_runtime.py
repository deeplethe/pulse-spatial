import unittest
from datetime import datetime, timedelta

from pulse_spatial import (
    CRS84,
    EventKind,
    GeofenceEvent,
    GeofenceConstraint,
    GeofenceRule,
    LocationObservation,
    Point,
    Polygon,
    SpatialRuntime,
    SpatialWorld,
    SustainedEventSpec,
    TemporalSpatialRuntime,
    project_geosparql,
)


class ModalRuntimeTests(unittest.TestCase):
    def make_world(self) -> SpatialWorld:
        return SpatialWorld(
            regions={
                "ColdZone": Polygon.from_xy(
                    [(0, 0), (10, 0), (10, 10), (0, 10)], CRS84
                )
            },
            positions={"batch_102": Point(5, 5)},
            states={"batch_102": "Safe"},
        )

    def make_rule(self) -> GeofenceRule:
        return GeofenceRule(
            name="ZoneDeparture",
            kind=EventKind.LEAVES,
            subject="batch_102",
            region="ColdZone",
            from_state="Safe",
            to_state="AtRisk",
        )

    def test_observation_does_not_overwrite_asserted_position(self) -> None:
        world = self.make_world()
        world.record_observation(
            LocationObservation(
                subject="batch_102",
                value=Point(12, 5),
                observed_at=datetime.fromisoformat("2026-07-18T09:12:00+08:00"),
                source="gps_07",
                confidence=0.98,
                accuracy_m=5,
            )
        )
        self.assertEqual(world.positions["batch_102"], Point(5, 5))
        self.assertEqual(world.observations[-1].value, Point(12, 5))

    def test_leave_event_drives_state_transition(self) -> None:
        world = self.make_world()
        events = SpatialRuntime(world, [self.make_rule()]).move(
            "batch_102", Point(12, 5)
        )
        self.assertEqual(
            events,
            (GeofenceEvent(EventKind.LEAVES, "batch_102", "ColdZone"),),
        )
        self.assertEqual(world.states["batch_102"], "AtRisk")

    def test_scenario_isolated_from_authoritative_world(self) -> None:
        world = self.make_world()
        result = SpatialRuntime(world, [self.make_rule()]).scenario(
            [("batch_102", Point(12, 5))]
        )
        self.assertEqual(world.positions["batch_102"], Point(5, 5))
        self.assertEqual(world.states["batch_102"], "Safe")
        self.assertEqual(result.world.positions["batch_102"], Point(12, 5))
        self.assertEqual(result.world.states["batch_102"], "AtRisk")

    def test_cross_crs_move_fails_without_mutating_world(self) -> None:
        world = self.make_world()
        original = world.positions["batch_102"]
        with self.assertRaisesRegex(ValueError, "between CRSs"):
            SpatialRuntime(world).move(
                "batch_102",
                Point(12, 5, "https://example.org/crs/local"),
            )
        self.assertEqual(world.positions["batch_102"], original)

    def test_normative_constraint_and_projection(self) -> None:
        world = self.make_world()
        constraint = GeofenceConstraint(
            "ColdZoneContainment",
            "batch_102",
            "ColdZone",
            while_state="Safe",
        )
        self.assertEqual(world.validate((constraint,)), ())
        world.assert_position("batch_102", Point(12, 5))
        violations = world.validate((constraint,))
        self.assertEqual(len(violations), 1)

        turtle = project_geosparql(world)
        self.assertIn("geo:asWKT", turtle)
        self.assertIn("POINT (12 5)", turtle)
        self.assertIn(CRS84, turtle)

    def test_sustained_leave_fires_at_deadline(self) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        rule = GeofenceRule(
            name="SustainedDeparture",
            kind=EventKind.LEAVES,
            subject="batch_102",
            region="ColdZone",
            from_state="Safe",
            to_state="AtRisk",
            minimum_duration_seconds=600,
        )
        runtime = TemporalSpatialRuntime(self.make_world(), started, [rule])
        step = runtime.move_at("batch_102", Point(12, 5), started)
        self.assertEqual(len(step.instantaneous), 1)
        self.assertEqual(runtime.world.states["batch_102"], "Safe")

        events = runtime.advance_to(started + timedelta(minutes=10))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].effective_at, started + timedelta(minutes=10))
        self.assertEqual(runtime.world.states["batch_102"], "AtRisk")

    def test_duration_rule_guard_is_required_when_monitor_starts(self) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        world = self.make_world()
        world.states["batch_102"] = "AtRisk"
        rule = GeofenceRule(
            name="SustainedDeparture",
            kind=EventKind.LEAVES,
            subject="batch_102",
            region="ColdZone",
            from_state="Safe",
            to_state="AtRisk",
            minimum_duration_seconds=600,
        )
        runtime = TemporalSpatialRuntime(world, started, [rule])

        runtime.move_at("batch_102", Point(12, 5), started)

        self.assertEqual(
            runtime.advance_to(started + timedelta(minutes=10)),
            (),
        )

    def test_duration_rule_guard_is_rechecked_at_deadline(self) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        rule = GeofenceRule(
            name="SustainedDeparture",
            kind=EventKind.LEAVES,
            subject="batch_102",
            region="ColdZone",
            from_state="Safe",
            to_state="AtRisk",
            minimum_duration_seconds=600,
        )
        runtime = TemporalSpatialRuntime(self.make_world(), started, [rule])
        runtime.move_at("batch_102", Point(12, 5), started)
        runtime.world.states["batch_102"] = "Maintenance"

        events = runtime.advance_to(started + timedelta(minutes=10))

        self.assertEqual(len(events), 1)
        self.assertEqual(runtime.world.states["batch_102"], "Maintenance")

    def test_duration_monitor_uses_state_before_same_crossing_immediate_rule(
        self,
    ) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        immediate = GeofenceRule(
            name="ImmediateDeparture",
            kind=EventKind.LEAVES,
            subject="batch_102",
            region="ColdZone",
            from_state="Safe",
            to_state="Mid",
        )
        sustained = GeofenceRule(
            name="SustainedDeparture",
            kind=EventKind.LEAVES,
            subject="batch_102",
            region="ColdZone",
            from_state="Safe",
            to_state="AtRisk",
            minimum_duration_seconds=600,
        )
        runtime = TemporalSpatialRuntime(
            self.make_world(), started, [immediate, sustained]
        )

        runtime.move_at("batch_102", Point(12, 5), started)
        self.assertEqual(runtime.world.states["batch_102"], "Mid")

        events = runtime.advance_to(started + timedelta(minutes=10))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].specification, "SustainedDeparture")
        self.assertEqual(runtime.world.states["batch_102"], "Mid")

    def test_duration_monitor_does_not_use_same_crossing_post_rule_state(
        self,
    ) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        immediate = GeofenceRule(
            name="ImmediateDeparture",
            kind=EventKind.LEAVES,
            subject="batch_102",
            region="ColdZone",
            from_state="Safe",
            to_state="Mid",
        )
        sustained = GeofenceRule(
            name="SustainedDeparture",
            kind=EventKind.LEAVES,
            subject="batch_102",
            region="ColdZone",
            from_state="Mid",
            to_state="AtRisk",
            minimum_duration_seconds=600,
        )
        runtime = TemporalSpatialRuntime(
            self.make_world(), started, [immediate, sustained]
        )

        runtime.move_at("batch_102", Point(12, 5), started)
        self.assertEqual(runtime.world.states["batch_102"], "Mid")

        events = runtime.advance_to(started + timedelta(minutes=10))
        self.assertEqual(events, ())
        self.assertEqual(runtime.world.states["batch_102"], "Mid")

    def test_sustained_leave_is_cancelled_by_reentry(self) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        monitor = SustainedEventSpec(
            "OutsideForTenMinutes",
            EventKind.LEAVES,
            "batch_102",
            "ColdZone",
            600,
        )
        runtime = TemporalSpatialRuntime(
            self.make_world(),
            started,
            sustained_events=[monitor],
        )
        runtime.move_at("batch_102", Point(12, 5), started)
        runtime.move_at(
            "batch_102",
            Point(5, 5),
            started + timedelta(minutes=9),
        )
        self.assertEqual(
            runtime.advance_to(started + timedelta(minutes=20)),
            (),
        )

    def test_deadline_fires_before_move_at_same_timestamp(self) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        monitor = SustainedEventSpec(
            "OutsideForTenMinutes",
            EventKind.LEAVES,
            "batch_102",
            "ColdZone",
            600,
        )
        runtime = TemporalSpatialRuntime(
            self.make_world(),
            started,
            sustained_events=[monitor],
        )
        runtime.move_at("batch_102", Point(12, 5), started)
        result = runtime.move_at(
            "batch_102",
            Point(5, 5),
            started + timedelta(minutes=10),
        )
        self.assertEqual(len(result.sustained), 1)
        self.assertEqual(result.sustained[0].emitted_at, result.observed_at)
        self.assertEqual(result.instantaneous[0].kind, EventKind.ENTERS)

    def test_temporal_runtime_rejects_backwards_time(self) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        runtime = TemporalSpatialRuntime(self.make_world(), started)
        with self.assertRaisesRegex(ValueError, "backwards"):
            runtime.advance_to(started - timedelta(seconds=1))

    def test_invalid_temporal_move_is_atomic(self) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        runtime = TemporalSpatialRuntime(self.make_world(), started)
        with self.assertRaisesRegex(ValueError, "between CRSs"):
            runtime.move_at(
                "batch_102",
                Point(12, 5, "https://example.org/crs/local"),
                started + timedelta(minutes=5),
            )
        self.assertEqual(runtime.current_time, started)
        self.assertEqual(runtime.world.positions["batch_102"], Point(5, 5))

    def test_backwards_time_has_priority_over_crs_mismatch(self) -> None:
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        runtime = TemporalSpatialRuntime(self.make_world(), started)

        with self.assertRaisesRegex(ValueError, "backwards"):
            runtime.move_at(
                "batch_102",
                Point(12, 5, "https://example.org/crs/local"),
                started - timedelta(seconds=1),
            )

        self.assertEqual(runtime.current_time, started)
        self.assertEqual(runtime.world.positions["batch_102"], Point(5, 5))


if __name__ == "__main__":
    unittest.main()
