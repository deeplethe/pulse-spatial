"""Executable PULSE versus standards-composition comparison."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, TypeVar

from ..compiler import load_pulse
from ..runtime import EventKind
from ..validation import geosparql_reference_functions


DEFAULT_ROOT = Path("experiments/composition/cold-chain")


@dataclass(frozen=True, slots=True)
class InstantRecord:
    kind: str
    subject: str
    region: str
    at: str


@dataclass(frozen=True, slots=True)
class SustainedRecord:
    kind: str
    subject: str
    region: str
    duration_seconds: float
    started_at: str
    effective_at: str
    emitted_at: str


@dataclass(frozen=True, slots=True)
class Outcome:
    final_state: str
    instantaneous: tuple[InstantRecord, ...]
    sustained: tuple[SustainedRecord, ...]


@dataclass(frozen=True, slots=True)
class Policy:
    subject: str
    region: str
    trigger: EventKind
    duration_seconds: float
    from_state: str
    to_state: str
    initial_state: str


@dataclass(frozen=True, slots=True)
class WorkflowSemantics:
    """Auditable switches used only by the mutation-sensitivity experiment.

    The default value is the reference workflow.  A mutant changes exactly one
    switch, allowing the complete workflow loop to be rerun with the same
    policy, trace, and outcome oracle.
    """

    timer_before_sample: bool = True
    cancel_inverse_crossing: bool = True
    require_start_guard: bool = True
    require_deadline_guard: bool = True
    inclusive_deadline: bool = True
    duration_scale: float = 1.0
    deadline_as_emission_time: bool = False
    transition_on_start: bool = False
    monitor_after_immediate_rule: bool = False

    def __post_init__(self) -> None:
        if self.duration_scale <= 0:
            raise ValueError("Workflow duration scale must be positive")


@dataclass(frozen=True, slots=True)
class PathExecution:
    outcome: Outcome
    validation: dict[str, object]


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _local_name(value: object) -> str:
    text = str(value)
    return text.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def _reference_workflow(
    policy: Policy,
    timestamps: tuple[datetime, ...],
    memberships: tuple[bool, ...],
    semantics: WorkflowSemantics = WorkflowSemantics(),
    immediate_to_state: str | None = None,
) -> Outcome:
    if len(timestamps) != len(memberships) or len(timestamps) < 2:
        raise ValueError("Workflow requires equally sized time and membership traces")
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("Workflow timestamps must be strictly increasing")

    state = policy.initial_state
    previous = memberships[0]
    pending_started_at: datetime | None = None
    instantaneous: list[InstantRecord] = []
    sustained: list[SustainedRecord] = []

    def emit_due(now: datetime) -> None:
        nonlocal state, pending_started_at
        effective_duration = policy.duration_seconds * semantics.duration_scale
        if pending_started_at is None:
            return
        effective_at = pending_started_at + timedelta(seconds=effective_duration)
        is_due = (
            effective_at <= now
            if semantics.inclusive_deadline
            else effective_at < now
        )
        if not is_due:
            return
        sustained.append(
            SustainedRecord(
                policy.trigger.value,
                policy.subject,
                policy.region,
                effective_duration,
                _iso(pending_started_at),
                _iso(effective_at),
                _iso(
                    effective_at
                    if semantics.deadline_as_emission_time
                    else now
                ),
            )
        )
        if not semantics.require_deadline_guard or state == policy.from_state:
            state = policy.to_state
        pending_started_at = None

    def apply_immediate(kind: EventKind) -> None:
        nonlocal state
        if (
            immediate_to_state is not None
            and kind is policy.trigger
            and state == policy.from_state
        ):
            state = immediate_to_state

    def reconcile_monitor(kind: EventKind, now: datetime) -> None:
        nonlocal state, pending_started_at
        if (
            semantics.cancel_inverse_crossing
            and pending_started_at is not None
            and kind is not policy.trigger
        ):
            pending_started_at = None
        if kind is policy.trigger and (
            not semantics.require_start_guard or state == policy.from_state
        ):
            pending_started_at = now
            if semantics.transition_on_start:
                state = policy.to_state

    for now, current in zip(timestamps[1:], memberships[1:]):
        if semantics.timer_before_sample:
            emit_due(now)

        if current == previous:
            if not semantics.timer_before_sample:
                emit_due(now)
            continue
        kind = EventKind.ENTERS if current else EventKind.LEAVES
        instantaneous.append(
            InstantRecord(
                kind.value,
                policy.subject,
                policy.region,
                _iso(now),
            )
        )
        if semantics.monitor_after_immediate_rule:
            apply_immediate(kind)
            reconcile_monitor(kind, now)
        else:
            reconcile_monitor(kind, now)
            apply_immediate(kind)
        previous = current
        if not semantics.timer_before_sample:
            emit_due(now)
    return Outcome(state, tuple(instantaneous), tuple(sustained))


def run_pulse(root: str | Path = DEFAULT_ROOT) -> PathExecution:
    model = load_pulse(Path(root) / "pulse" / "model.pulse")
    observations = tuple(
        sorted(model.world.observations, key=lambda item: item.observed_at)
    )
    if len(observations) < 2:
        raise ValueError("PULSE comparison model requires at least two observations")
    rule = model.rules[0]
    first = observations[0]
    if model.world.positions[first.subject] != first.value:
        raise ValueError("First PULSE observation must match asserted initial position")
    runtime = model.temporal_runtime(first.observed_at)
    instantaneous: list[InstantRecord] = []
    sustained: list[SustainedRecord] = []
    for observation in observations[1:]:
        result = runtime.move_at(
            observation.subject,
            observation.value,
            observation.observed_at,
        )
        instantaneous.extend(
            InstantRecord(
                event.kind.value,
                event.subject,
                event.region,
                _iso(observation.observed_at),
            )
            for event in result.instantaneous
        )
        sustained.extend(
            SustainedRecord(
                event.kind.value,
                event.subject,
                event.region,
                event.duration_seconds,
                _iso(event.started_at),
                _iso(event.effective_at),
                _iso(event.emitted_at),
            )
            for event in result.sustained
        )
    outcome = Outcome(
        runtime.world.states[rule.subject],
        tuple(instantaneous),
        tuple(sustained),
    )
    return PathExecution(
        outcome,
        {
            "compiled": True,
            "typedRules": len(model.rules),
            "observations": len(observations),
        },
    )


def run_semantic_web(root: str | Path = DEFAULT_ROOT) -> PathExecution:
    try:
        from pyshacl import validate
        from rdflib import Graph, Namespace
        from rdflib.namespace import RDF
    except ImportError as error:
        raise RuntimeError(
            "Semantic Web comparison requires the test dependencies"
        ) from error

    directory = Path(root) / "semantic-web"
    graph = Graph().parse(directory / "data.ttl")
    graph.parse(directory / "policy.ttl")
    shapes = Graph().parse(directory / "shapes.ttl")
    conforms, _, report_text = validate(graph, shacl_graph=shapes, advanced=True)
    if not conforms:
        raise ValueError(f"Semantic Web input fails SHACL:\n{report_text}")

    ex = Namespace("https://example.org/cold-chain/")
    time_ns = Namespace("http://www.w3.org/2006/time#")
    policy_node = next(graph.subjects(RDF.type, ex.GeofencePolicy))
    subject = graph.value(policy_node, ex.subject)
    region = graph.value(policy_node, ex.region)
    boundary_predicate = graph.value(policy_node, ex.boundaryPredicate)
    trigger = graph.value(policy_node, ex.trigger)
    from_state = graph.value(policy_node, ex.fromState)
    to_state = graph.value(policy_node, ex.toState)
    duration = graph.value(policy_node, time_ns.hasDuration)
    duration_value = graph.value(duration, time_ns.numericDuration)
    duration_unit = graph.value(duration, time_ns.unitType)
    initial_state = graph.value(subject, ex.initialState)
    required = (
        subject,
        region,
        boundary_predicate,
        trigger,
        from_state,
        to_state,
        duration,
        duration_value,
        duration_unit,
        initial_state,
    )
    if any(value is None for value in required):
        raise ValueError("Semantic Web policy is incomplete")
    if _local_name(boundary_predicate) != "sfIntersects":
        raise ValueError("Comparison requires GeoSPARQL sfIntersects")
    unit_seconds = {"unitMinute": 60.0}
    unit_name = _local_name(duration_unit)
    if unit_name not in unit_seconds:
        raise ValueError(f"Unsupported OWL-Time unit: {unit_name}")
    policy = Policy(
        _local_name(subject),
        _local_name(region),
        EventKind(_local_name(trigger)),
        float(duration_value) * unit_seconds[unit_name],
        _local_name(from_state),
        _local_name(to_state),
        _local_name(initial_state),
    )

    query = """
PREFIX ex: <https://example.org/cold-chain/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
SELECT ?time ?inside WHERE {
  ex:SustainedDeparturePolicy ex:subject ?subject ; ex:region ?region .
  ?region geo:hasGeometry/geo:asWKT ?regionWkt .
  ?observation a sosa:Observation ;
    sosa:hasFeatureOfInterest ?subject ;
    sosa:resultTime ?time ;
    sosa:hasResult/geo:asWKT ?pointWkt .
  BIND(geof:sfIntersects(?pointWkt, ?regionWkt) AS ?inside)
}
ORDER BY ?time
"""
    with geosparql_reference_functions():
        rows = tuple(graph.query(query))
    timestamps = tuple(_parse_time(str(row.time)) for row in rows)
    memberships = tuple(bool(row.inside.toPython()) for row in rows)
    outcome = _reference_workflow(policy, timestamps, memberships)
    return PathExecution(
        outcome,
        {
            "shaclConforms": True,
            "rdfTriples": len(graph),
            "shapeTriples": len(shapes),
            "orderedQueryRows": len(rows),
            "geoSparqlFunctionAdapter": "Shapely/GEOS reference adapter",
            "dateTimeLiteralAdapter": "explicit xsd:dateTimeStamp lexical parse",
        },
    )


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Moving Features timestamps must include a UTC offset")
    return parsed


def _validate_mf_json(value: dict[str, object]) -> tuple[
    str,
    tuple[tuple[float, float], ...],
    tuple[datetime, ...],
    str,
]:
    if value.get("type") != "Feature" or not value.get("id"):
        raise ValueError("MF-JSON Prism must be an identified Feature")
    geometry = value.get("temporalGeometry")
    properties = value.get("properties")
    if not isinstance(geometry, dict) or geometry.get("type") != "MovingPoint":
        raise ValueError("MF-JSON Prism temporalGeometry must be a MovingPoint")
    if geometry.get("interpolation", "Linear") != "Step":
        raise ValueError("Comparison MF-JSON Prism requires Step interpolation")
    if not isinstance(properties, dict):
        raise ValueError("MF-JSON Prism properties are required")
    coordinate_values = geometry.get("coordinates")
    datetime_values = geometry.get("datetimes")
    if not isinstance(coordinate_values, list) or len(coordinate_values) < 2:
        raise ValueError("MF-JSON Prism requires at least two coordinates")
    if not isinstance(datetime_values, list):
        raise ValueError("MF-JSON Prism datetimes are required")
    coordinates = tuple(
        (float(coordinate[0]), float(coordinate[1]))
        for coordinate in coordinate_values
        if isinstance(coordinate, list) and len(coordinate) >= 2
    )
    timestamps = tuple(_parse_time(str(item)) for item in datetime_values)
    if len(coordinates) != len(coordinate_values):
        raise ValueError("MF-JSON Prism contains an invalid coordinate")
    if len(coordinates) != len(timestamps):
        raise ValueError("MF-JSON coordinates and datetimes must have equal length")
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("MF-JSON datetimes must be strictly increasing")
    initial_state = properties.get("initialState")
    if not isinstance(initial_state, str):
        raise ValueError("Comparison moving feature requires initialState")
    return str(value["id"]), coordinates, timestamps, initial_state


def run_moving_features(root: str | Path = DEFAULT_ROOT) -> PathExecution:
    try:
        from shapely import Point as ReferencePoint
        from shapely import Polygon as ReferencePolygon
        from shapely import covers
    except ImportError as error:
        raise RuntimeError(
            "Moving Features comparison requires the test dependencies"
        ) from error

    directory = Path(root) / "moving-features"
    trajectory = json.loads(
        (directory / "moving-feature.json").read_text("utf-8")
    )
    policy_value = json.loads((directory / "policy.json").read_text("utf-8"))
    if not isinstance(trajectory, dict) or not isinstance(policy_value, dict):
        raise ValueError("Moving Features comparison inputs must be JSON objects")
    subject, coordinates, timestamps, initial_state = _validate_mf_json(trajectory)
    region_value = policy_value.get("region")
    if not isinstance(region_value, dict) or region_value.get("type") != "Polygon":
        raise ValueError("Moving Features policy requires a Polygon region")
    shells = region_value.get("coordinates")
    if not isinstance(shells, list) or not shells:
        raise ValueError("Moving Features policy Polygon requires a shell")
    polygon = ReferencePolygon(shells[0])
    memberships = tuple(
        bool(covers(polygon, ReferencePoint(x, y))) for x, y in coordinates
    )
    if policy_value.get("subject") != subject:
        raise ValueError("Moving Features policy subject does not match trajectory")
    if policy_value.get("boundaryPolicy") != "coveredBy":
        raise ValueError("Comparison requires coveredBy boundary semantics")
    policy = Policy(
        subject,
        str(policy_value["regionName"]),
        EventKind(str(policy_value["trigger"])),
        float(policy_value["minimumDurationSeconds"]),
        str(policy_value["fromState"]),
        str(policy_value["toState"]),
        initial_state,
    )
    outcome = _reference_workflow(policy, timestamps, memberships)
    return PathExecution(
        outcome,
        {
            "mfJsonPrismSubsetValid": True,
            "checkedRequirements": (
                "local checks corresponding to portions of OGC 19-045r3 "
                "Prism requirements 2.4-2.8 and 2.12; not a complete "
                "conformance suite"
            ),
            "coordinates": len(coordinates),
            "timestamps": len(timestamps),
            "policyIsNonStandardWorkflowConfiguration": True,
        },
    )


def _expected_outcome() -> Outcome:
    return Outcome(
        "AtRisk",
        (
            InstantRecord(
                "leaves",
                "shipment_102",
                "ColdZone",
                "2026-07-19T08:05:00Z",
            ),
            InstantRecord(
                "enters",
                "shipment_102",
                "ColdZone",
                "2026-07-19T08:12:00Z",
            ),
            InstantRecord(
                "leaves",
                "shipment_102",
                "ColdZone",
                "2026-07-19T08:20:00Z",
            ),
        ),
        (
            SustainedRecord(
                "leaves",
                "shipment_102",
                "ColdZone",
                600.0,
                "2026-07-19T08:20:00Z",
                "2026-07-19T08:30:00Z",
                "2026-07-19T08:31:00Z",
            ),
        ),
    )


def _substantive_lines(path: Path) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        count += 1
    return count


def _artifact_metrics(
    root: Path,
    approach: str,
    relative_paths: tuple[str, ...],
    components: tuple[str, ...],
    vocabularies: tuple[str, ...],
) -> dict[str, object]:
    paths = tuple(root / approach / relative for relative in relative_paths)
    return {
        "inputFiles": [path.relative_to(root).as_posix() for path in paths],
        "inputFileCount": len(paths),
        "inputBytes": sum(path.stat().st_size for path in paths),
        "substantiveLines": sum(_substantive_lines(path) for path in paths),
        "executionComponents": list(components),
        "executionComponentCount": len(components),
        "declaredStandardsOrVocabularies": list(vocabularies),
    }


_T = TypeVar("_T")


def _timed(function: Callable[[], _T], repetitions: int) -> tuple[_T, list[float]]:
    samples: list[float] = []
    result: _T | None = None
    for _ in range(repetitions):
        started = time.perf_counter()
        result = function()
        samples.append(time.perf_counter() - started)
    assert result is not None
    return result, samples


def run_comparison(
    root: str | Path = DEFAULT_ROOT,
    *,
    repetitions: int = 3,
) -> dict[str, object]:
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    base = Path(root)
    functions: dict[str, Callable[[str | Path], PathExecution]] = {
        "pulse": run_pulse,
        "semanticWebComposition": run_semantic_web,
        "movingFeaturesComposition": run_moving_features,
    }
    executions: dict[str, PathExecution] = {}
    timings: dict[str, object] = {}
    for name, function in functions.items():
        function(base)
        execution, samples = _timed(lambda f=function: f(base), repetitions)
        executions[name] = execution
        timings[name] = {
            "seconds": samples,
            "medianSeconds": statistics.median(samples),
        }
    expected = _expected_outcome()
    outcome_matches = {
        name: execution.outcome == expected
        for name, execution in executions.items()
    }
    all_equivalent = len({execution.outcome for execution in executions.values()}) == 1
    metrics = {
        "pulse": _artifact_metrics(
            base,
            "pulse",
            ("model.pulse",),
            (
                "PULSE parser/compiler",
                "PULSE geometry kernel",
                "PULSE temporal runtime",
            ),
            ("PULSE",),
        ),
        "semanticWebComposition": _artifact_metrics(
            base,
            "semantic-web",
            ("data.ttl", "policy.ttl", "shapes.ttl"),
            (
                "RDF parser and SPARQL engine",
                "SHACL engine",
                "GeoSPARQL function adapter",
                "dateTime literal adapter",
                "duration workflow",
            ),
            ("RDF", "SOSA", "GeoSPARQL", "OWL-Time", "SHACL", "XSD"),
        ),
        "movingFeaturesComposition": _artifact_metrics(
            base,
            "moving-features",
            ("moving-feature.json", "policy.json"),
            (
                "MF-JSON Prism subset validator",
                "geometry engine",
                "duration workflow",
            ),
            ("OGC MF-JSON Prism", "GeoJSON", "custom policy JSON"),
        ),
    }
    return {
        "experiment": "cold-chain-composition-comparison-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "task": {
            "description": (
                "A shipment briefly leaves and re-enters a geofence, then "
                "leaves for at least ten minutes and changes Safe to AtRisk."
            ),
            "clock": "discrete sample-and-hold; due timers precede same-time moves",
            "boundaryPolicy": "coveredBy",
        },
        "standardRoles": {
            "GeoSPARQL": "RDF spatial representation and topological query",
            "SHACL": "RDF structural validation",
            "OWL-Time": "duration and instant description",
            "MF-JSON": "trajectory exchange",
            "workflow": (
                "required in both composed baselines for timer cancellation "
                "and state transition"
            ),
        },
        "expectedOutcome": asdict(expected),
        "paths": {
            name: {
                "outcome": asdict(execution.outcome),
                "matchesExpected": outcome_matches[name],
                "validation": execution.validation,
            }
            for name, execution in executions.items()
        },
        "equivalence": {
            "allPathsMatchExpected": all(outcome_matches.values()),
            "allPathOutcomesEquivalent": all_equivalent,
        },
        "descriptiveCompositionMetrics": metrics,
        "timing": {
            "scope": (
                "warm-process local end-to-end microbenchmark including parse "
                "and validation; one untimed warm-up per path"
            ),
            "repetitions": repetitions,
            "paths": timings,
        },
        "claimBoundary": (
            "Executable outcome equivalence and descriptive artifact composition "
            "for one frozen task; not standards conformance, maintainability, "
            "usability, or general productivity evidence."
        ),
    }


def render_markdown(result: dict[str, object]) -> str:
    equivalence = result["equivalence"]
    paths = result["paths"]
    metrics = result["descriptiveCompositionMetrics"]
    timing = result["timing"]
    assert isinstance(equivalence, dict)
    assert isinstance(paths, dict)
    assert isinstance(metrics, dict)
    assert isinstance(timing, dict)
    timing_paths = timing["paths"]
    assert isinstance(timing_paths, dict)
    lines = [
        "# Cold-chain composition comparison",
        "",
        "## Outcome equivalence",
        "",
        f"- All paths match expected: **{equivalence['allPathsMatchExpected']}**",
        "- All path outcomes equivalent: "
        f"**{equivalence['allPathOutcomesEquivalent']}**",
        "",
        "| Path | Expected outcome | Input files | Substantive lines | "
        "Components | Median |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("pulse", "semanticWebComposition", "movingFeaturesComposition"):
        path = paths[name]
        metric = metrics[name]
        path_timing = timing_paths[name]
        lines.append(
            f"| {name} | {path['matchesExpected']} | "
            f"{metric['inputFileCount']} | {metric['substantiveLines']} | "
            f"{metric['executionComponentCount']} | "
            f"{path_timing['medianSeconds']:.6f} s |"
        )
    lines.extend(
        (
            "",
            "Metrics are descriptive properties of these checked-in artifacts;",
            "they are not usability or maintainability measurements.",
            "",
            "## Claim boundary",
            "",
            str(result["claimBoundary"]),
            "",
        )
    )
    return "\n".join(lines)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-composition",
        description="Compare three executable encodings of one cold-chain task.",
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-equivalence", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_comparison(arguments.root, repetitions=arguments.repetitions)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    equivalence = result["equivalence"]
    assert isinstance(equivalence, dict)
    if arguments.require_equivalence and not all(equivalence.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
