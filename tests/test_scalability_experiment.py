import unittest

from pulse_spatial.experiments.scalability import run_scalability


class ScalabilityExperimentTests(unittest.TestCase):
    def test_small_scale_ladder_is_complete_and_deterministic(self) -> None:
        result = run_scalability((10, 100), repetitions=1)
        self.assertTrue(result["summary"]["allChecksPass"])
        self.assertEqual(result["summary"]["largestSize"], 100)
        self.assertEqual(result["summary"]["largestExecutionEvents"], 100)
        self.assertEqual(
            result["rows"][1]["evidenceAndProjection"]["observationResources"],
            100,
        )


if __name__ == "__main__":
    unittest.main()
