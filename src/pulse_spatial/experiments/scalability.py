"""Deterministic synthetic scale ladder for execution and evidence projection."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
import tracemalloc
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..geometry import Point, Polygon
from ..model import LocationObservation, SpatialWorld
from ..projection import project_sosa
from ..runtime import SpatialRuntime


BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
INSIDE = Point(5.0, 5.0)
OUTSIDE = Point(15.0, 5.0)
ZONE = Polygon.from_xy(((0, 0), (10, 0), (10, 10), (0, 10)))


def _execution_run(size: int) -> tuple[float, int]:
    world = SpatialWorld(regions={"Zone": ZONE}, positions={"asset": OUTSIDE})
    runtime = SpatialRuntime(world)
    event_count = 0
    started = time.perf_counter()
    for index in range(size):
        target = INSIDE if index % 2 == 0 else OUTSIDE
        event_count += len(runtime.move("asset", target))
    seconds = time.perf_counter() - started
    return seconds, event_count


def _evidence_projection_run(size: int) -> dict[str, object]:
    tracemalloc.start()
    world = SpatialWorld(regions={"Zone": ZONE}, positions={"asset": OUTSIDE})
    ingest_started = time.perf_counter()
    for index in range(size):
        world.record_observation(
            LocationObservation(
                "asset",
                INSIDE if index % 2 == 0 else OUTSIDE,
                BASE_TIME + timedelta(seconds=index),
                "synthetic-scale-sensor",
                confidence=0.99,
                accuracy_m=5.0,
            )
        )
    ingest_seconds = time.perf_counter() - ingest_started
    current_after_ingest, peak_after_ingest = tracemalloc.get_traced_memory()
    projection_started = time.perf_counter()
    graph = project_sosa(world)
    projection_seconds = time.perf_counter() - projection_started
    current_after_projection, peak_after_projection = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    graph_bytes = len(graph.encode("utf-8"))
    observation_markers = graph.count("a sosa:Observation")
    if observation_markers != size:
        raise AssertionError(
            f"projection lost observations: expected {size}, found {observation_markers}"
        )
    return {
        "ingestSeconds": ingest_seconds,
        "ingestObservationsPerSecond": size / ingest_seconds,
        "projectionSeconds": projection_seconds,
        "projectionObservationsPerSecond": size / projection_seconds,
        "projectedBytes": graph_bytes,
        "projectedBytesPerObservation": graph_bytes / size,
        "allocatedBytesAfterIngest": current_after_ingest,
        "peakAllocatedBytesAfterIngest": peak_after_ingest,
        "allocatedBytesAfterProjection": current_after_projection,
        "peakAllocatedBytesAfterProjection": peak_after_projection,
        "observationResources": observation_markers,
    }


def run_scalability(
    sizes: tuple[int, ...] = (1_000, 10_000, 100_000), repetitions: int = 3
) -> dict[str, object]:
    if not sizes or any(size <= 0 for size in sizes):
        raise ValueError("sizes must contain positive integers")
    if tuple(sorted(set(sizes))) != sizes:
        raise ValueError("sizes must be unique and strictly increasing")
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")

    rows: list[dict[str, object]] = []
    for size in sizes:
        _execution_run(size)  # untimed warm-up
        execution_seconds: list[float] = []
        event_counts: list[int] = []
        for _ in range(repetitions):
            seconds, events = _execution_run(size)
            execution_seconds.append(seconds)
            event_counts.append(events)
        if len(set(event_counts)) != 1 or event_counts[0] != size:
            raise AssertionError("synthetic execution trace is not deterministic")
        median_execution = statistics.median(execution_seconds)
        evidence = _evidence_projection_run(size)
        rows.append(
            {
                "observationsOrMoves": size,
                "execution": {
                    "repetitions": repetitions,
                    "seconds": execution_seconds,
                    "medianSeconds": median_execution,
                    "movesPerSecond": size / median_execution,
                    "events": event_counts[0],
                },
                "evidenceAndProjection": evidence,
            }
        )

    return {
        "experiment": "pulse-deterministic-scale-ladder-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "claimBoundary": (
            "Single-process deterministic scale ladder for one Point/Polygon "
            "geofence and append-only evidence projection. Tracemalloc reports "
            "Python-managed allocations, not total process RSS. Results are "
            "not a concurrency, distributed deployment, database, or industrial "
            "service-level benchmark."
        ),
        "protocol": {
            "sizes": list(sizes),
            "repetitions": repetitions,
            "execution": "alternating outside/inside moves; one event per move",
            "evidence": "append-only observations with time, source, confidence, accuracy",
            "projection": "SOSA/GeoSPARQL Turtle string materialization",
        },
        "rows": rows,
        "summary": {
            "largestSize": sizes[-1],
            "largestExecutionEvents": rows[-1]["execution"]["events"],
            "largestProjectionBytes": rows[-1]["evidenceAndProjection"][
                "projectedBytes"
            ],
            "allChecksPass": True,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    rows = result["rows"]
    assert isinstance(rows, list)
    lines = [
        "# PULSE deterministic scale ladder",
        "",
        "| Size | Moves/s | Ingest obs/s | Projection obs/s | RDF bytes | Peak allocated bytes |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        execution = row["execution"]
        evidence = row["evidenceAndProjection"]
        lines.append(
            f"| {row['observationsOrMoves']:,} | "
            f"{execution['movesPerSecond']:,.0f} | "
            f"{evidence['ingestObservationsPerSecond']:,.0f} | "
            f"{evidence['projectionObservationsPerSecond']:,.0f} | "
            f"{evidence['projectedBytes']:,} | "
            f"{evidence['peakAllocatedBytesAfterProjection']:,} |"
        )
    lines.extend(("", "## Claim boundary", "", str(result["claimBoundary"]), ""))
    return "\n".join(lines)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def _sizes(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as error:
        raise argparse.ArgumentTypeError("sizes must be comma-separated integers") from error
    if not parsed:
        raise argparse.ArgumentTypeError("at least one size is required")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-scalability",
        description="Run deterministic execution and projection scale ladders.",
    )
    parser.add_argument("--sizes", type=_sizes, default=(1_000, 10_000, 100_000))
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    arguments = parser.parse_args()
    try:
        result = run_scalability(arguments.sizes, arguments.repetitions)
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
