"""Differential boundary corpus for the dependency-free topology kernel."""

from __future__ import annotations

import argparse
import json
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from ..geometry import CRS84, Point, Polygon, covered_by, on_boundary, within


@dataclass(frozen=True, slots=True)
class TopologyCase:
    name: str
    feature: str
    shell: tuple[tuple[float, float], ...]
    point: tuple[float, float]
    crs: str = CRS84


SQUARE = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
CONCAVE = (
    (0.0, 0.0),
    (6.0, 0.0),
    (6.0, 6.0),
    (4.0, 6.0),
    (4.0, 2.0),
    (2.0, 2.0),
    (2.0, 6.0),
    (0.0, 6.0),
)

CASES: tuple[TopologyCase, ...] = (
    TopologyCase("square-interior", "interior", SQUARE, (5.0, 5.0)),
    TopologyCase("square-exterior", "exterior", SQUARE, (11.0, 5.0)),
    TopologyCase("horizontal-edge", "boundary edge", SQUARE, (5.0, 0.0)),
    TopologyCase("vertical-edge", "boundary edge", SQUARE, (0.0, 5.0)),
    TopologyCase("square-vertex", "boundary vertex", SQUARE, (0.0, 0.0)),
    TopologyCase(
        "near-boundary-inside",
        "1e-13 inside boundary",
        SQUARE,
        (1e-13, 5.0),
    ),
    TopologyCase(
        "near-boundary-outside",
        "1e-13 outside boundary",
        SQUARE,
        (-1e-13, 5.0),
    ),
    TopologyCase("concave-interior", "concave interior", CONCAVE, (1.0, 3.0)),
    TopologyCase("concave-notch", "concave exterior", CONCAVE, (3.0, 3.0)),
    TopologyCase(
        "concave-horizontal-edge",
        "concave boundary edge",
        CONCAVE,
        (3.0, 2.0),
    ),
    TopologyCase(
        "concave-reflex-vertex",
        "concave boundary vertex",
        CONCAVE,
        (2.0, 2.0),
    ),
    TopologyCase(
        "reversed-ring",
        "clockwise orientation",
        tuple(reversed(SQUARE)),
        (5.0, 5.0),
    ),
    TopologyCase(
        "slanted-edge",
        "non-axis-aligned boundary",
        ((0.0, 0.0), (10.0, 10.0), (10.0, 0.0)),
        (5.0, 5.0),
    ),
    TopologyCase(
        "tiny-polygon",
        "1e-9-scale interior",
        ((0.0, 0.0), (1e-9, 0.0), (1e-9, 1e-9), (0.0, 1e-9)),
        (5e-10, 5e-10),
    ),
    TopologyCase(
        "large-offset-grid",
        "1e9-offset local grid",
        (
            (1e9, 1e9),
            (1e9 + 10.0, 1e9),
            (1e9 + 10.0, 1e9 + 10.0),
            (1e9, 1e9 + 10.0),
        ),
        (1e9 + 5.0, 1e9 + 5.0),
        "urn:pulse:test:grid",
    ),
    TopologyCase(
        "thin-polygon",
        "1e-12-height interior",
        ((0.0, 0.0), (1.0, 0.0), (1.0, 1e-12), (0.0, 1e-12)),
        (0.5, 5e-13),
        "urn:pulse:test:grid",
    ),
    TopologyCase(
        "negative-coordinates",
        "negative-coordinate interior",
        ((-10.0, -10.0), (-2.0, -10.0), (-2.0, -2.0), (-10.0, -2.0)),
        (-6.0, -6.0),
        "urn:pulse:test:grid",
    ),
)


def _evaluate(case: TopologyCase) -> dict[str, object]:
    try:
        from shapely import Point as ReferencePoint
        from shapely import Polygon as ReferencePolygon
    except ImportError as error:
        raise RuntimeError("Shapely is required for reference execution") from error

    polygon = Polygon.from_xy(case.shell, case.crs)
    point = Point(*case.point, case.crs)
    reference_polygon = ReferencePolygon(case.shell)
    reference_point = ReferencePoint(case.point)
    if not reference_polygon.is_valid:
        raise ValueError(f"Reference polygon is invalid in case {case.name!r}")

    internal = {
        "within": within(point, polygon),
        "onBoundary": on_boundary(point, polygon),
        "coveredBy": covered_by(point, polygon),
    }
    reference = {
        "within": bool(reference_point.within(reference_polygon)),
        "onBoundary": bool(reference_polygon.boundary.covers(reference_point)),
        "coveredBy": bool(reference_polygon.covers(reference_point)),
    }
    return {
        "name": case.name,
        "feature": case.feature,
        "crs": case.crs,
        "shell": [list(coordinate) for coordinate in case.shell],
        "point": list(case.point),
        "internal": internal,
        "reference": reference,
        "matches": internal == reference,
    }


def _rejection_cases() -> tuple[tuple[str, str, Callable[[], object]], ...]:
    local = "urn:pulse:test:grid"
    return (
        (
            "too-few-coordinates",
            "at least four coordinates",
            lambda: Polygon((Point(0, 0), Point(1, 0), Point(0, 0))),
        ),
        (
            "open-shell",
            "must be closed",
            lambda: Polygon(
                (Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1))
            ),
        ),
        (
            "mixed-shell-crs",
            "share one CRS",
            lambda: Polygon(
                (
                    Point(0, 0),
                    Point(1, 0, local),
                    Point(0, 1),
                    Point(0, 0),
                )
            ),
        ),
        (
            "non-finite-coordinate",
            "must be finite",
            lambda: Point(float("nan"), 0),
        ),
        (
            "missing-crs",
            "must be explicit",
            lambda: Point(0, 0, ""),
        ),
        (
            "collinear-shell",
            "cannot be collinear",
            lambda: Polygon.from_xy(((0, 0), (1, 0), (2, 0))),
        ),
        (
            "self-intersecting-shell",
            "must be simple",
            lambda: Polygon.from_xy(((0, 0), (2, 2), (0, 2), (2, 0))),
        ),
        (
            "zero-length-edge",
            "zero-length edges",
            lambda: Polygon.from_xy(((0, 0), (2, 0), (2, 0), (0, 2))),
        ),
        (
            "query-crs-mismatch",
            "CRS mismatch",
            lambda: covered_by(
                Point(0.5, 0.5, local),
                Polygon.from_xy(((0, 0), (1, 0), (1, 1), (0, 1))),
            ),
        ),
    )


def _evaluate_rejection(
    name: str,
    expected_message: str,
    operation: Callable[[], object],
) -> dict[str, object]:
    try:
        operation()
    except ValueError as error:
        message = str(error)
        return {
            "name": name,
            "expectedMessageFragment": expected_message,
            "actualError": message,
            "rejectedAsExpected": expected_message in message,
        }
    return {
        "name": name,
        "expectedMessageFragment": expected_message,
        "actualError": None,
        "rejectedAsExpected": False,
    }


def run_corpus() -> dict[str, object]:
    try:
        import shapely
    except ImportError as error:
        raise RuntimeError("Shapely is required for reference execution") from error

    topology_cases = [_evaluate(case) for case in CASES]
    rejection_cases = [
        _evaluate_rejection(name, message, operation)
        for name, message, operation in _rejection_cases()
    ]
    topology_mismatches = sum(not bool(case["matches"]) for case in topology_cases)
    rejection_mismatches = sum(
        not bool(case["rejectedAsExpected"]) for case in rejection_cases
    )
    return {
        "experiment": "point-polygon-boundary-differential-corpus-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "claimBoundary": (
            "Differential agreement with Shapely/GEOS for the checked-in, "
            "two-dimensional Point/simple-Polygon cases and explicit rejection "
            "contracts. This is not an OGC or GeoSPARQL conformance suite and "
            "does not cover holes, multipolygons, coordinate transformation, "
            "geodesic predicates, or antimeridian semantics."
        ),
        "semantics": {
            "within": "strict interior; polygon boundary excluded",
            "onBoundary": "point lies on a polygon shell segment",
            "coveredBy": "strict interior or polygon boundary",
            "numericPolicy": (
                "binary64 fast orientation with exact-rational fallback near "
                "the floating-point error bound; no coordinate-unit epsilon"
            ),
        },
        "summary": {
            "topologyCases": len(topology_cases),
            "topologyMismatches": topology_mismatches,
            "rejectionCases": len(rejection_cases),
            "rejectionMismatches": rejection_mismatches,
            "allChecksPass": not topology_mismatches and not rejection_mismatches,
        },
        "topologyCases": topology_cases,
        "rejectionCases": rejection_cases,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    topology_cases = result["topologyCases"]
    rejection_cases = result["rejectionCases"]
    assert isinstance(summary, dict)
    assert isinstance(topology_cases, list)
    assert isinstance(rejection_cases, list)
    lines = [
        "# Point/Polygon boundary differential corpus",
        "",
        "## Summary",
        "",
        f"- Topology cases: {summary['topologyCases']}",
        f"- Topology mismatches: {summary['topologyMismatches']}",
        f"- Rejection cases: {summary['rejectionCases']}",
        f"- Rejection mismatches: {summary['rejectionMismatches']}",
        f"- All checks pass: **{summary['allChecksPass']}**",
        "",
        "## Topology cases",
        "",
        "| Case | Feature | Within | Boundary | Covered by | Match |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for case in topology_cases:
        internal = case["internal"]
        lines.append(
            f"| {case['name']} | {case['feature']} | {internal['within']} | "
            f"{internal['onBoundary']} | {internal['coveredBy']} | "
            f"{case['matches']} |"
        )
    lines.extend(
        (
            "",
            "## Explicit rejection cases",
            "",
            "| Case | Rejected as expected | Error |",
            "|---|---:|---|",
        )
    )
    for case in rejection_cases:
        lines.append(
            f"| {case['name']} | {case['rejectedAsExpected']} | "
            f"{case['actualError']} |"
        )
    lines.extend(("", "## Claim boundary", "", str(result["claimBoundary"]), ""))
    return "\n".join(lines)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-topology-corpus",
        description="Run the Point/Polygon boundary differential corpus.",
    )
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-parity", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_corpus()
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    if arguments.require_parity and not result["summary"]["allChecksPass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
