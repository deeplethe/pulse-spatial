"""PostGIS agreement on the same topology graph used by the Jena baseline."""

from __future__ import annotations

import argparse
import csv
import io
import json
import platform
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .geosparql_external import compare_results, expected_results, topology_world
from .postgis_baseline import (
    DEFAULT_IMAGE,
    _docker,
    _ensure_image,
    _polygon_wkt,
    _psql,
    _start_container,
)


def _write_inputs(directory: Path) -> None:
    world = topology_world()
    with (directory / "points.csv").open(
        "w", encoding="utf-8", newline=""
    ) as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("name", "x", "y"))
        for name, point in sorted(world.positions.items()):
            writer.writerow((name, format(point.x, ".17g"), format(point.y, ".17g")))
    with (directory / "regions.csv").open(
        "w", encoding="utf-8", newline=""
    ) as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("name", "wkt"))
        for name, polygon in sorted(world.regions.items()):
            writer.writerow(
                (name, _polygon_wkt((point.x, point.y) for point in polygon.shell))
            )
    directory.chmod(0o755)
    (directory / "points.csv").chmod(0o644)
    (directory / "regions.csv").chmod(0o644)


def parse_postgis_rows(value: str) -> dict[tuple[str, str], dict[str, bool]]:
    parsed: dict[tuple[str, str], dict[str, bool]] = {}
    for row in csv.reader(io.StringIO(value)):
        if len(row) != 6:
            raise ValueError(f"Malformed PostGIS topology row: {row!r}")
        subject, region, inside, covered, disjoint, boundary = row
        key = (subject, region)
        if key in parsed:
            raise ValueError(f"Duplicate PostGIS topology pair: {key!r}")
        parsed[key] = {
            "inside": inside == "t",
            "coveredBy": covered == "t",
            "disjoint": disjoint == "t",
            "onBoundary": boundary == "t",
        }
    return parsed


def _load_and_query(container: str) -> tuple[dict[tuple[str, str], dict[str, bool]], dict[str, float]]:
    timings: dict[str, float] = {}
    started = time.perf_counter()
    _psql(
        container,
        """
        CREATE EXTENSION IF NOT EXISTS postgis;
        CREATE TABLE benchmark_points (
          name text PRIMARY KEY,
          x double precision NOT NULL,
          y double precision NOT NULL,
          geom geometry(Point, 4326)
        );
        CREATE TABLE benchmark_regions (
          name text PRIMARY KEY,
          wkt text NOT NULL,
          geom geometry(Polygon, 4326)
        );
        COPY benchmark_points(name, x, y)
          FROM '/benchmark/points.csv' WITH (FORMAT csv, HEADER true);
        COPY benchmark_regions(name, wkt)
          FROM '/benchmark/regions.csv' WITH (FORMAT csv, HEADER true);
        UPDATE benchmark_points
          SET geom = ST_SetSRID(ST_MakePoint(x, y), 4326);
        UPDATE benchmark_regions SET geom = ST_GeomFromText(wkt, 4326);
        ALTER TABLE benchmark_points ALTER COLUMN geom SET NOT NULL;
        ALTER TABLE benchmark_regions ALTER COLUMN geom SET NOT NULL;
        CREATE INDEX benchmark_points_gix ON benchmark_points USING GIST (geom);
        CREATE INDEX benchmark_regions_gix ON benchmark_regions USING GIST (geom);
        ANALYZE benchmark_points;
        ANALYZE benchmark_regions;
        """,
    )
    timings["databaseLoadAndIndex"] = time.perf_counter() - started

    started = time.perf_counter()
    output = _psql(
        container,
        """
        COPY (
          SELECT p.name,
                 r.name,
                 ST_Within(p.geom, r.geom),
                 ST_CoveredBy(p.geom, r.geom),
                 ST_Disjoint(p.geom, r.geom),
                 ST_Touches(p.geom, r.geom)
          FROM benchmark_points AS p
          CROSS JOIN benchmark_regions AS r
          ORDER BY p.name, r.name
        ) TO STDOUT WITH (FORMAT csv);
        """,
    )
    timings["crossProductQuery"] = time.perf_counter() - started
    return parse_postgis_rows(output), timings


def run_experiment(*, image: str = DEFAULT_IMAGE) -> dict[str, object]:
    world = topology_world()
    expected = expected_results(world)
    token = uuid.uuid4().hex[:12]
    container = f"pulse-postgis-topology-{token}"
    volume = f"pulse-postgis-topology-{token}"
    pull_seconds, image_id = _ensure_image(image)
    _docker(["volume", "create", volume])
    try:
        with tempfile.TemporaryDirectory(prefix="pulse-postgis-topology-") as value:
            directory = Path(value)
            started = time.perf_counter()
            _write_inputs(directory)
            serialization_seconds = time.perf_counter() - started
            started = time.perf_counter()
            _start_container(
                container,
                volume,
                directory,
                image,
                initial_creation=True,
            )
            startup_seconds = time.perf_counter() - started
            actual, database_timings = _load_and_query(container)
            versions = _psql(
                container,
                "SELECT version() || E'\\n' || PostGIS_Full_Version();",
            ).splitlines()
    finally:
        _docker(["rm", "--force", container], check=False)
        _docker(["volume", "rm", "--force", volume], check=False)

    mismatches = compare_results(expected, actual)
    boundary_subjects = {
        name
        for name, values in expected.items()
        if name[0] == name[1] and values["onBoundary"]
    }
    boundary_mismatches = [
        mismatch
        for mismatch in mismatches
        if mismatch["subject"] == mismatch["region"]
        and mismatch["subject"] in boundary_subjects
    ]
    return {
        "experiment": "postgis-shared-topology-external-agreement-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "claimBoundary": (
            "Agreement with PostgreSQL/PostGIS ST_Within, ST_CoveredBy, "
            "ST_Disjoint, and ST_Touches on the exact 7,396 CRS84 "
            "Point/Polygon pairs used by the Apache Jena baseline. This is a "
            "shared semantic workload, not an OGC conformance certificate, "
            "geodesic test, or performance contest."
        ),
        "summary": {
            "points": len(world.positions),
            "regions": len(world.regions),
            "pairs": len(expected),
            "rows": len(actual),
            "boundarySelfPairs": len(boundary_subjects),
            "mismatches": len(mismatches),
            "boundaryMismatches": len(boundary_mismatches),
            "allChecksPass": not mismatches,
        },
        "timingSeconds": {
            "imagePull": pull_seconds,
            "inputSerialization": serialization_seconds,
            "databaseStartup": startup_seconds,
            **database_timings,
        },
        "mismatches": mismatches[:20],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "externalSystem": "PostgreSQL/PostGIS",
            "postgresVersion": versions[0] if versions else "unknown",
            "postgisVersion": versions[1] if len(versions) > 1 else "unknown",
            "containerImage": image,
            "containerImageId": image_id,
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    timing = result["timingSeconds"]
    environment = result["environment"]
    assert isinstance(summary, dict)
    assert isinstance(timing, dict)
    assert isinstance(environment, dict)
    lines = [
        "# PostGIS shared topology external agreement",
        "",
        "## Summary",
        "",
        f"- External system: {environment['externalSystem']}",
        f"- Points: {summary['points']}",
        f"- Regions: {summary['regions']}",
        f"- Shared cross-product pairs: {summary['pairs']}",
        f"- Returned rows: {summary['rows']}",
        f"- Boundary self-pairs: {summary['boundarySelfPairs']}",
        f"- Mismatches: **{summary['mismatches']}**",
        f"- All checks pass: **{summary['allChecksPass']}**",
        "",
        "## Timing (seconds)",
        "",
    ]
    for name, seconds in timing.items():
        lines.append(f"- {name}: {seconds if seconds is not None else 'cached'}")
    lines.extend(("", "## Claim boundary", "", str(result["claimBoundary"]), ""))
    return "\n".join(lines)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-postgis-topology",
        description="Compare the shared topology graph with PostGIS.",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-parity", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_experiment(image=arguments.image)
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    if arguments.require_parity:
        summary = result["summary"]
        assert isinstance(summary, dict)
        if not summary["allChecksPass"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
