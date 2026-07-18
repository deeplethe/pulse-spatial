import unittest

from pulse_spatial import CRS84, Point, Polygon, covered_by, within


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


if __name__ == "__main__":
    unittest.main()
