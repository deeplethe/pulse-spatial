import json
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
from pulse_spatial.__main__ import _json_value


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
PAPER_EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "paper_cold_chain_st.pulse"
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
        self.assertEqual(
            report.completed_at - report.started_at,
            timedelta(minutes=20),
        )
        self.assertEqual(report.result.events[0].kind, EventKind.LEAVES)
        self.assertEqual(
            tuple(answer.value for answer in report.answers),
            (False, "AtRisk"),
        )
        self.assertEqual(model.world.states["batch_102"], "Safe")
        self.assertEqual(model.world.positions["batch_102"].x, 121.5)

    def test_paper_listing_executes_duration_scenario_end_to_end(self) -> None:
        model = load_pulse(PAPER_EXAMPLE)
        source_position = model.world.positions["batch"]
        source_state = model.world.states["batch"]

        report = model.run_scenario("Reroute")

        self.assertEqual(
            report.started_at,
            datetime.fromisoformat("2026-07-19T08:20:00+00:00"),
        )
        self.assertEqual(
            report.completed_at,
            datetime.fromisoformat("2026-07-19T08:40:00+00:00"),
        )
        self.assertEqual(report.horizon_seconds, 1200)
        self.assertEqual(len(report.result.events), 2)
        # CLI output must remain JSON-serializable when events carry datetimes.
        json.dumps(_json_value(report.result.events))
        self.assertEqual(report.result.events[0].kind, EventKind.LEAVES)
        self.assertEqual(
            report.result.events[1].effective_at,
            report.started_at + timedelta(minutes=10),
        )
        self.assertEqual(
            tuple(answer.value for answer in report.answers),
            (False, "AtRisk"),
        )
        self.assertEqual(model.world.positions["batch"], source_position)
        self.assertEqual(model.world.states["batch"], source_state)

        earlier = model.run_scenario(
            "Reroute",
            datetime.fromisoformat("2026-07-19T08:00:00+00:00"),
        )
        self.assertEqual(earlier.started_at, report.started_at)

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

    def test_compiled_runner_rejects_undeclared_subject_atomically(self) -> None:
        model = load_pulse(TEMPORAL_EXAMPLE)
        started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
        runtime = model.temporal_runtime(started)
        positions_before = dict(runtime.world.positions)

        with self.assertRaisesRegex(ValueError, "Unknown declared subject"):
            runtime.move_at("undeclared", Point(117, 40), started)

        self.assertEqual(runtime.world.positions, positions_before)
        self.assertEqual(runtime.current_time, started)
        self.assertEqual(runtime.pending_count, 0)

    def test_scenario_can_clone_live_clock_state_and_pending_monitors(self) -> None:
        model = load_pulse(PAPER_EXAMPLE)
        started = datetime.fromisoformat("2026-07-19T08:20:00+00:00")
        runtime = model.temporal_runtime(started)
        source_target = Point(121.512, 31.201)
        runtime.move_at("batch", source_target, started)
        self.assertEqual(runtime.pending_count, 1)
        self.assertEqual(runtime.world.states["batch"], "Safe")

        report = model.run_scenario(
            "Reroute",
            datetime.fromisoformat("2026-07-19T08:00:00+00:00"),
            source_runtime=runtime,
        )

        self.assertEqual(report.started_at, started)
        self.assertEqual(len(report.result.events), 1)
        self.assertEqual(report.result.events[0].effective_at, started + timedelta(minutes=10))
        self.assertEqual(report.result.world.states["batch"], "AtRisk")
        self.assertEqual(runtime.current_time, started)
        self.assertEqual(runtime.pending_count, 1)
        self.assertEqual(runtime.world.positions["batch"], source_target)
        self.assertEqual(runtime.world.states["batch"], "Safe")

    def test_parameterized_monitor_is_grounded_per_subject_and_ties_follow_declaration_order(
        self,
    ) -> None:
        source = """
model MultiAsset version "0.1"
crs C = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
region Z crs C = polygon [[0,0], [10,0], [10,10], [0,10], [0,0]]
entity Shipment {
  property position: Point crs C
  state condition oneof [Safe, AtRisk]
}
instance zeta: Shipment { position = point(5,5) condition = Safe }
instance alpha: Shipment { position = point(5,5) condition = Safe }
process SustainedDeparture(s: Shipment) {
  when leaves(s.position,Z) for 1 min
  changes s.condition: Safe -> AtRisk
}
"""
        model = compile_pulse(source)
        self.assertEqual(
            tuple(rule.name for rule in model.rules),
            ("SustainedDeparture@zeta", "SustainedDeparture@alpha"),
        )

        started = datetime.fromisoformat("2026-07-21T00:00:00+00:00")
        runtime = model.temporal_runtime(started)
        runtime.move_at("zeta", Point(12, 5), started)
        runtime.move_at("alpha", Point(12, 5), started)
        self.assertEqual(runtime.pending_count, 2)

        events = runtime.advance_to(started + timedelta(minutes=1))
        self.assertEqual(
            tuple(event.specification for event in events),
            ("SustainedDeparture@zeta", "SustainedDeparture@alpha"),
        )

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
