import unittest
from pathlib import Path

from pulse_spatial import (
    GeofenceConstraint,
    Point,
    load_pulse,
    validate_projection_parity,
)


EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "cold_chain_geofence.pulse"
)


class ReferenceValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = load_pulse(EXAMPLE)

    def test_inside_position_conforms_in_both_views(self) -> None:
        report = validate_projection_parity(
            self.model.world, self.model.constraints
        )
        self.assertTrue(report.matches)
        self.assertTrue(report.internal_conforms)
        self.assertTrue(report.projected_conforms)
        self.assertEqual(report.internal_violations, ())
        self.assertEqual(report.projected_result_count, 0)

    def test_outside_position_violates_both_views(self) -> None:
        world = self.model.world.clone()
        world.assert_position("batch_102", Point(121.52, 31.2))
        report = validate_projection_parity(world, self.model.constraints)
        self.assertTrue(report.matches)
        self.assertFalse(report.internal_conforms)
        self.assertFalse(report.projected_conforms)
        self.assertEqual(len(report.internal_violations), 1)
        self.assertEqual(report.projected_result_count, 1)

    def test_boundary_distinguishes_inside_from_covered_by(self) -> None:
        world = self.model.world.clone()
        world.assert_position("batch_102", Point(121.49, 31.2))
        inside = GeofenceConstraint(
            "StrictInterior",
            "batch_102",
            "ColdZone",
            predicate="inside",
        )
        covered_by = GeofenceConstraint(
            "BoundaryAllowed",
            "batch_102",
            "ColdZone",
            predicate="coveredBy",
        )

        inside_report = validate_projection_parity(world, (inside,))
        covered_report = validate_projection_parity(world, (covered_by,))

        self.assertTrue(inside_report.matches)
        self.assertFalse(inside_report.internal_conforms)
        self.assertFalse(inside_report.projected_conforms)
        self.assertTrue(covered_report.matches)
        self.assertTrue(covered_report.internal_conforms)
        self.assertTrue(covered_report.projected_conforms)

    def test_state_guard_is_inactive_in_both_views(self) -> None:
        world = self.model.world.clone()
        world.assert_position("batch_102", Point(121.52, 31.2))
        world.states["batch_102"] = "AtRisk"
        report = validate_projection_parity(world, self.model.constraints)
        self.assertTrue(report.matches)
        self.assertTrue(report.internal_conforms)
        self.assertTrue(report.projected_conforms)


if __name__ == "__main__":
    unittest.main()
