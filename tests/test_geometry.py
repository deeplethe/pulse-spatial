import unittest

from pulse_spatial import CRS84, Point, Polygon, covered_by, on_boundary, within


class GeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.square = Polygon.from_xy(
            [(0, 0), (10, 0), (10, 10), (0, 10)], CRS84
        )

    def test_within_excludes_boundary(self) -> None:
        self.assertTrue(within(Point(5, 5), self.square))
        self.assertFalse(within(Point(0, 5), self.square))
        self.assertTrue(covered_by(Point(0, 5), self.square))
        self.assertFalse(covered_by(Point(11, 5), self.square))

    def test_mixed_crs_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "CRS mismatch"):
            within(Point(5, 5, "urn:local:grid"), self.square)

    def test_topology_is_not_tied_to_an_absolute_coordinate_epsilon(self) -> None:
        tiny = Polygon.from_xy(
            [(0, 0), (1e-9, 0), (1e-9, 1e-9), (0, 1e-9)], CRS84
        )
        point = Point(5e-10, 5e-10, CRS84)
        self.assertTrue(within(point, tiny))
        self.assertFalse(on_boundary(point, tiny))

    def test_invalid_polygon_shells_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "collinear"):
            Polygon.from_xy([(0, 0), (1, 0), (2, 0)], CRS84)
        with self.assertRaisesRegex(ValueError, "simple"):
            Polygon.from_xy([(0, 0), (2, 2), (0, 2), (2, 0)], CRS84)
        with self.assertRaisesRegex(ValueError, "zero-length"):
            Polygon.from_xy([(0, 0), (2, 0), (2, 0), (0, 2)], CRS84)


if __name__ == "__main__":
    unittest.main()
