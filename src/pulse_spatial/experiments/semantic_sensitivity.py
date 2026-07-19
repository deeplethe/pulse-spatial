"""Sensitivity checks for PULSE's explicit modal and clock policies."""

from __future__ import annotations

import argparse
import json
import platform
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..geometry import CRS84, Point, Polygon, covered_by, within
from ..model import LocationObservation, SpatialWorld
from ..runtime import (
    EventKind,
    GeofenceRule,
    SpatialRuntime,
    SustainedEventSpec,
    TemporalSpatialRuntime,
)


@dataclass(frozen=True, slots=True)
class SensitivityCheck:
    name: str
    contract: str
    pulse_outcome: str
    alternative: str
    alternative_outcome: str
    distinguishable: bool


def _zone() -> Polygon:
    return Polygon.from_xy(((0, 0), (10, 0), (10, 10), (0, 10)), CRS84)


def _world() -> SpatialWorld:
    return SpatialWorld(
        regions={"Zone": _zone()},
        positions={"asset": Point(5, 5, CRS84)},
        states={"asset": "Safe"},
    )


def _rule(*, duration_seconds: float | None = None) -> GeofenceRule:
    return GeofenceRule(
        "Departure",
        EventKind.LEAVES,
        "asset",
        "Zone",
        "Safe",
        "AtRisk",
        duration_seconds,
    )


def _boundary_policy() -> SensitivityCheck:
    world = _world()
    source = world.positions["asset"]
    target = Point(0, 5, CRS84)
    events = SpatialRuntime(world).move("asset", target)
    strict_event = within(source, world.regions["Zone"]) and not within(
        target, world.regions["Zone"]
    )
    return SensitivityCheck(
        "boundary-inclusion",
        "coveredBy treats a shell point as inside",
        f"sampled events={len(events)}",
        "strict within excludes the shell",
        f"sampled leaves={int(strict_event)}",
        not events and strict_event,
    )


def _observation_non_overwrite() -> SensitivityCheck:
    world = _world()
    observation = LocationObservation(
        "asset",
        Point(12, 5, CRS84),
        datetime.fromisoformat("2026-07-19T08:05:00+00:00"),
        "sensor-1",
    )
    world.record_observation(observation)
    pulse_inside = covered_by(world.positions["asset"], world.regions["Zone"])
    overwrite_inside = covered_by(observation.value, world.regions["Zone"])
    return SensitivityCheck(
        "observation-non-overwrite",
        "record(o) appends evidence and preserves asserted position",
        f"assertedInside={str(pulse_inside).lower()}",
        "sensor value silently replaces the assertion",
        f"assertedInside={str(overwrite_inside).lower()}",
        pulse_inside != overwrite_inside,
    )


def _scenario_isolation() -> SensitivityCheck:
    world = _world()
    scenario = SpatialRuntime(world, (_rule(),)).scenario(
        (("asset", Point(12, 5, CRS84)),)
    )
    shared = _world()
    SpatialRuntime(shared, (_rule(),)).move("asset", Point(12, 5, CRS84))
    pulse = f"source={world.states['asset']},scenario={scenario.world.states['asset']}"
    alternative = f"source={shared.states['asset']}"
    return SensitivityCheck(
        "scenario-isolation",
        "assumptions execute on a cloned world",
        pulse,
        "assumptions execute on the source world",
        alternative,
        world.states["asset"] != shared.states["asset"],
    )


def _inverse_cancellation() -> SensitivityCheck:
    started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
    runtime = TemporalSpatialRuntime(
        _world(),
        started,
        sustained_events=(
            SustainedEventSpec(
                "OutsideTenMinutes",
                EventKind.LEAVES,
                "asset",
                "Zone",
                600,
            ),
        ),
    )
    runtime.move_at("asset", Point(12, 5, CRS84), started)
    runtime.move_at("asset", Point(5, 5, CRS84), started + timedelta(minutes=9))
    events = runtime.advance_to(started + timedelta(minutes=10))
    no_cancel_events = 1
    return SensitivityCheck(
        "inverse-cancellation",
        "inverse sampled entry before the deadline cancels a leave monitor",
        f"sustained events={len(events)}",
        "pending monitors are never cancelled",
        f"sustained events={no_cancel_events}",
        len(events) != no_cancel_events,
    )


def _deadline_ordering() -> SensitivityCheck:
    started = datetime.fromisoformat("2026-07-19T08:00:00+00:00")
    runtime = TemporalSpatialRuntime(
        _world(),
        started,
        sustained_events=(
            SustainedEventSpec(
                "OutsideTenMinutes",
                EventKind.LEAVES,
                "asset",
                "Zone",
                600,
            ),
        ),
    )
    runtime.move_at("asset", Point(12, 5, CRS84), started)
    result = runtime.move_at(
        "asset", Point(5, 5, CRS84), started + timedelta(minutes=10)
    )
    move_first_events = 0
    return SensitivityCheck(
        "deadline-ordering",
        "due timers fire before a move at the same timestamp",
        f"sustained events={len(result.sustained)}",
        "same-time move cancels before timers are exposed",
        f"sustained events={move_first_events}",
        len(result.sustained) != move_first_events,
    )


def _sampling_policy() -> SensitivityCheck:
    try:
        from shapely import LineString
        from shapely import Polygon as ReferencePolygon
    except ImportError as error:
        raise RuntimeError("Shapely is required for sensitivity checks") from error

    world = SpatialWorld(
        regions={"Zone": _zone()},
        positions={"asset": Point(-1, 5, CRS84)},
    )
    events = SpatialRuntime(world).move("asset", Point(11, 5, CRS84))
    line = LineString(((-1, 5), (11, 5)))
    polygon = ReferencePolygon(((0, 0), (10, 0), (10, 10), (0, 10)))
    intersections = line.intersection(polygon.boundary)
    crossing_points = len(getattr(intersections, "geoms", (intersections,)))
    return SensitivityCheck(
        "sample-and-hold",
        "sampled entry/exit depends only on consecutive memberships",
        f"sampled events={len(events)}",
        "linear segment interpolation detects intervening boundary contacts",
        f"boundary contacts={crossing_points}",
        not events and crossing_points == 2,
    )


def run_sensitivity() -> dict[str, object]:
    try:
        import shapely
    except ImportError as error:
        raise RuntimeError("Shapely is required for sensitivity checks") from error

    checks = (
        _boundary_policy(),
        _observation_non_overwrite(),
        _scenario_isolation(),
        _inverse_cancellation(),
        _deadline_ordering(),
        _sampling_policy(),
    )
    distinguished = sum(check.distinguishable for check in checks)
    return {
        "experiment": "pulse-semantic-policy-sensitivity-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "summary": {
            "policies": len(checks),
            "distinguishedAlternatives": distinguished,
            "allAlternativesChangeObservableOutcome": distinguished == len(checks),
        },
        "checks": [asdict(check) for check in checks],
        "claimBoundary": (
            "Constructed sensitivity cases show that six declared policies change "
            "observable traces or modal state. They are mutation-adequacy checks, "
            "not evidence that each PULSE policy is universally preferable."
        ),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    checks = result["checks"]
    assert isinstance(summary, dict)
    assert isinstance(checks, list)
    lines = [
        "# Semantic policy sensitivity",
        "",
        f"- Policies checked: {summary['policies']}",
        "- Alternatives changing an observable outcome: "
        f"{summary['distinguishedAlternatives']}",
        "",
        "| Policy | PULSE | Alternative | Distinguishable |",
        "|---|---|---|---:|",
    ]
    for check in checks:
        lines.append(
            f"| {check['name']} | {check['pulse_outcome']} | "
            f"{check['alternative_outcome']} | {check['distinguishable']} |"
        )
    lines.extend(("", "## Claim boundary", "", str(result["claimBoundary"]), ""))
    return "\n".join(lines)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-semantic-sensitivity",
        description="Run PULSE semantic policy sensitivity checks.",
    )
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-all-distinguished", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_sensitivity()
    except RuntimeError as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    summary = result["summary"]
    assert isinstance(summary, dict)
    if (
        arguments.require_all_distinguished
        and not summary["allAlternativesChangeObservableOutcome"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
