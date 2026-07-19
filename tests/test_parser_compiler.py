import unittest
from datetime import datetime, timedelta
from pathlib import Path

from pulse_spatial import (
    EventKind,
    Point,
    PulseModelError,
    PulseSyntaxError,
    compile_pulse,
    load_pulse,
    parse_pulse,
)


EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "cold_chain_geofence.pulse"
)
TEMPORAL_EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "cold_chain_spatiotemporal.pulse"
)


class ParserCompilerTests(unittest.TestCase):
    def test_example_parses_to_typed_document(self) -> None:
        document = parse_pulse(EXAMPLE.read_text(encoding="utf-8"), str(EXAMPLE))
        self.assertEqual(document.name, "ColdChainSpatial")
        self.assertEqual(document.version, "0.1")
        self.assertEqual(len(document.entities), 1)
        self.assertEqual(document.entities[0].properties[0].type_name, "Point")
        self.assertEqual(document.scenarios[0].run_for.unit, "min")

    def test_example_compiles_without_modal_conflation(self) -> None:
        model = load_pulse(EXAMPLE)
        asserted = model.world.positions["batch_102"]
        observed = model.world.observations[0].value
        self.assertNotEqual(asserted, observed)
        self.assertEqual(model.validate(), ())
        self.assertEqual(len(model.rules), 1)

    def test_scenario_executes_and_preserves_source_world(self) -> None:
        model = load_pulse(EXAMPLE)
        report = model.run_scenario("EmergencyReroute")
        self.assertEqual(report.horizon_seconds, 1200)
        self.assertEqual(report.result.events[0].kind, EventKind.LEAVES)
        self.assertEqual(
            tuple(answer.value for answer in report.answers),
            (False, "AtRisk"),
        )
        self.assertEqual(model.world.states["batch_102"], "Safe")
        self.assertEqual(model.world.positions["batch_102"].x, 121.5)

    def test_duration_qualified_process_compiles_and_executes(self) -> None:
        model = load_pulse(TEMPORAL_EXAMPLE)
        self.assertEqual(model.rules[0].minimum_duration_seconds, 600)
        with self.assertRaisesRegex(ValueError, "TemporalSpatialRuntime"):
            model.runtime()

        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        runtime = model.temporal_runtime(started)
        runtime.move_at("shipment_102", Point(117, 40), started)
        self.assertEqual(
            runtime.advance_to(started + timedelta(minutes=9)),
            (),
        )
        events = runtime.advance_to(started + timedelta(minutes=10))
        self.assertEqual(len(events), 1)
        self.assertEqual(runtime.world.states["shipment_102"], "AtRisk")

    def test_syntax_error_includes_source_location(self) -> None:
        with self.assertRaisesRegex(PulseSyntaxError, r"broken\.pulse:2:1"):
            parse_pulse('model Broken version "0.1"\n@', "broken.pulse")

    def test_unknown_crs_is_rejected_semantically(self) -> None:
        source = """
model Broken version "0.1"
crs Known = "https://example.org/crs/known"
region Zone crs Missing = polygon [[0, 0], [1, 0], [0, 1], [0, 0]]
"""
        with self.assertRaisesRegex(PulseModelError, "unknown CRS 'Missing'"):
            compile_pulse(source)

    def test_unsupported_scalar_type_is_not_silently_accepted(self) -> None:
        source = """
model Broken version "0.1"
crs WGS84 = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
entity Asset { property label: UnresolvedDatatype }
instance asset_1: Asset { label = "pump" }
"""
        with self.assertRaisesRegex(PulseModelError, "unsupported scalar type"):
            compile_pulse(source)


if __name__ == "__main__":
    unittest.main()
