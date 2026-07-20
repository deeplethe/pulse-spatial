import unittest

from pulse_spatial.experiments.postgis_topology_external import (
    parse_postgis_rows,
)


class PostgisTopologyExternalTests(unittest.TestCase):
    def test_parse_postgis_rows_preserves_four_predicates(self) -> None:
        parsed = parse_postgis_rows("point,region,f,t,f,t\n")
        self.assertEqual(
            parsed[("point", "region")],
            {
                "inside": False,
                "coveredBy": True,
                "disjoint": False,
                "onBoundary": True,
            },
        )

    def test_parse_postgis_rows_rejects_duplicate_pairs(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse_postgis_rows(
                "point,region,t,t,f,f\npoint,region,t,t,f,f\n"
            )


if __name__ == "__main__":
    unittest.main()
