import unittest

from pulse_spatial.experiments.ogc_conformance import (
    DGGS_NON_SF_FUNCTIONS,
    DGGS_QUERY_FUNCTIONS,
    _aggregate_status,
    build_probe_plan,
    load_manifest,
    probes_for,
)
from pulse_spatial.experiments.ogc_source_audit import run_source_audit


class OgcConformanceTests(unittest.TestCase):
    def test_pinned_official_rdf_sources_are_audited_without_equating_them(self) -> None:
        result = run_source_audit()
        self.assertTrue(result["auditPassed"])
        inventories = result["inventories"]
        self.assertEqual(inventories["annexA"]["testAllocations"], 55)
        self.assertEqual(
            inventories["requirementsRegister"]["conformanceTestResources"],
            58,
        )
        self.assertEqual(inventories["serviceDescription"]["features"], 52)
        self.assertEqual(
            result["crosswalkSummary"]["annexAllocationsCorroborated"],
            55,
        )

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

    def test_query_rewrite_covers_every_named_relation(self) -> None:
        identifiers = (
            "/conf/query-rewrite-extension/sf-query-rewrite",
            "/conf/query-rewrite-extension/eh-query-rewrite",
            "/conf/query-rewrite-extension/rcc8-query-rewrite",
        )
        probes = tuple(
            probe for identifier in identifiers for probe in probes_for(identifier)
        )
        self.assertEqual(len(probes), 24)
        self.assertEqual(len({probe.name for probe in probes}), 24)
        self.assertTrue(
            all(probe.query.count(f"geo:{probe.name}") == 4 for probe in probes)
        )

    def test_dggs_plan_checks_every_required_function(self) -> None:
        simple_features = probes_for(
            "/conf/geometry-extension-dggs/query-functions"
        )
        non_simple_features = probes_for(
            "/conf/geometry-extension-dggs/query-functions-non-sf"
        )
        aggregates = probes_for("/conf/geometry-extension-dggs/sa-functions")
        self.assertEqual(len(simple_features), len(DGGS_QUERY_FUNCTIONS))
        self.assertEqual(len(simple_features), 23)
        self.assertEqual(len(non_simple_features), len(DGGS_NON_SF_FUNCTIONS))
        self.assertEqual(len(non_simple_features), 14)
        self.assertEqual(len(aggregates), 6)
        self.assertTrue(
            all("https://h3geo.org/" in probe.query for probe in simple_features)
        )


if __name__ == "__main__":
    unittest.main()
