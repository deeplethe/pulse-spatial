import unittest

from pulse_spatial.experiments.ogc_conformance import (
    _aggregate_status,
    build_probe_plan,
    load_manifest,
)


class OgcConformanceTests(unittest.TestCase):
    def test_manifest_covers_all_normative_abstract_tests(self) -> None:
        manifest = load_manifest()
        plan = build_probe_plan(manifest)
        self.assertEqual(len(manifest["classes"]), 7)
        self.assertEqual(len(plan), 55)
        self.assertTrue(all(plan.values()))

    def test_class_status_never_hides_manual_or_error(self) -> None:
        self.assertEqual(_aggregate_status(({"status": "pass"},)), "pass")
        self.assertEqual(
            _aggregate_status(({"status": "pass"}, {"status": "manual"})),
            "manual",
        )
        self.assertEqual(
            _aggregate_status(({"status": "pass"}, {"status": "error"})),
            "error",
        )


if __name__ == "__main__":
    unittest.main()
