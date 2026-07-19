import copy
import json
import unittest
from pathlib import Path

from pulse_spatial.experiments.composition import (
    DEFAULT_ROOT,
    _validate_mf_json,
    run_comparison,
)


class CompositionExperimentTests(unittest.TestCase):
    def test_all_paths_produce_the_frozen_expected_outcome(self) -> None:
        result = run_comparison(repetitions=1)
        self.assertTrue(result["equivalence"]["allPathsMatchExpected"])
        self.assertTrue(result["equivalence"]["allPathOutcomesEquivalent"])
        paths = result["paths"]
        for value in paths.values():
            self.assertEqual(value["outcome"]["final_state"], "AtRisk")
            self.assertEqual(len(value["outcome"]["instantaneous"]), 3)
            self.assertEqual(len(value["outcome"]["sustained"]), 1)
            self.assertEqual(
                value["outcome"]["sustained"][0]["started_at"],
                "2026-07-19T08:20:00Z",
            )

    def test_composition_metrics_are_descriptive_and_complete(self) -> None:
        result = run_comparison(repetitions=1)
        metrics = result["descriptiveCompositionMetrics"]
        self.assertEqual(metrics["pulse"]["inputFileCount"], 1)
        self.assertEqual(metrics["semanticWebComposition"]["inputFileCount"], 3)
        self.assertEqual(metrics["movingFeaturesComposition"]["inputFileCount"], 2)
        self.assertIn("not standards conformance", result["claimBoundary"])

    def test_mf_json_prism_requires_step_interpolation(self) -> None:
        path = Path(DEFAULT_ROOT) / "moving-features" / "moving-feature.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        invalid = copy.deepcopy(value)
        invalid["temporalGeometry"]["interpolation"] = "Linear"
        with self.assertRaisesRegex(ValueError, "Step interpolation"):
            _validate_mf_json(invalid)


if __name__ == "__main__":
    unittest.main()
