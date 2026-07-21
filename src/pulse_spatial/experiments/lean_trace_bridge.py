"""Generated observable-trace bridge between Python and Lean kernels."""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..geometry import CRS84, Point, Polygon
from ..model import SpatialWorld
from ..runtime import EventKind, GeofenceRule, TemporalSpatialRuntime


DEFAULT_LEAN_FIXTURE = Path("formal/lean/generated-integrated-traces.json")
_STATE_IDS = {"Safe": 0, "Maintenance": 1, "AtRisk": 2}


def _position(inside: bool) -> Point:
    return Point(1.0 if inside else -1.0, 1.0, CRS84)


def _event(kind: str, effective_at: int, emitted_at: int) -> dict[str, object]:
    return {
        "kind": kind,
        "effectiveAt": effective_at,
        "emittedAt": emitted_at,
    }


def _run_case(
    initial_inside: bool,
    first_inside: bool,
    second_inside: bool,
    immediate: bool,
) -> dict[str, object]:
    origin = datetime(2026, 7, 21, tzinfo=UTC)
    world = SpatialWorld(
        regions={
            "zone": Polygon.from_xy(
                ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)),
                CRS84,
            )
        },
        positions={"asset": _position(initial_inside)},
        states={"asset": "Safe"},
    )
    rules = [
        GeofenceRule(
            "duration",
            EventKind.LEAVES,
            "asset",
            "zone",
            "Safe",
            "AtRisk",
            2.0,
        )
    ]
    if immediate:
        rules.append(
            GeofenceRule(
                "immediate",
                EventKind.LEAVES,
                "asset",
                "zone",
                "Safe",
                "Maintenance",
            )
        )
    runtime = TemporalSpatialRuntime(world, origin, rules)
    trace: list[dict[str, object]] = []
    for offset, inside in ((1, first_inside), (2, second_inside)):
        step = runtime.move_at("asset", _position(inside), origin + timedelta(seconds=offset))
        trace.extend(
            _event(
                "sustained",
                int((event.effective_at - origin).total_seconds()),
                int((event.emitted_at - origin).total_seconds()),
            )
            for event in step.sustained
        )
        trace.extend(
            _event(event.kind.value, offset, offset)
            for event in step.instantaneous
        )
    trace.extend(
        _event(
            "sustained",
            int((event.effective_at - origin).total_seconds()),
            int((event.emitted_at - origin).total_seconds()),
        )
        for event in runtime.advance_to(origin + timedelta(seconds=4))
    )
    return {
        "initialInside": initial_inside,
        "firstInside": first_inside,
        "secondInside": second_inside,
        "immediate": immediate,
        "status": "ok",
        "finalState": _STATE_IDS[world.states["asset"]],
        "pending": runtime.pending_count,
        "trace": trace,
    }


def generated_python_traces() -> dict[str, object]:
    """Execute the full 2^4 model/action grid with the production runtime."""

    cases = [
        _run_case(initial, first, second, immediate)
        for initial, first, second, immediate in itertools.product(
            (False, True), repeat=4
        )
    ]
    return {"schemaVersion": 1, "caseCount": len(cases), "cases": cases}


def compare_with_lean(path: str | Path = DEFAULT_LEAN_FIXTURE) -> dict[str, object]:
    lean = json.loads(Path(path).read_text(encoding="utf-8"))
    python = generated_python_traces()
    mismatches = [
        index
        for index, (lean_case, python_case) in enumerate(
            zip(lean["cases"], python["cases"], strict=True)
        )
        if lean_case != python_case
    ]
    return {
        "leanCaseCount": lean["caseCount"],
        "pythonCaseCount": python["caseCount"],
        "exactMatches": python["caseCount"] - len(mismatches),
        "mismatchIndexes": mismatches,
        "allExact": lean == python,
        "claimBoundary": (
            "Exact observable-trace correspondence over the declared 16-case "
            "Boolean model/action grid; not a general refinement theorem."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare generated Python traces with the Lean fixture."
    )
    parser.add_argument("--lean-fixture", default=str(DEFAULT_LEAN_FIXTURE))
    parser.add_argument("--require-exact", action="store_true")
    arguments = parser.parse_args()
    result = compare_with_lean(arguments.lean_fixture)
    print(json.dumps(result, indent=2))
    if arguments.require_exact and not result["allExact"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
