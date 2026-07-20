"""Persistent PostGIS/GiST baseline for the IBTrACS workload."""

from __future__ import annotations

import argparse
import csv
import io
import json
import platform
import subprocess
import tempfile
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from ..runtime import EventKind
from .ibtracs import SOURCE_DOI, Track, _sha256, load_ibtracs, source_descriptor
from .spatiotemporal import (
    DURATIONS_HOURS,
    STUDY_ZONES,
    ExperimentTrace,
    InstantEventLabel,
    MembershipLabel,
    SustainedEventLabel,
    _internal_trace,
)


DEFAULT_IMAGE = (
    "postgis/postgis:18-3.6@"
    "sha256:c893f6f2652d11e13f50f8623045b3523991b41d038b4d213dc040f42641f0d7"
)
DATABASE = "pulse"
PASSWORD = "pulse-local-benchmark"


def _docker(
    arguments: list[str],
    *,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["docker", *arguments],
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode:
        raise RuntimeError(
            f"docker {' '.join(arguments[:3])} failed with exit code "
            f"{completed.returncode}: {completed.stderr.strip()}"
        )
    return completed


def _psql(container: str, sql: str) -> str:
    completed = _docker(
        [
            "exec",
            "-e",
            f"PGPASSWORD={PASSWORD}",
            container,
            "psql",
            "--no-psqlrc",
            "--set",
            "ON_ERROR_STOP=1",
            "--quiet",
            "--tuples-only",
            "--no-align",
            "--username",
            "postgres",
            "--dbname",
            DATABASE,
            "--command",
            sql,
        ]
    )
    return completed.stdout.strip()


def _wait_ready(
    container: str,
    *,
    initial_creation: bool,
    timeout_seconds: float = 120.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        logs = _docker(["logs", container], check=False)
        combined_logs = logs.stdout + logs.stderr
        if initial_creation and "PostgreSQL init process complete" not in combined_logs:
            time.sleep(0.5)
            continue
        completed = _docker(
            [
                "exec",
                container,
                "pg_isready",
                "--username",
                "postgres",
                "--dbname",
                DATABASE,
            ],
            check=False,
        )
        if completed.returncode == 0:
            probe = _docker(
                [
                    "exec",
                    "-e",
                    f"PGPASSWORD={PASSWORD}",
                    container,
                    "psql",
                    "--no-psqlrc",
                    "--tuples-only",
                    "--no-align",
                    "--username",
                    "postgres",
                    "--dbname",
                    DATABASE,
                    "--command",
                    "SELECT 1;",
                ],
                check=False,
            )
            if probe.returncode == 0 and probe.stdout.strip() == "1":
                return
        last_error = completed.stderr.strip() or completed.stdout.strip()
        time.sleep(0.5)
    raise RuntimeError(f"PostGIS did not become ready: {last_error}")


def _start_container(
    container: str,
    volume: str,
    benchmark_directory: Path,
    image: str,
    *,
    initial_creation: bool,
    network: str | None = None,
) -> None:
    command = [
        "run",
        "--detach",
        "--name",
        container,
        "--env",
        f"POSTGRES_PASSWORD={PASSWORD}",
        "--env",
        f"POSTGRES_DB={DATABASE}",
        "--mount",
        f"type=volume,source={volume},target=/var/lib/postgresql",
        "--mount",
        (
            "type=bind,source="
            f"{benchmark_directory.resolve()},target=/benchmark,readonly"
        ),
    ]
    if network is not None:
        command.extend(("--network", network))
    command.append(image)
    _docker(command)
    _wait_ready(container, initial_creation=initial_creation)


def _ensure_image(image: str) -> tuple[float | None, str]:
    present = _docker(["image", "inspect", image], check=False)
    pull_seconds: float | None = None
    if present.returncode:
        started = time.perf_counter()
        _docker(["pull", image])
        pull_seconds = time.perf_counter() - started
    identifier = _docker(
        ["image", "inspect", image, "--format", "{{.Id}}"]
    ).stdout.strip()
    return pull_seconds, identifier


def _polygon_wkt(coordinates: Iterable[tuple[float, float]]) -> str:
    return "POLYGON((" + ",".join(f"{x:.15g} {y:.15g}" for x, y in coordinates) + "))"


def _write_database_inputs(directory: Path, tracks: Iterable[Track]) -> int:
    regions_path = directory / "regions.csv"
    samples_path = directory / "samples.csv"
    with regions_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("name", "wkt"))
        for name, coordinates in STUDY_ZONES:
            writer.writerow((name, _polygon_wkt(coordinates)))
    sample_count = 0
    with samples_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            ("sid", "sample_index", "observed_at", "longitude", "latitude")
        )
        for track in tracks:
            for index, point in enumerate(track.points):
                writer.writerow(
                    (
                        track.sid,
                        index,
                        point.observed_at.isoformat(),
                        format(point.longitude, ".15g"),
                        format(point.latitude, ".15g"),
                    )
                )
                sample_count += 1
    # Linux containers run PostgreSQL as a non-root user.  TemporaryDirectory
    # is 0700 by default, so explicitly grant read/traverse access.
    directory.chmod(0o755)
    regions_path.chmod(0o644)
    samples_path.chmod(0o644)
    return sample_count


def _load_schema(container: str) -> dict[str, float]:
    timings: dict[str, float] = {}
    started = time.perf_counter()
    _psql(
        container,
        """
        CREATE EXTENSION IF NOT EXISTS postgis;
        DROP TABLE IF EXISTS samples;
        DROP TABLE IF EXISTS regions;
        CREATE TABLE regions (
          name text PRIMARY KEY,
          wkt text NOT NULL,
          geom geometry(Polygon, 4326)
        );
        CREATE TABLE samples (
          sid text NOT NULL,
          sample_index integer NOT NULL,
          observed_at timestamptz NOT NULL,
          longitude double precision NOT NULL,
          latitude double precision NOT NULL,
          geom geometry(Point, 4326),
          PRIMARY KEY (sid, sample_index)
        );
        """,
    )
    timings["schema"] = time.perf_counter() - started

    started = time.perf_counter()
    _psql(
        container,
        """
        COPY regions(name, wkt)
          FROM '/benchmark/regions.csv' WITH (FORMAT csv, HEADER true);
        UPDATE regions SET geom = ST_GeomFromText(wkt, 4326);
        ALTER TABLE regions ALTER COLUMN geom SET NOT NULL;
        COPY samples(sid, sample_index, observed_at, longitude, latitude)
          FROM '/benchmark/samples.csv' WITH (FORMAT csv, HEADER true);
        UPDATE samples
          SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326);
        ALTER TABLE samples ALTER COLUMN geom SET NOT NULL;
        """,
    )
    timings["copyAndMaterialize"] = time.perf_counter() - started

    started = time.perf_counter()
    _psql(
        container,
        """
        CREATE INDEX samples_geom_gix ON samples USING GIST (geom);
        CREATE INDEX regions_geom_gix ON regions USING GIST (geom);
        ANALYZE samples;
        ANALYZE regions;
        CHECKPOINT;
        """,
    )
    timings["indexAnalyzeCheckpoint"] = time.perf_counter() - started
    return timings


def _positive_memberships(container: str) -> tuple[set[tuple[str, int, str]], float]:
    started = time.perf_counter()
    output = _psql(
        container,
        """
        COPY (
          SELECT s.sid, s.sample_index, r.name
          FROM regions AS r
          JOIN samples AS s ON ST_Covers(r.geom, s.geom)
          ORDER BY s.sid, s.sample_index, r.name
        ) TO STDOUT WITH (FORMAT csv);
        """,
    )
    seconds = time.perf_counter() - started
    rows = {
        (sid, int(index), region)
        for sid, index, region in csv.reader(io.StringIO(output))
    }
    return rows, seconds


def trace_from_memberships(
    tracks: Iterable[Track], positive: set[tuple[str, int, str]]
) -> ExperimentTrace:
    """Derive sampled events without calling PULSE or another geometry library."""

    memberships: list[MembershipLabel] = []
    instantaneous: list[InstantEventLabel] = []
    sustained: list[SustainedEventLabel] = []
    region_names = tuple(name for name, _ in STUDY_ZONES)
    for track in tracks:
        if len(track.points) < 2:
            continue
        previous = {
            region: (track.sid, 0, region) in positive for region in region_names
        }
        pending: dict[str, tuple[str, EventKind, float, datetime]] = {}
        for index, point in enumerate(track.points[1:], start=1):
            now = point.observed_at
            due = sorted(
                (
                    (name, value)
                    for name, value in pending.items()
                    if value[3] + timedelta(seconds=value[2]) <= now
                ),
                key=lambda item: (
                    item[1][3] + timedelta(seconds=item[1][2]),
                    item[0],
                ),
            )
            for name, (region, kind, seconds, started_at) in due:
                sustained.append(
                    SustainedEventLabel(
                        track.sid,
                        region,
                        kind.value,
                        seconds,
                        started_at.isoformat(),
                        (started_at + timedelta(seconds=seconds)).isoformat(),
                        now.isoformat(),
                    )
                )
                del pending[name]
            for region in region_names:
                inside = (track.sid, index, region) in positive
                memberships.append(
                    MembershipLabel(
                        track.sid, index, now.isoformat(), region, inside
                    )
                )
                if previous[region] == inside:
                    continue
                kind = EventKind.ENTERS if inside else EventKind.LEAVES
                instantaneous.append(
                    InstantEventLabel(
                        track.sid, index, now.isoformat(), region, kind.value
                    )
                )
                for name in tuple(pending):
                    value = pending[name]
                    if value[0] == region and value[1] is not kind:
                        del pending[name]
                for hours in DURATIONS_HOURS:
                    name = f"{region}:{kind.value}:{hours}h"
                    pending[name] = (region, kind, hours * 3600, now)
                previous[region] = inside
    return ExperimentTrace(
        tuple(sorted(memberships)),
        tuple(sorted(instantaneous)),
        tuple(sorted(sustained)),
    )


def _difference_sample(
    internal: Iterable[object], baseline: Iterable[object]
) -> list[dict[str, object]]:
    return [asdict(value) for value in sorted(set(internal) ^ set(baseline))[:20]]


def _plan_uses_index(plan: object, index_name: str) -> bool:
    if isinstance(plan, dict):
        if plan.get("Index Name") == index_name:
            return True
        return any(_plan_uses_index(value, index_name) for value in plan.values())
    if isinstance(plan, list):
        return any(_plan_uses_index(value, index_name) for value in plan)
    return False


def run_experiment(
    dataset_path: str | Path,
    *,
    image: str = DEFAULT_IMAGE,
    max_tracks: int | None = None,
    keep_volume: bool = False,
) -> dict[str, object]:
    path = Path(dataset_path)
    dataset = load_ibtracs(path, max_tracks=max_tracks)
    tracks = dataset.tracks
    token = uuid.uuid4().hex[:12]
    container = f"pulse-postgis-{token}"
    volume = f"pulse-postgis-{token}"
    pull_seconds, image_id = _ensure_image(image)
    _docker(["volume", "create", volume])
    timings: dict[str, float | None] = {"imagePull": pull_seconds}
    try:
        with tempfile.TemporaryDirectory(prefix="pulse-postgis-") as temporary:
            benchmark_directory = Path(temporary)
            started = time.perf_counter()
            sample_count = _write_database_inputs(benchmark_directory, tracks)
            timings["csvSerialization"] = time.perf_counter() - started

            started = time.perf_counter()
            _start_container(
                container,
                volume,
                benchmark_directory,
                image,
                initial_creation=True,
            )
            timings["initialDatabaseStart"] = time.perf_counter() - started
            timings.update(_load_schema(container))

            positive, query_seconds = _positive_memberships(container)
            timings["indexedMembershipQuery"] = query_seconds

            plan_text = _psql(
                container,
                """
                EXPLAIN (FORMAT JSON)
                SELECT s.sid, s.sample_index, r.name
                FROM regions AS r
                JOIN samples AS s ON ST_Covers(r.geom, s.geom);
                """,
            )
            plan = json.loads(plan_text)
            uses_gist = _plan_uses_index(plan, "samples_geom_gix")
            stats_before = next(
                csv.reader(
                    io.StringIO(
                        _psql(
                            container,
                            """
                            SELECT count(*),
                                   pg_relation_size('samples'),
                                   pg_indexes_size('samples'),
                                   pg_database_size(current_database())
                            FROM samples;
                            """,
                        ).replace("|", ",")
                    )
                )
            )
            versions = _psql(
                container,
                "SELECT version() || E'\\n' || PostGIS_Full_Version();",
            ).splitlines()

            _docker(["rm", "--force", container])
            started = time.perf_counter()
            _start_container(
                container,
                volume,
                benchmark_directory,
                image,
                initial_creation=False,
            )
            timings["persistentRestart"] = time.perf_counter() - started
            persisted = _psql(
                container,
                """
                SELECT count(*),
                       count(*) FILTER (WHERE geom IS NOT NULL),
                       to_regclass('public.samples_geom_gix') IS NOT NULL
                FROM samples;
                """,
            ).split("|")

            started = time.perf_counter()
            baseline = trace_from_memberships(tracks, positive)
            timings["eventDerivation"] = time.perf_counter() - started
            started = time.perf_counter()
            internal = _internal_trace(tracks)
            timings["pulseExecution"] = time.perf_counter() - started

        membership_mismatches = len(
            set(internal.memberships) ^ set(baseline.memberships)
        )
        event_mismatches = len(
            set(internal.instantaneous) ^ set(baseline.instantaneous)
        )
        sustained_mismatches = len(
            set(internal.sustained) ^ set(baseline.sustained)
        )
        all_match = not (
            membership_mismatches or event_mismatches or sustained_mismatches
        )
        dataset_name, source_url = source_descriptor(path)
        transitions = sum(max(len(track.points) - 1, 0) for track in tracks)
        return {
            "experiment": "postgis-persistent-gist-baseline-v1",
            "generatedAt": datetime.now(UTC).isoformat(),
            "claimBoundary": (
                "Persistent PostgreSQL/PostGIS geometry baseline using an "
                "on-disk Docker volume, GiST indexes, and ST_Covers for the "
                "five experiment-defined Polygon zones. Event and duration "
                "labels are derived from returned sampled memberships. This "
                "is not a concurrent service benchmark, continuous-trajectory "
                "evaluation, or comparison with an RDF triplestore."
            ),
            "dataset": {
                "name": dataset_name,
                "doi": SOURCE_DOI,
                "sourceUrl": source_url,
                "path": path.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "tracks": len(tracks),
                "points": sample_count,
                "transitions": transitions,
                "transitionZonePairs": transitions * len(STUDY_ZONES),
            },
            "database": {
                "image": image,
                "imageId": image_id,
                "postgresVersion": versions[0] if versions else "unknown",
                "postgisVersion": versions[1] if len(versions) > 1 else "unknown",
                "predicate": "ST_Covers(region.geom, sample.geom)",
                "pointSrid": 4326,
                "indexMethod": "GiST",
                "planUsesSamplesGistIndex": uses_gist,
                "positiveMembershipRows": len(positive),
                "sampleTableBytes": int(stats_before[1]),
                "sampleIndexBytes": int(stats_before[2]),
                "databaseBytes": int(stats_before[3]),
                "persistentRestart": {
                    "rows": int(persisted[0]),
                    "geometryRows": int(persisted[1]),
                    "indexPresent": persisted[2] == "t",
                    "verified": (
                        int(persisted[0]) == sample_count
                        and int(persisted[1]) == sample_count
                        and persisted[2] == "t"
                    ),
                },
            },
            "parity": {
                "matches": all_match,
                "membershipMismatches": membership_mismatches,
                "instantaneousEventMismatches": event_mismatches,
                "sustainedEventMismatches": sustained_mismatches,
                "membershipDifferenceSample": _difference_sample(
                    internal.memberships, baseline.memberships
                ),
                "instantaneousDifferenceSample": _difference_sample(
                    internal.instantaneous, baseline.instantaneous
                ),
                "sustainedDifferenceSample": _difference_sample(
                    internal.sustained, baseline.sustained
                ),
            },
            "workload": {
                "instantaneousEvents": len(baseline.instantaneous),
                "sustainedEvents": len(baseline.sustained),
            },
            "timingSeconds": timings,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
        }
    finally:
        _docker(["rm", "--force", container], check=False)
        if not keep_volume:
            _docker(["volume", "rm", "--force", volume], check=False)


def render_markdown(result: dict[str, object]) -> str:
    dataset = result["dataset"]
    database = result["database"]
    parity = result["parity"]
    timing = result["timingSeconds"]
    assert isinstance(dataset, dict)
    assert isinstance(database, dict)
    assert isinstance(parity, dict)
    assert isinstance(timing, dict)
    return "\n".join(
        (
            "# Persistent PostGIS/GiST baseline",
            "",
            f"- Tracks / points: {dataset['tracks']:,} / {dataset['points']:,}",
            f"- Transition-zone pairs: {dataset['transitionZonePairs']:,}",
            f"- Positive membership rows: {database['positiveMembershipRows']:,}",
            f"- Query plan uses samples GiST: **{database['planUsesSamplesGistIndex']}**",
            f"- Persistent restart verified: **{database['persistentRestart']['verified']}**",
            f"- Membership mismatches: {parity['membershipMismatches']:,}",
            f"- Instantaneous-event mismatches: {parity['instantaneousEventMismatches']:,}",
            f"- Sustained-event mismatches: {parity['sustainedEventMismatches']:,}",
            f"- All layers match: **{parity['matches']}**",
            f"- Indexed membership query: {timing['indexedMembershipQuery']:.6f} s",
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
        prog="pulse-spatial-postgis",
        description="Run the persistent PostGIS/GiST baseline.",
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--max-tracks", type=int)
    parser.add_argument("--keep-volume", action="store_true")
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-parity", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_experiment(
            arguments.data,
            image=arguments.image,
            max_tracks=arguments.max_tracks,
            keep_volume=arguments.keep_volume,
        )
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    if arguments.require_parity:
        database = result["database"]
        parity = result["parity"]
        assert isinstance(database, dict)
        assert isinstance(parity, dict)
        if not (
            parity["matches"]
            and database["planUsesSamplesGistIndex"]
            and database["persistentRestart"]["verified"]
        ):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
