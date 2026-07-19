import unittest

from pulse_spatial.experiments.formal_properties import run_bounded_checks


class FormalPropertiesExperimentTests(unittest.TestCase):
    def test_depth_three_exhaustive_check_passes(self) -> None:
        result = run_bounded_checks(max_depth=3)
        self.assertTrue(result["summary"]["allChecksPass"])
        self.assertEqual(result["summary"]["failures"], 0)
        self.assertEqual(result["abstraction"]["sequenceCount"], 84)
        self.assertEqual(result["checks"]["determinism"], 84)
        self.assertGreater(result["checks"]["preservation"], 0)


if __name__ == "__main__":
    unittest.main()
