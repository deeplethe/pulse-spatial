import unittest

from pulse_spatial.experiments.topology_corpus import CASES, run_corpus


class TopologyCorpusTests(unittest.TestCase):
    def test_all_cases_match_geos_or_reject_as_declared(self) -> None:
        result = run_corpus()
        self.assertTrue(result["summary"]["allChecksPass"])
        self.assertEqual(result["summary"]["topologyMismatches"], 0)
        self.assertEqual(result["summary"]["rejectionMismatches"], 0)

    def test_corpus_covers_numeric_and_boundary_risks(self) -> None:
        names = {case.name for case in CASES}
        self.assertEqual(len(CASES), 89)
        self.assertIn("near-boundary-inside", names)
        self.assertIn("near-boundary-outside", names)
        self.assertIn("concave-reflex-vertex", names)
        self.assertIn("tiny-polygon", names)
        self.assertIn("large-offset-grid", names)
        self.assertIn("profile-triangle-east-large-edge", names)
        self.assertIn("profile-concave-east-tiny-notch", names)

    def test_claim_is_explicitly_not_conformance(self) -> None:
        result = run_corpus()
        self.assertIn("not an OGC or GeoSPARQL conformance", result["claimBoundary"])


if __name__ == "__main__":
    unittest.main()
