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


def _event(
    kind: str,
    subject: int,
    effective_at: int,
    emitted_at: int,
) -> dict[str, object]:
    return {
        "kind": kind,
        "subject": subject,
        "region": 9,
        "effectiveAt": effective_at,
        "emittedAt": emitted_at,
    }


def _run_case(
    initial_inside: bool,
    first_inside: bool,
    second_inside: bool,
    immediate: bool,
    dual_rule: bool,
) -> dict[str, object]:
    origin = datetime(2026, 7, 21, tzinfo=UTC)
    world = SpatialWorld(
        regions={
            "zone": Polygon.from_xy(
                ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)),
                CRS84,
            )
        },
        positions={
            "asset": _position(initial_inside),
            "secondary": _position(True),
        },
        states={"asset": "Safe", "secondary": "Safe"},
    )
    rules = [
        GeofenceRule(
            "z-duration",
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
    if dual_rule:
        rules.append(
            GeofenceRule(
                "a-duration",
                EventKind.LEAVES,
                "secondary",
                "zone",
                "Safe",
                "AtRisk",
                2.0,
            )
        )
    runtime = TemporalSpatialRuntime(world, origin, rules)
    trace: list[dict[str, object]] = []
    moves = [(1, "asset", first_inside)]
    if dual_rule:
        moves.append((1, "secondary", False))
    moves.append((2, "asset", second_inside))
    for offset, subject, inside in moves:
        step = runtime.move_at(subject, _position(inside), origin + timedelta(seconds=offset))
        trace.extend(
            _event(
                "sustained",
                0 if event.subject == "asset" else 1,
                int((event.effective_at - origin).total_seconds()),
                int((event.emitted_at - origin).total_seconds()),
            )
            for event in step.sustained
        )
        trace.extend(
            _event(
                event.kind.value,
                0 if event.subject == "asset" else 1,
                offset,
                offset,
            )
            for event in step.instantaneous
        )
    trace.extend(
        _event(
            "sustained",
            0 if event.subject == "asset" else 1,
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
        "dualRule": dual_rule,
        "status": "ok",
        "finalState": _STATE_IDS[world.states["asset"]],
        "secondaryState": _STATE_IDS[world.states["secondary"]],
        "pending": runtime.pending_count,
        "trace": trace,
    }


def generated_python_traces() -> dict[str, object]:
    """Execute the full 2^5 model/action grid with the production runtime."""

    cases = [
        _run_case(initial, first, second, immediate, dual_rule)
        for initial, first, second, immediate, dual_rule in itertools.product(
            (False, True), repeat=5
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
            "Exact observable-trace correspondence over the declared 32-case "
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
