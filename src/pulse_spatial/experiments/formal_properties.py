"""Bounded exhaustive checks supporting the PULSE core metatheory."""

from __future__ import annotations

import argparse
import itertools
import json
import platform
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..geometry import CRS84, Point, Polygon
from ..model import LocationObservation, SpatialWorld
from ..runtime import EventKind, GeofenceRule, SpatialRuntime, TemporalSpatialRuntime


BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
STATE_DOMAIN = frozenset({"Safe", "Inside", "Outside"})
POSITIONS = (
    ("west", Point(-1.0, 5.0)),
    ("boundary", Point(0.0, 5.0)),
    ("inside", Point(5.0, 5.0)),
    ("east", Point(11.0, 5.0)),
)


def _world(initial: Point) -> SpatialWorld:
    return SpatialWorld(
        regions={"Zone": Polygon.from_xy(((0, 0), (10, 0), (10, 10), (0, 10)))},
        positions={"asset": initial},
        states={"asset": "Safe"},
    )


def _rules() -> tuple[GeofenceRule, ...]:
    return (
        GeofenceRule(
            "enter-zone",
            EventKind.ENTERS,
            "asset",
            "Zone",
            "Safe",
            "Inside",
        ),
        GeofenceRule(
            "sustained-leave",
            EventKind.LEAVES,
            "asset",
            "Zone",
            "Inside",
            "Outside",
            minimum_duration_seconds=2.0,
        ),
    )


def _event_value(event: object) -> tuple[object, ...]:
    values = []
    for field in (
        "kind",
        "subject",
        "region",
        "specification",
        "started_at",
        "effective_at",
        "emitted_at",
    ):
        if hasattr(event, field):
            value = getattr(event, field)
            values.append(value.value if isinstance(value, EventKind) else value)
    return tuple(values)


def _snapshot(runtime: TemporalSpatialRuntime) -> tuple[object, ...]:
    world = runtime.world
    pending = tuple(
        sorted(
            (
                name,
                item.specification.kind.value,
                item.specification.subject,
                item.specification.region,
                item.started_at,
                item.specification.duration_seconds,
            )
            for name, item in runtime._pending.items()
        )
    )
    return (
        tuple(sorted(world.regions.items())),
        tuple(sorted(world.positions.items())),
        tuple(sorted(world.states.items())),
        tuple(world.observations),
        pending,
        runtime.current_time,
    )


def _execute(sequence: tuple[int, ...]) -> tuple[object, ...]:
    runtime = TemporalSpatialRuntime(
        _world(POSITIONS[0][1]), BASE_TIME, rules=_rules()
    )
    trace: list[tuple[object, ...]] = []
    preservation_checks = 0
    for index, position_index in enumerate(sequence, start=1):
        result = runtime.move_at(
            "asset", POSITIONS[position_index][1], BASE_TIME + timedelta(seconds=index)
        )
        trace.extend(_event_value(event) for event in result.sustained)
        trace.extend(_event_value(event) for event in result.instantaneous)
        if runtime.world.states["asset"] not in STATE_DOMAIN:
            raise AssertionError("state-domain preservation failed")
        if runtime.world.positions["asset"].crs != CRS84:
            raise AssertionError("CRS preservation failed")
        if len(runtime._pending) != len(set(runtime._pending)):
            raise AssertionError("pending monitor uniqueness failed")
        preservation_checks += 1
    pending_before = len(runtime._pending)
    due = runtime.advance_to(BASE_TIME + timedelta(seconds=len(sequence) + 3))
    if len(due) > pending_before:
        raise AssertionError("finite-advance bound failed")
    trace.extend(_event_value(event) for event in due)
    return _snapshot(runtime), tuple(trace), preservation_checks, pending_before


def _atomic_error_checks() -> int:
    checks = 0
    runtime = TemporalSpatialRuntime(_world(POSITIONS[2][1]), BASE_TIME, _rules())
    before = _snapshot(runtime)
    try:
        runtime.move_at(
            "asset",
            Point(5.0, 5.0, "urn:pulse:test:grid"),
            BASE_TIME + timedelta(seconds=1),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("mixed-CRS move was not rejected")
    if _snapshot(runtime) != before:
        raise AssertionError("mixed-CRS error mutated the configuration")
    checks += 1

    try:
        runtime.move_at("asset", POSITIONS[2][1], BASE_TIME - timedelta(seconds=1))
    except ValueError:
        pass
    else:
        raise AssertionError("backward move was not rejected")
    if _snapshot(runtime) != before:
        raise AssertionError("backward-time error mutated the configuration")
    return checks + 1


def _observation_checks() -> int:
    checks = 0
    for _, position in POSITIONS:
        world = _world(position)
        authoritative = (
            tuple(world.positions.items()),
            tuple(world.states.items()),
            tuple(world.regions.items()),
        )
        world.record_observation(
            LocationObservation(
                "asset",
                Point(position.x + 0.25, position.y),
                BASE_TIME,
                "bounded-check",
            )
        )
        after = (
            tuple(world.positions.items()),
            tuple(world.states.items()),
            tuple(world.regions.items()),
        )
        if after != authoritative or len(world.observations) != 1:
            raise AssertionError("observation non-interference failed")
        checks += 1
    return checks


def _scenario_checks() -> int:
    checks = 0
    immediate_rule = _rules()[0]
    for _, target in POSITIONS:
        world = _world(POSITIONS[0][1])
        source = (
            tuple(world.positions.items()),
            tuple(world.states.items()),
            tuple(world.observations),
        )
        result = SpatialRuntime(world, (immediate_rule,)).scenario((('asset', target),))
        after = (
            tuple(world.positions.items()),
            tuple(world.states.items()),
            tuple(world.observations),
        )
        if after != source or result.world is world:
            raise AssertionError("scenario isolation failed")
        checks += 1
    return checks


def run_bounded_checks(max_depth: int = 4) -> dict[str, object]:
    if max_depth < 1:
        raise ValueError("max_depth must be positive")
    sequences = tuple(
        sequence
        for depth in range(1, max_depth + 1)
        for sequence in itertools.product(range(len(POSITIONS)), repeat=depth)
    )
    deterministic_checks = 0
    preservation_checks = 0
    finite_advance_checks = 0
    explored_steps = 0
    for sequence in sequences:
        first = _execute(sequence)
        second = _execute(sequence)
        if first[:2] != second[:2]:
            raise AssertionError(f"determinism failed for {sequence!r}")
        deterministic_checks += 1
        preservation_checks += first[2] + second[2]
        finite_advance_checks += 2
        explored_steps += len(sequence) * 2

    atomic_checks = _atomic_error_checks()
    observation_checks = _observation_checks()
    scenario_checks = _scenario_checks()
    return {
        "experiment": "pulse-core-bounded-metatheory-check-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "claimBoundary": (
            "Exhaustive exploration of every action sequence through the "
            f"finite four-position abstraction up to depth {max_depth}. It "
            "supports testing of the proof assumptions but is not a general, "
            "machine-checked proof of the unbounded calculus."
        ),
        "abstraction": {
            "positions": [name for name, _ in POSITIONS],
            "states": sorted(STATE_DOMAIN),
            "maxDepth": max_depth,
            "sequenceCount": len(sequences),
            "executedMoveSteps": explored_steps,
        },
        "checks": {
            "determinism": deterministic_checks,
            "preservation": preservation_checks,
            "finiteAdvance": finite_advance_checks,
            "atomicFailure": atomic_checks,
            "observationNonInterference": observation_checks,
            "scenarioIsolation": scenario_checks,
        },
        "summary": {
            "totalChecks": (
                deterministic_checks
                + preservation_checks
                + finite_advance_checks
                + atomic_checks
                + observation_checks
                + scenario_checks
            ),
            "failures": 0,
            "allChecksPass": True,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    abstraction = result["abstraction"]
    checks = result["checks"]
    summary = result["summary"]
    assert isinstance(abstraction, dict)
    assert isinstance(checks, dict)
    assert isinstance(summary, dict)
    lines = [
        "# PULSE core bounded metatheory check",
        "",
        "## Exploration",
        "",
        f"- Maximum depth: {abstraction['maxDepth']}",
        f"- Action sequences: {abstraction['sequenceCount']}",
        f"- Executed move steps: {abstraction['executedMoveSteps']}",
        "",
        "## Property checks",
        "",
    ]
    lines.extend(f"- {name}: {count}" for name, count in checks.items())
    lines.extend(
        (
            f"- Total checks: **{summary['totalChecks']}**",
            f"- Failures: **{summary['failures']}**",
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
        prog="pulse-spatial-formal-properties",
        description="Run bounded exhaustive checks for PULSE core properties.",
    )
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    arguments = parser.parse_args()
    try:
        result = run_bounded_checks(arguments.max_depth)
    except (AssertionError, ValueError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")


if __name__ == "__main__":
    main()
