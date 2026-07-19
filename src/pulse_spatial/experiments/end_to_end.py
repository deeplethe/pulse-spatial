"""End-to-end real-track exercise of all four PULSE semantic modes."""

from __future__ import annotations

import argparse
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

from ..geometry import CRS84, Point
from ..model import GeofenceConstraint, LocationObservation, SpatialWorld
from ..projection import project_standards
from ..runtime import EventKind, GeofenceRule, SpatialRuntime, TemporalSpatialRuntime
from ..validation import validate_projection_parity
from .ibtracs import SOURCE_DOI, SOURCE_URL, _sha256, load_ibtracs
from .spatiotemporal import _regions


DEFAULT_TRACK = "2023251N16334"
DEFAULT_REGION = "NorthAtlanticStudyZone"


def run_end_to_end(
    dataset_path: str | Path,
    *,
    track_id: str = DEFAULT_TRACK,
    region_name: str = DEFAULT_REGION,
) -> dict[str, object]:
    """Replay one frozen track through evidence, execution, scenario, and RDF."""

    path = Path(dataset_path)
    dataset = load_ibtracs(path)
    tracks = {track.sid: track for track in dataset.tracks}
    if track_id not in tracks:
        raise ValueError(f"Track {track_id!r} is absent from the dataset")
    regions = _regions()
    if region_name not in regions:
        raise ValueError(f"Region {region_name!r} is not defined")
    track = tracks[track_id]
    if len(track.points) < 2:
        raise ValueError("End-to-end track requires at least two points")

    first = track.points[0]
    world = SpatialWorld(
        regions={region_name: regions[region_name]},
        positions={track.sid: Point(first.longitude, first.latitude, CRS84)},
        states={track.sid: "Safe"},
    )
    constraint = GeofenceConstraint(
        "RemainInStudyZone",
        track.sid,
        region_name,
        predicate="coveredBy",
        while_state="Safe",
    )
    rule = GeofenceRule(
        "SustainedDeparture",
        EventKind.LEAVES,
        track.sid,
        region_name,
        "Safe",
        "AtRisk",
        minimum_duration_seconds=6 * 3600,
    )
    runtime = TemporalSpatialRuntime(world, first.observed_at, rules=(rule,))

    observations_preserving_assertions = 0
    instantaneous_events = []
    sustained_events = []
    violating_steps = 0
    state_changes = 0

    for index, point in enumerate(track.points):
        previous_position = world.positions[track.sid]
        observation = LocationObservation(
            track.sid,
            Point(point.longitude, point.latitude, CRS84),
            point.observed_at,
            "IBTrACS-main-track",
            property_name="position",
        )
        world.record_observation(observation)
        if world.positions[track.sid] == previous_position:
            observations_preserving_assertions += 1
        if index == 0:
            continue

        previous_state = world.states[track.sid]
        step = runtime.move_at(track.sid, observation.value, observation.observed_at)
        if world.states[track.sid] != previous_state:
            state_changes += 1
        instantaneous_events.extend(step.instantaneous)
        sustained_events.extend(step.sustained)
        if world.validate((constraint,)):
            violating_steps += 1

    source_position = world.positions[track.sid]
    source_state = world.states[track.sid]
    scenario_target = Point(first.longitude, first.latitude, CRS84)
    scenario = SpatialRuntime(world).scenario(
        ((track.sid, scenario_target),)
    )
    scenario_source_preserved = (
        world.positions[track.sid] == source_position
        and world.states[track.sid] == source_state
    )

    validation = validate_projection_parity(world, (constraint,))
    bundle = project_standards(world, (constraint,))
    try:
        import pyshacl
        import rdflib
        import shapely
        from rdflib import Graph
    except ImportError as error:
        raise RuntimeError(
            "End-to-end validation requires the optional test dependencies"
        ) from error
    data_triples = len(Graph().parse(data=bundle.data_graph, format="turtle"))
    shape_triples = len(Graph().parse(data=bundle.shapes_graph, format="turtle"))

    all_modes_exercised = (
        len(world.observations) == len(track.points)
        and observations_preserving_assertions == len(track.points)
        and bool(instantaneous_events)
        and bool(sustained_events)
        and state_changes == 1
        and violating_steps > 0
        and scenario_source_preserved
        and validation.matches
    )
    return {
        "experiment": "ibtracs-four-mode-end-to-end-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "dataset": {
            "name": "NOAA IBTrACS v04r01 normalized main-track snapshot",
            "doi": SOURCE_DOI,
            "sourceUrl": SOURCE_URL,
            "path": path.as_posix(),
            "sha256": _sha256(path),
            "track": track.sid,
            "trackName": track.name,
            "points": len(track.points),
            "transitions": len(track.points) - 1,
        },
        "policy": {
            "region": region_name,
            "trigger": "sampled leaves for 6 hours",
            "transition": "Safe -> AtRisk",
            "acceptanceBoundary": (
                "record_observation appends evidence; the runner separately "
                "accepts a sample through move_at to update asserted position"
            ),
        },
        "modalExecution": {
            "assertedMoves": len(track.points) - 1,
            "observations": len(world.observations),
            "observationNonOverwriteChecks": observations_preserving_assertions,
            "normativeViolatingStepsBeforeGuardDeactivation": violating_steps,
            "scenarioSourcePreserved": scenario_source_preserved,
            "scenarioEvents": len(scenario.events),
        },
        "trace": {
            "instantaneousEvents": len(instantaneous_events),
            "sustainedEvents": len(sustained_events),
            "stateChanges": state_changes,
            "finalState": world.states[track.sid],
        },
        "projection": {
            "dataTriples": data_triples,
            "shapeTriples": shape_triples,
            "internalConforms": validation.internal_conforms,
            "projectedConforms": validation.projected_conforms,
            "crossViewMatches": validation.matches,
        },
        "summary": {
            "allFourModesExercised": all_modes_exercised,
            "allChecksPass": all_modes_exercised,
        },
        "claimBoundary": (
            "One frozen real trajectory exercises the asserted, observed, "
            "normative, and hypothetical contracts together with duration "
            "execution and RDF/SHACL projection parity. It is an integration "
            "case, not an industrial deployment or productivity study."
        ),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "rdflib": rdflib.__version__,
            "pyshacl": pyshacl.__version__,
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    dataset = result["dataset"]
    modal = result["modalExecution"]
    trace = result["trace"]
    projection = result["projection"]
    summary = result["summary"]
    assert all(
        isinstance(value, dict)
        for value in (dataset, modal, trace, projection, summary)
    )
    return "\n".join(
        (
            "# IBTrACS four-mode end-to-end result",
            "",
            f"- Track: {dataset['track']} ({dataset['points']} points)",
            f"- Asserted moves: {modal['assertedMoves']}",
            f"- Evidence observations: {modal['observations']}",
            "- Observation non-overwrite checks: "
            f"{modal['observationNonOverwriteChecks']}",
            f"- Instantaneous/sustained events: {trace['instantaneousEvents']} / "
            f"{trace['sustainedEvents']}",
            f"- State changes/final state: {trace['stateChanges']} / {trace['finalState']}",
            "- Normative violating steps before guard deactivation: "
            f"{modal['normativeViolatingStepsBeforeGuardDeactivation']}",
            f"- Scenario source preserved: {modal['scenarioSourcePreserved']}",
            f"- Projection triples (data/shapes): {projection['dataTriples']} / "
            f"{projection['shapeTriples']}",
            f"- Internal/projected validation match: {projection['crossViewMatches']}",
            f"- All checks pass: **{summary['allChecksPass']}**",
            "",
            "## Claim boundary",
            "",
            str(result["claimBoundary"]),
            "",
        )
    )


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-end-to-end",
        description="Run the real-track four-mode end-to-end experiment.",
    )
    parser.add_argument(
        "--data",
        default=(
            "experiments/ibtracs/snapshots/"
            "ibtracs-last3years-main-2026-07-16.csv"
        ),
    )
    parser.add_argument("--track", default=DEFAULT_TRACK)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-all-checks", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_end_to_end(
            arguments.data,
            track_id=arguments.track,
            region_name=arguments.region,
        )
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    summary = result["summary"]
    assert isinstance(summary, dict)
    if arguments.require_all_checks and not summary["allChecksPass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
