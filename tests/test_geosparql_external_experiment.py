import unittest

from pulse_spatial.experiments.geosparql_external import (
    compare_results,
    expected_results,
    parse_results,
    topology_world,
)


class ExternalGeoSparqlExperimentTests(unittest.TestCase):
    def test_topology_world_uses_only_crs84_and_has_cross_product(self) -> None:
        world = topology_world()
        self.assertEqual(len(world.positions), 86)
        self.assertEqual(len(world.regions), 86)
        self.assertEqual(len(expected_results(world)), 7396)
        self.assertEqual(
            {point.crs for point in world.positions.values()},
            {"http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
        )

    def test_standard_sparql_json_is_parsed(self) -> None:
        payload = {
            "results": {
                "bindings": [
                    {
                        "subject": {
                            "value": "https://example.test/instance/a%20b"
                        },
                        "region": {"value": "https://example.test/region/r"},
                        "inside": {"value": "false"},
                        "coveredBy": {"value": "true"},
                        "disjoint": {"value": "false"},
                        "onBoundary": {"value": "true"},
                    }
                ]
            }
        }
        self.assertEqual(
            parse_results(payload),
            {
                ("a b", "r"): {
                    "inside": False,
                    "coveredBy": True,
                    "disjoint": False,
                    "onBoundary": True,
                }
            },
        )

    def test_comparison_reports_missing_and_changed_pairs(self) -> None:
        expected = {
            ("a", "r"): {
                "inside": True,
                "coveredBy": True,
                "disjoint": False,
                "onBoundary": False,
            },
            ("b", "r"): {
                "inside": False,
                "coveredBy": False,
                "disjoint": True,
                "onBoundary": False,
            },
        }
        actual = {
            ("a", "r"): {
                "inside": False,
                "coveredBy": True,
                "disjoint": False,
                "onBoundary": False,
            },
        }
        mismatches = compare_results(expected, actual)
        self.assertEqual(len(mismatches), 2)
        self.assertEqual(mismatches[0]["subject"], "a")
        self.assertIsNone(mismatches[1]["actual"])


if __name__ == "__main__":
    unittest.main()
