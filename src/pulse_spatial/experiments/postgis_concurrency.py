"""Production-oriented concurrent PostGIS benchmark using pgbench."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import statistics
import subprocess
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .ibtracs import SOURCE_DOI, _sha256, load_ibtracs, source_descriptor
from .postgis_baseline import (
    DATABASE,
    DEFAULT_IMAGE,
    PASSWORD,
    _docker,
    _ensure_image,
    _load_schema,
    _plan_uses_index,
    _psql,
    _start_container,
    _wait_ready,
    _write_database_inputs,
)


SCRIPT_NAMES = ("point-membership", "window-scan", "position-update")
SCRIPT_WEIGHTS = (6, 2, 2)


def _runtime_environment(container: str) -> dict[str, object]:
    docker_info = json.loads(_docker(["info", "--format", "{{json .}}"]).stdout)
    settings = dict(
        line.split("=", 1)
        for line in _psql(
            container,
            """
            SELECT name || '=' || setting || coalesce(unit, '')
            FROM pg_settings
            WHERE name IN (
              'shared_buffers', 'effective_cache_size', 'work_mem',
              'maintenance_work_mem', 'max_connections',
              'max_worker_processes', 'max_parallel_workers',
              'checkpoint_timeout', 'max_wal_size'
            )
            ORDER BY name;
            """,
        ).splitlines()
    )
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logicalCpuCount": os.cpu_count(),
        "docker": {
            "serverVersion": docker_info.get("ServerVersion"),
            "operatingSystem": docker_info.get("OperatingSystem"),
            "kernelVersion": docker_info.get("KernelVersion"),
            "logicalCpus": docker_info.get("NCPU"),
            "memoryBytes": docker_info.get("MemTotal"),
        },
        "postgresql": {
            "serverVersion": _psql(container, "SHOW server_version;"),
            "postgisVersion": _psql(container, "SELECT postgis_lib_version();"),
            "settings": settings,
            "databaseSizeBytes": int(
                _psql(container, "SELECT pg_database_size(current_database());")
            ),
        },
    }


def percentile(values: Iterable[float], fraction: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    if not 0 <= fraction <= 1:
        raise ValueError("Percentile fraction must be between zero and one")
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def parse_pgbench_log(value: str) -> dict[str, object]:
    latencies: list[float] = []
    by_script: dict[int, list[float]] = {}
    failures: dict[str, int] = {}
    retries = 0
    schedule_lags: list[float] = []
    for line in value.splitlines():
        fields = line.split()
        if len(fields) < 6:
            continue
        elapsed = fields[2]
        script = int(fields[3])
        if elapsed.isdigit():
            milliseconds = int(elapsed) / 1000.0
            latencies.append(milliseconds)
            by_script.setdefault(script, []).append(milliseconds)
        else:
            failures[elapsed] = failures.get(elapsed, 0) + 1
        if len(fields) >= 8:
            if fields[6].isdigit():
                schedule_lags.append(int(fields[6]) / 1000.0)
            if fields[7].isdigit():
                retries += int(fields[7])
        elif len(fields) >= 7 and fields[6].isdigit():
            retries += int(fields[6])

    def statistics(samples: list[float]) -> dict[str, float | int | None]:
        return {
            "transactions": len(samples),
            "meanMs": sum(samples) / len(samples) if samples else None,
            "p50Ms": percentile(samples, 0.50),
            "p95Ms": percentile(samples, 0.95),
            "p99Ms": percentile(samples, 0.99),
            "maxMs": max(samples) if samples else None,
        }

    return {
        **statistics(latencies),
        "failures": failures,
        "retries": retries,
        "scheduleLag": statistics(schedule_lags),
        "scripts": {
            SCRIPT_NAMES[index]
            if index < len(SCRIPT_NAMES)
            else str(index): statistics(samples)
            for index, samples in sorted(by_script.items())
        },
    }


def summarize_levels(levels: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[int, list[dict[str, object]]] = {}
    for level in levels:
        grouped.setdefault(int(level["clients"]), []).append(level)
    summaries: list[dict[str, object]] = []
    for clients, records in sorted(grouped.items()):
        tps_values = [float(record["tps"]) for record in records]
        p99_values = [float(record["p99Ms"]) for record in records]
        mean_tps = statistics.mean(tps_values)
        summaries.append(
            {
                "clients": clients,
                "repetitions": len(records),
                "tpsMean": mean_tps,
                "tpsMin": min(tps_values),
                "tpsMax": max(tps_values),
                "tpsPopulationStddev": statistics.pstdev(tps_values),
                "tpsCoefficientOfVariation": (
                    statistics.pstdev(tps_values) / mean_tps if mean_tps else None
                ),
                "p99MeanMs": statistics.mean(p99_values),
                "p99MinMs": min(p99_values),
                "p99MaxMs": max(p99_values),
                "transactionFailures": sum(
                    sum(record["failures"].values()) for record in records
                ),
                "lateTransactions": sum(
                    int(record["lateTransactions"]) for record in records
                ),
            }
        )
    return summaries


def _write_scripts(directory: Path, device_count: int) -> tuple[Path, ...]:
    point = directory / "point-membership.sql"
    window = directory / "window-scan.sql"
    update = directory / "position-update.sql"
    point.write_text(
        f"""\\set device_id random(1, {device_count})
BEGIN;
SELECT count(r.name)
FROM live_positions AS p
LEFT JOIN regions AS r ON ST_Covers(r.geom, p.geom)
WHERE p.device_id = :device_id;
COMMIT;
""",
        encoding="utf-8",
        newline="\n",
    )
    window.write_text(
        """\\set x random(-179000, 179000)
\\set y random(-89000, 89000)
SELECT count(*)
FROM live_positions
WHERE geom && ST_MakeEnvelope(
  (:x - 1000) / 1000.0,
  (:y - 1000) / 1000.0,
  (:x + 1000) / 1000.0,
  (:y + 1000) / 1000.0,
  4326
);
""",
        encoding="utf-8",
        newline="\n",
    )
    update.write_text(
        f"""\\set device_id random(1, {device_count})
\\set x random(-180000, 180000)
\\set y random(-90000, 90000)
BEGIN;
UPDATE live_positions
SET observed_at = clock_timestamp(),
    geom = ST_SetSRID(ST_MakePoint(:x / 1000.0, :y / 1000.0), 4326),
    version = version + 1
WHERE device_id = :device_id;
INSERT INTO live_events(device_id, recorded_at, region, geom)
SELECT p.device_id, clock_timestamp(), r.name, p.geom
FROM live_positions AS p
LEFT JOIN LATERAL (
  SELECT name
  FROM regions
  WHERE ST_Covers(regions.geom, p.geom)
  ORDER BY name
  LIMIT 1
) AS r ON true
WHERE p.device_id = :device_id;
COMMIT;
""",
        encoding="utf-8",
        newline="\n",
    )
    for path in (point, window, update):
        path.chmod(0o644)
    return point, window, update


def _prepare_live_workload(container: str, device_count: int) -> dict[str, object]:
    _psql(
        container,
        f"""
        DROP TABLE IF EXISTS live_events;
        DROP TABLE IF EXISTS live_positions;
        CREATE TABLE live_positions (
          device_id integer PRIMARY KEY,
          observed_at timestamptz NOT NULL,
          geom geometry(Point, 4326) NOT NULL,
          version bigint NOT NULL DEFAULT 1
        );
        INSERT INTO live_positions(device_id, observed_at, geom)
        SELECT row_number() OVER (ORDER BY sid, sample_index)::integer,
               observed_at,
               geom
        FROM samples
        ORDER BY sid, sample_index
        LIMIT {device_count};
        CREATE INDEX live_positions_geom_gix
          ON live_positions USING GIST (geom);
        CREATE TABLE live_events (
          event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          device_id integer NOT NULL,
          recorded_at timestamptz NOT NULL,
          region text,
          geom geometry(Point, 4326) NOT NULL
        );
        CREATE INDEX live_events_device_time_idx
          ON live_events(device_id, recorded_at DESC);
        ALTER TABLE live_positions SET (
          autovacuum_vacuum_scale_factor = 0.02,
          autovacuum_analyze_scale_factor = 0.01
        );
        ANALYZE live_positions;
        CHECKPOINT;
        """,
    )
    actual = int(_psql(container, "SELECT count(*) FROM live_positions;"))
    if actual != device_count:
        raise RuntimeError(f"Expected {device_count} live devices, found {actual}")
    plan = json.loads(
        _psql(
            container,
            """
            EXPLAIN (FORMAT JSON)
            SELECT count(*)
            FROM live_positions
            WHERE geom && ST_MakeEnvelope(-10, -10, 10, 10, 4326);
            """,
        )
    )
    return {
        "devices": actual,
        "windowPlanUsesGist": _plan_uses_index(plan, "live_positions_geom_gix"),
        "windowPlan": plan,
    }


def _pgbench_command(
    container: str,
    scripts: tuple[Path, ...],
    *,
    clients: int,
    duration_seconds: int,
    latency_limit_ms: int,
    log_prefix: str | None,
    rate: int | None = None,
) -> list[str]:
    command = [
        "docker",
        "exec",
        "-e",
        f"PGPASSWORD={PASSWORD}",
        container,
        "pgbench",
        "--no-vacuum",
        "--username",
        "postgres",
        "--dbname",
        DATABASE,
        "--client",
        str(clients),
        "--jobs",
        str(min(clients, 8)),
        "--time",
        str(duration_seconds),
        "--protocol",
        "prepared",
        "--max-tries",
        "3",
        "--latency-limit",
        str(latency_limit_ms),
        "--failures-detailed",
        "--report-per-command",
    ]
    for path, weight in zip(scripts, SCRIPT_WEIGHTS, strict=True):
        command.extend(("--file", f"/benchmark/{path.name}@{weight}"))
    if log_prefix:
        command.extend(("--log", "--log-prefix", f"/tmp/{log_prefix}"))
    if rate is not None:
        command.extend(("--rate", str(rate)))
    return command


def _parse_tps(stdout: str) -> float | None:
    matches = re.findall(
        r"^tps = ([0-9.]+) \(without initial connection time\)$",
        stdout,
        flags=re.MULTILINE,
    )
    return float(matches[-1]) if matches else None


def _run_level(
    container: str,
    scripts: tuple[Path, ...],
    *,
    clients: int,
    warmup_seconds: int,
    duration_seconds: int,
    latency_limit_ms: int,
    repetition: int,
) -> dict[str, object]:
    if warmup_seconds:
        warmup = subprocess.run(
            _pgbench_command(
                container,
                scripts,
                clients=clients,
                duration_seconds=warmup_seconds,
                latency_limit_ms=latency_limit_ms,
                log_prefix=None,
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        if warmup.returncode:
            raise RuntimeError(f"pgbench warmup failed: {warmup.stderr.strip()}")
    prefix = f"pulse-{clients}-{repetition}-{uuid.uuid4().hex[:8]}"
    started = time.perf_counter()
    measured = subprocess.run(
        _pgbench_command(
            container,
            scripts,
            clients=clients,
            duration_seconds=duration_seconds,
            latency_limit_ms=latency_limit_ms,
            log_prefix=prefix,
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    wall_seconds = time.perf_counter() - started
    if measured.returncode:
        raise RuntimeError(
            f"pgbench measured run failed with {measured.returncode}: "
            f"{measured.stderr.strip()}"
        )
    logs = _docker(
        ["exec", container, "sh", "-c", f"cat /tmp/{prefix}.*"],
    ).stdout
    parsed = parse_pgbench_log(logs)
    parsed.update(
        {
            "clients": clients,
            "threads": min(clients, 8),
            "repetition": repetition,
            "warmupSeconds": warmup_seconds,
            "measurementSeconds": duration_seconds,
            "wallSeconds": wall_seconds,
            "tps": _parse_tps(measured.stdout),
            "lateTransactions": sum(
                latency > latency_limit_ms
                for line in logs.splitlines()
                if len(line.split()) >= 3 and line.split()[2].isdigit()
                for latency in (int(line.split()[2]) / 1000.0,)
            ),
            "stdout": measured.stdout,
        }
    )
    return parsed


def _run_rate(
    container: str,
    scripts: tuple[Path, ...],
    *,
    clients: int,
    rate: int,
    warmup_seconds: int,
    duration_seconds: int,
    latency_limit_ms: int,
    maximum_skip_rate: float,
    repetition: int,
) -> dict[str, object]:
    if warmup_seconds:
        warmup = subprocess.run(
            _pgbench_command(
                container,
                scripts,
                clients=clients,
                duration_seconds=warmup_seconds,
                latency_limit_ms=latency_limit_ms,
                log_prefix=None,
                rate=rate,
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        if warmup.returncode:
            raise RuntimeError(
                f"pgbench open-loop warmup failed: {warmup.stderr.strip()}"
            )
    prefix = f"pulse-rate-{rate}-{repetition}-{uuid.uuid4().hex[:8]}"
    measured = subprocess.run(
        _pgbench_command(
            container,
            scripts,
            clients=clients,
            duration_seconds=duration_seconds,
            latency_limit_ms=latency_limit_ms,
            log_prefix=prefix,
            rate=rate,
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    if measured.returncode:
        raise RuntimeError(
            f"pgbench open-loop run failed with {measured.returncode}: "
            f"{measured.stderr.strip()}"
        )
    logs = _docker(
        ["exec", container, "sh", "-c", f"cat /tmp/{prefix}.*"],
    ).stdout
    parsed = parse_pgbench_log(logs)
    skipped = int(parsed["failures"].get("skipped", 0))
    transaction_failures = sum(
        count for name, count in parsed["failures"].items() if name != "skipped"
    )
    attempted = int(parsed["transactions"]) + sum(parsed["failures"].values())
    skip_rate = skipped / attempted if attempted else None
    completed_above_limit = sum(
        latency > latency_limit_ms
        for line in logs.splitlines()
        if len(line.split()) >= 3 and line.split()[2].isdigit()
        for latency in (int(line.split()[2]) / 1000.0,)
    )
    parsed.update(
        {
            "clients": clients,
            "threads": min(clients, 8),
            "targetTps": rate,
            "repetition": repetition,
            "warmupSeconds": warmup_seconds,
            "measurementSeconds": duration_seconds,
            "reportedTps": _parse_tps(measured.stdout),
            "attemptedTransactions": attempted,
            "transactionFailures": transaction_failures,
            "skippedTransactions": skipped,
            "skipRate": skip_rate,
            "completedAboveLatencyLimit": completed_above_limit,
            "sloPass": (
                transaction_failures == 0
                and skip_rate is not None
                and skip_rate <= maximum_skip_rate
                and parsed["p99Ms"] is not None
                and parsed["p99Ms"] <= latency_limit_ms
            ),
            "stdout": measured.stdout,
        }
    )
    return parsed


def _crash_recovery(
    container: str,
    scripts: tuple[Path, ...],
    *,
    clients: int,
    crash_after_seconds: int,
) -> dict[str, object]:
    before = _psql(
        container,
        "SELECT count(*), coalesce(sum(version), 0) FROM live_positions;",
    ).split("|")
    command = _pgbench_command(
        container,
        scripts,
        clients=clients,
        duration_seconds=max(crash_after_seconds * 4, 20),
        latency_limit_ms=1000,
        log_prefix=None,
    )
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(crash_after_seconds)
    _docker(["kill", "--signal", "KILL", container])
    process.communicate(timeout=30)
    started = time.perf_counter()
    _docker(["start", container])
    _wait_ready(container, initial_creation=False)
    recovery_seconds = time.perf_counter() - started
    after = _psql(
        container,
        """
        SELECT count(*), coalesce(sum(version), 0),
               (SELECT count(*) FROM live_events),
               (SELECT bool_and(indisvalid AND indisready)
                  FROM pg_index
                 WHERE indexrelid IN (
                   'live_positions_geom_gix'::regclass,
                   'live_events_device_time_idx'::regclass
                 ))
        FROM live_positions;
        """,
    ).split("|")
    plan = json.loads(
        _psql(
            container,
            """
            EXPLAIN (FORMAT JSON)
            SELECT count(*) FROM live_positions
            WHERE geom && ST_MakeEnvelope(-10, -10, 10, 10, 4326);
            """,
        )
    )
    probe = subprocess.run(
        _pgbench_command(
            container,
            scripts,
            clients=1,
            duration_seconds=2,
            latency_limit_ms=1000,
            log_prefix=None,
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    verified = (
        int(after[0]) == int(before[0])
        and int(after[1]) >= int(before[1])
        and int(after[2]) > 0
        and after[3] == "t"
        and _plan_uses_index(plan, "live_positions_geom_gix")
        and probe.returncode == 0
    )
    return {
        "signal": "SIGKILL",
        "clientsDuringCrash": clients,
        "crashAfterSeconds": crash_after_seconds,
        "recoverySeconds": recovery_seconds,
        "rowsBefore": int(before[0]),
        "rowsAfter": int(after[0]),
        "versionSumBefore": int(before[1]),
        "versionSumAfter": int(after[1]),
        "eventRowsAfter": int(after[2]),
        "indexesValidAndReady": after[3] == "t",
        "windowPlanUsesGistAfter": _plan_uses_index(plan, "live_positions_geom_gix"),
        "postRecoveryMixedProbe": probe.returncode == 0,
        "verified": verified,
    }


def run_experiment(
    dataset_path: str | Path,
    *,
    image: str = DEFAULT_IMAGE,
    clients: Iterable[int] = (1, 4, 8, 16, 32),
    warmup_seconds: int = 15,
    duration_seconds: int = 60,
    repetitions: int = 1,
    device_count: int = 50_000,
    latency_limit_ms: int = 1000,
    crash_clients: int = 16,
    crash_after_seconds: int = 5,
) -> dict[str, object]:
    if warmup_seconds < 0 or duration_seconds < 1 or repetitions < 1:
        raise ValueError("Invalid benchmark duration or repetition count")
    client_levels = tuple(clients)
    if not client_levels or any(value < 1 for value in client_levels):
        raise ValueError("Client counts must be positive")
    path = Path(dataset_path)
    dataset = load_ibtracs(path)
    point_count = sum(len(track.points) for track in dataset.tracks)
    if device_count > point_count:
        raise ValueError(
            f"device_count {device_count} exceeds available points {point_count}"
        )
    token = uuid.uuid4().hex[:12]
    container = f"pulse-postgis-concurrency-{token}"
    volume = f"pulse-postgis-concurrency-{token}"
    pull_seconds, image_id = _ensure_image(image)
    _docker(["volume", "create", volume])
    levels: list[dict[str, object]] = []
    try:
        with tempfile.TemporaryDirectory(
            prefix="pulse-postgis-concurrency-"
        ) as temporary:
            directory = Path(temporary)
            directory.chmod(0o755)
            _write_database_inputs(directory, dataset.tracks)
            scripts = _write_scripts(directory, device_count)
            _start_container(
                container,
                volume,
                directory,
                image,
                initial_creation=True,
            )
            _load_schema(container)
            live = _prepare_live_workload(container, device_count)
            durability = dict(
                line.split("=", 1)
                for line in _psql(
                    container,
                    """
                    SELECT 'fsync=' || current_setting('fsync')
                    UNION ALL SELECT 'synchronous_commit=' || current_setting('synchronous_commit')
                    UNION ALL SELECT 'full_page_writes=' || current_setting('full_page_writes')
                    UNION ALL SELECT 'wal_level=' || current_setting('wal_level')
                    UNION ALL SELECT 'max_connections=' || current_setting('max_connections');
                    """,
                ).splitlines()
            )
            versions = _psql(
                container,
                "SELECT version() || E'\n' || PostGIS_Full_Version();",
            ).splitlines()
            for client_count in client_levels:
                for repetition in range(1, repetitions + 1):
                    levels.append(
                        _run_level(
                            container,
                            scripts,
                            clients=client_count,
                            warmup_seconds=warmup_seconds,
                            duration_seconds=duration_seconds,
                            latency_limit_ms=latency_limit_ms,
                            repetition=repetition,
                        )
                    )
            recovery = _crash_recovery(
                container,
                scripts,
                clients=crash_clients,
                crash_after_seconds=crash_after_seconds,
            )
            final_counts = _psql(
                container,
                "SELECT count(*), (SELECT count(*) FROM live_events) FROM live_positions;",
            ).split("|")
        dataset_name, source_url = source_descriptor(path)
        all_zero_failures = all(not level["failures"] for level in levels)
        all_tps = all(level["tps"] is not None for level in levels)
        return {
            "experiment": "postgis-production-concurrency-v1",
            "generatedAt": datetime.now(UTC).isoformat(),
            "claimBoundary": (
                "Durable single-node PostgreSQL/PostGIS mixed spatial workload "
                "using pgbench prepared statements, weighted reads/writes, "
                "per-transaction latency logs, GiST plan checks, and SIGKILL "
                "recovery. This is production-oriented evidence, not a claim "
                "of multi-node high availability, cloud SLA, or universal "
                "capacity independent of the reported host."
            ),
            "dataset": {
                "name": dataset_name,
                "doi": SOURCE_DOI,
                "sourceUrl": source_url,
                "path": path.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "tracks": len(dataset.tracks),
                "points": point_count,
            },
            "database": {
                "image": image,
                "imageId": image_id,
                "postgresVersion": versions[0] if versions else "unknown",
                "postgisVersion": versions[1] if len(versions) > 1 else "unknown",
                "durability": durability,
                "liveWorkload": live,
                "finalLiveRows": int(final_counts[0]),
                "finalEventRows": int(final_counts[1]),
            },
            "protocol": {
                "clients": list(client_levels),
                "warmupSecondsPerLevel": warmup_seconds,
                "measurementSecondsPerLevel": duration_seconds,
                "repetitions": repetitions,
                "deviceCount": device_count,
                "scriptWeights": dict(zip(SCRIPT_NAMES, SCRIPT_WEIGHTS, strict=True)),
                "preparedStatements": True,
                "latencyLimitMs": latency_limit_ms,
            },
            "levels": levels,
            "summaryByClients": summarize_levels(levels),
            "crashRecovery": recovery,
            "acceptance": {
                "zeroTransactionFailures": all_zero_failures,
                "allLevelsReportTps": all_tps,
                "windowPlanUsesGist": live["windowPlanUsesGist"],
                "crashRecoveryVerified": recovery["verified"],
                "passes": all_zero_failures
                and all_tps
                and live["windowPlanUsesGist"]
                and recovery["verified"],
            },
            "timingSeconds": {"imagePull": pull_seconds},
            "environment": _runtime_environment(container),
        }
    finally:
        _docker(["rm", "--force", container], check=False)
        _docker(["volume", "rm", "--force", volume], check=False)


def run_slo_experiment(
    dataset_path: str | Path,
    *,
    image: str = DEFAULT_IMAGE,
    rates: Iterable[int] = (1_000, 5_000, 10_000, 15_000, 20_000, 25_000),
    clients: int = 32,
    warmup_seconds: int = 10,
    duration_seconds: int = 30,
    repetitions: int = 1,
    device_count: int = 50_000,
    latency_limit_ms: int = 20,
    maximum_skip_rate: float = 0.001,
) -> dict[str, object]:
    rate_levels = tuple(rates)
    if not rate_levels or any(rate < 1 for rate in rate_levels):
        raise ValueError("Rates must be positive")
    if clients < 1 or warmup_seconds < 0 or duration_seconds < 1:
        raise ValueError("Invalid SLO benchmark parameters")
    if not 0 <= maximum_skip_rate < 1:
        raise ValueError("maximum_skip_rate must be in [0, 1)")
    path = Path(dataset_path)
    dataset = load_ibtracs(path)
    point_count = sum(len(track.points) for track in dataset.tracks)
    if device_count > point_count:
        raise ValueError(
            f"device_count {device_count} exceeds available points {point_count}"
        )
    token = uuid.uuid4().hex[:12]
    container = f"pulse-postgis-slo-{token}"
    volume = f"pulse-postgis-slo-{token}"
    pull_seconds, image_id = _ensure_image(image)
    _docker(["volume", "create", volume])
    levels: list[dict[str, object]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="pulse-postgis-slo-") as temporary:
            directory = Path(temporary)
            directory.chmod(0o755)
            _write_database_inputs(directory, dataset.tracks)
            scripts = _write_scripts(directory, device_count)
            _start_container(
                container,
                volume,
                directory,
                image,
                initial_creation=True,
            )
            _load_schema(container)
            live = _prepare_live_workload(container, device_count)
            durability = dict(
                line.split("=", 1)
                for line in _psql(
                    container,
                    """
                    SELECT 'fsync=' || current_setting('fsync')
                    UNION ALL SELECT 'synchronous_commit=' || current_setting('synchronous_commit')
                    UNION ALL SELECT 'full_page_writes=' || current_setting('full_page_writes');
                    """,
                ).splitlines()
            )
            for rate in rate_levels:
                for repetition in range(1, repetitions + 1):
                    levels.append(
                        _run_rate(
                            container,
                            scripts,
                            clients=clients,
                            rate=rate,
                            warmup_seconds=warmup_seconds,
                            duration_seconds=duration_seconds,
                            latency_limit_ms=latency_limit_ms,
                            maximum_skip_rate=maximum_skip_rate,
                            repetition=repetition,
                        )
                    )
            final_events = int(_psql(container, "SELECT count(*) FROM live_events;"))
        per_rate = []
        for rate in rate_levels:
            records = [level for level in levels if level["targetTps"] == rate]
            per_rate.append(
                {
                    "targetTps": rate,
                    "repetitions": len(records),
                    "allSloPass": all(record["sloPass"] for record in records),
                    "reportedTpsMean": statistics.mean(
                        float(record["reportedTps"]) for record in records
                    ),
                    "p99MeanMs": statistics.mean(
                        float(record["p99Ms"]) for record in records
                    ),
                    "p99MaxMs": max(float(record["p99Ms"]) for record in records),
                    "scheduleLagP99MaxMs": max(
                        float(record["scheduleLag"]["p99Ms"] or 0) for record in records
                    ),
                    "transactionFailures": sum(
                        int(record["transactionFailures"]) for record in records
                    ),
                    "skippedTransactions": sum(
                        int(record["skippedTransactions"]) for record in records
                    ),
                    "skipRateMax": max(float(record["skipRate"]) for record in records),
                    "completedAboveLatencyLimit": sum(
                        int(record["completedAboveLatencyLimit"]) for record in records
                    ),
                }
            )
        passing_rates = [
            record["targetTps"] for record in per_rate if record["allSloPass"]
        ]
        dataset_name, source_url = source_descriptor(path)
        return {
            "experiment": "postgis-open-loop-slo-saturation-v1",
            "generatedAt": datetime.now(UTC).isoformat(),
            "claimBoundary": (
                "Open-loop Poisson arrivals generated by pgbench against the "
                "same durable mixed spatial workload. Passing means no database "
                "transaction failure, a skipped-arrival rate within the declared "
                "admission budget, and observed completion p99 at or below the "
                "stated latency limit on the reported host. It is not a universal SLA."
            ),
            "dataset": {
                "name": dataset_name,
                "doi": SOURCE_DOI,
                "sourceUrl": source_url,
                "path": path.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "tracks": len(dataset.tracks),
                "points": point_count,
            },
            "database": {
                "image": image,
                "imageId": image_id,
                "durability": durability,
                "liveWorkload": live,
                "finalEventRows": final_events,
            },
            "protocol": {
                "arrivalModel": "Poisson open-loop (--rate)",
                "ratesTps": list(rate_levels),
                "clients": clients,
                "warmupSecondsPerRate": warmup_seconds,
                "measurementSecondsPerRate": duration_seconds,
                "repetitions": repetitions,
                "latencyLimitMs": latency_limit_ms,
                "maximumSkipRate": maximum_skip_rate,
                "deviceCount": device_count,
                "scriptWeights": dict(zip(SCRIPT_NAMES, SCRIPT_WEIGHTS, strict=True)),
            },
            "levels": levels,
            "summaryByRate": per_rate,
            "capacity": {
                "maximumPassingTargetTps": max(passing_rates)
                if passing_rates
                else None,
                "testedUpperTargetTps": max(rate_levels),
                "saturationObserved": any(
                    not record["allSloPass"] for record in per_rate
                ),
            },
            "acceptance": {
                "windowPlanUsesGist": live["windowPlanUsesGist"],
                "allRunsProducedLatencyLogs": all(
                    level["transactions"] for level in levels
                ),
                "valid": live["windowPlanUsesGist"]
                and all(level["transactions"] for level in levels),
            },
            "timingSeconds": {"imagePull": pull_seconds},
            "environment": _runtime_environment(container),
        }
    finally:
        _docker(["rm", "--force", container], check=False)
        _docker(["volume", "rm", "--force", volume], check=False)


def render_slo_markdown(result: dict[str, object]) -> str:
    protocol = result["protocol"]
    capacity = result["capacity"]
    summaries = result["summaryByRate"]
    assert isinstance(protocol, dict)
    assert isinstance(capacity, dict)
    assert isinstance(summaries, list)
    rows = [
        "# PostGIS open-loop spatial SLO saturation",
        "",
        f"- Latency limit: {protocol['latencyLimitMs']} ms",
        f"- Maximum skipped-arrival rate: {100 * protocol['maximumSkipRate']:.3f}%",
        f"- Maximum passing target: {capacity['maximumPassingTargetTps']} TPS",
        f"- Saturation observed: **{capacity['saturationObserved']}**",
        "",
        "| Target TPS | reported TPS | mean p99 ms | max lag p99 ms | failures | skipped | max skip rate | pass |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rows.extend(
        "| {targetTps} | {reportedTpsMean:.2f} | {p99MeanMs:.3f} | "
        "{scheduleLagP99MaxMs:.3f} | {transactionFailures} | "
        "{skippedTransactions} | {skipRateMax:.4%} | {allSloPass} |".format(**summary)
        for summary in summaries
    )
    rows.extend(("", "## Claim boundary", "", str(result["claimBoundary"]), ""))
    return "\n".join(rows)


def render_markdown(result: dict[str, object]) -> str:
    protocol = result["protocol"]
    recovery = result["crashRecovery"]
    acceptance = result["acceptance"]
    levels = result["levels"]
    summaries = result["summaryByClients"]
    assert isinstance(protocol, dict)
    assert isinstance(recovery, dict)
    assert isinstance(acceptance, dict)
    assert isinstance(levels, list)
    assert isinstance(summaries, list)
    rows = [
        "# PostGIS production-oriented concurrency benchmark",
        "",
        f"- Devices: {protocol['deviceCount']:,}",
        f"- Warm-up / measurement per level: {protocol['warmupSecondsPerLevel']} s / {protocol['measurementSecondsPerLevel']} s",
        f"- Crash recovery verified: **{recovery['verified']}**",
        f"- Acceptance passes: **{acceptance['passes']}**",
        "",
        "| Clients | Rep | TPS | p50 ms | p95 ms | p99 ms | failures |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for level in levels:
        failure_count = sum(level["failures"].values())
        rows.append(
            "| {clients} | {repetition} | {tps:.2f} | {p50Ms:.3f} | "
            "{p95Ms:.3f} | {p99Ms:.3f} | {failure_count} |".format(
                **level,
                failure_count=failure_count,
            )
        )
    rows.extend(
        (
            "",
            "## Three-run summary",
            "",
            "| Clients | mean TPS | TPS CV | mean p99 ms | p99 range ms |",
            "|---:|---:|---:|---:|---:|",
        )
    )
    rows.extend(
        "| {clients} | {tpsMean:.2f} | {tpsCoefficientOfVariation:.3f} | "
        "{p99MeanMs:.3f} | {p99MinMs:.3f}--{p99MaxMs:.3f} |".format(**summary)
        for summary in summaries
    )
    rows.extend(("", "## Claim boundary", "", str(result["claimBoundary"]), ""))
    return "\n".join(rows)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def _clients(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(item) for item in value.split(",") if item)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    if not parsed or any(item < 1 for item in parsed):
        raise argparse.ArgumentTypeError("clients must be positive integers")
    return parsed


def _rates(value: str) -> tuple[int, ...]:
    return _clients(value)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-postgis-concurrency",
        description="Run the durable concurrent PostGIS workload.",
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--clients", type=_clients, default=(1, 4, 8, 16, 32))
    parser.add_argument("--warmup-seconds", type=int, default=15)
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--device-count", type=int, default=50_000)
    parser.add_argument("--latency-limit-ms", type=int, default=1000)
    parser.add_argument("--crash-clients", type=int, default=16)
    parser.add_argument("--crash-after-seconds", type=int, default=5)
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-acceptance", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_experiment(
            arguments.data,
            image=arguments.image,
            clients=arguments.clients,
            warmup_seconds=arguments.warmup_seconds,
            duration_seconds=arguments.duration_seconds,
            repetitions=arguments.repetitions,
            device_count=arguments.device_count,
            latency_limit_ms=arguments.latency_limit_ms,
            crash_clients=arguments.crash_clients,
            crash_after_seconds=arguments.crash_after_seconds,
        )
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    if arguments.require_acceptance:
        acceptance = result["acceptance"]
        assert isinstance(acceptance, dict)
        if not acceptance["passes"]:
            raise SystemExit(1)


def main_slo() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-postgis-slo",
        description="Run the open-loop PostGIS spatial SLO saturation sweep.",
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument(
        "--rates", type=_rates, default=(1_000, 5_000, 10_000, 15_000, 20_000, 25_000)
    )
    parser.add_argument("--clients", type=int, default=32)
    parser.add_argument("--warmup-seconds", type=int, default=10)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--device-count", type=int, default=50_000)
    parser.add_argument("--latency-limit-ms", type=int, default=20)
    parser.add_argument("--maximum-skip-rate", type=float, default=0.001)
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-valid", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_slo_experiment(
            arguments.data,
            image=arguments.image,
            rates=arguments.rates,
            clients=arguments.clients,
            warmup_seconds=arguments.warmup_seconds,
            duration_seconds=arguments.duration_seconds,
            repetitions=arguments.repetitions,
            device_count=arguments.device_count,
            latency_limit_ms=arguments.latency_limit_ms,
            maximum_skip_rate=arguments.maximum_skip_rate,
        )
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_slo_markdown(result))
    print(rendered, end="")
    if arguments.require_valid:
        acceptance = result["acceptance"]
        assert isinstance(acceptance, dict)
        if not acceptance["valid"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
