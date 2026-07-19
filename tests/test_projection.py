import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.plugins.sparql import prepareQuery

from pulse_spatial import (
    GeofenceConstraint,
    load_pulse,
    project_shacl,
    project_standards,
    write_projection_bundle,
)


EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "cold_chain_geofence.pulse"
)


class StandardsProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = load_pulse(EXAMPLE)

    def test_data_graph_preserves_assertion_observation_distinction(self) -> None:
        graph = project_standards(
            self.model.world, self.model.constraints
        ).data_graph
        self.assertIn("sosa:Observation", graph)
        self.assertIn("pulse:modality pulse:Asserted", graph)
        self.assertIn("pulse:modality pulse:Observed", graph)
        self.assertIn("property/position", graph)
        self.assertIn("a sosa:Property", graph)
        self.assertIn("sensor/gps_07", graph)
        self.assertIn("POINT (121.5 31.2)", graph)
        self.assertIn("POINT (121.512 31.201)", graph)
        self.assertIn('pulse:confidence "0.98"^^xsd:decimal', graph)
        self.assertIn('pulse:accuracyMetres "5"^^xsd:decimal', graph)

    def test_constraint_projects_to_geosparql_enabled_shacl(self) -> None:
        graph = project_shacl(self.model.constraints)
        self.assertIn("a sh:NodeShape", graph)
        self.assertIn("sh:targetNode", graph)
        self.assertIn("geof:sfWithin", graph)
        self.assertIn('pulse:state "Safe"', graph)
        self.assertIn("ColdZoneContainment", graph)

    def test_covered_by_uses_corresponding_geosparql_function(self) -> None:
        graph = project_shacl(
            (
                GeofenceConstraint(
                    "BoundaryAllowed",
                    "batch_102",
                    "ColdZone",
                    predicate="coveredBy",
                ),
            )
        )
        self.assertIn("geof:sfIntersects", graph)
        self.assertNotIn("geof:ehCoveredBy", graph)

    def test_bundle_is_deterministic_and_writes_lf_turtle(self) -> None:
        first = project_standards(self.model.world, self.model.constraints)
        second = project_standards(self.model.world, self.model.constraints)
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            paths = write_projection_bundle(first, directory, "cold-chain")
            self.assertTrue(paths.data_graph.is_file())
            self.assertTrue(paths.shapes_graph.is_file())
            self.assertNotIn(b"\r\n", paths.data_graph.read_bytes())
            self.assertIn("sosa:Observation", paths.data_graph.read_text("utf-8"))

    def test_generated_graphs_and_embedded_queries_parse(self) -> None:
        bundle = project_standards(self.model.world, self.model.constraints)
        data_graph = Graph().parse(data=bundle.data_graph, format="turtle")
        shapes_graph = Graph().parse(data=bundle.shapes_graph, format="turtle")
        self.assertGreater(len(data_graph), 0)
        self.assertGreater(len(shapes_graph), 0)
        sh = Namespace("http://www.w3.org/ns/shacl#")
        queries = tuple(shapes_graph.objects(None, sh.select))
        self.assertTrue(queries)
        for query in queries:
            prepareQuery(str(query))

    def test_invalid_iri_and_file_stem_are_rejected(self) -> None:
        bundle = project_standards(self.model.world, self.model.constraints)
        with self.assertRaisesRegex(ValueError, "Invalid base IRI"):
            project_standards(
                self.model.world,
                self.model.constraints,
                "not an iri",
            )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "file stem"):
                write_projection_bundle(bundle, directory, "../escape")


if __name__ == "__main__":
    unittest.main()
