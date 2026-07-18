import unittest
from datetime import datetime

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


if __name__ == "__main__":
    unittest.main()
