"""Real-trajectory geofence parity experiment using NOAA IBTrACS."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

from ..geometry import CRS84, Point, Polygon
from ..model import SpatialWorld
from ..runtime import SpatialRuntime


SOURCE_URL = (
    "https://www.ncei.noaa.gov/data/"
    "international-best-track-archive-for-climate-stewardship-ibtracs/"
    "v04r01/access/csv/ibtracs.last3years.list.v04r01.csv"
)
SINCE_1980_SOURCE_URL = (
    "https://www.ncei.noaa.gov/data/"
    "international-best-track-archive-for-climate-stewardship-ibtracs/"
    "v04r01/access/csv/ibtracs.since1980.list.v04r01.csv"
)
SOURCE_DOI = "10.25921/82ty-9e16"
PINNED_SINCE_1980_SHA256 = (
    "9f3db13f92bdc47d49edcdec677e64bafe9f20c67529552a65a10882205bb7fe"
)
PINNED_SINCE_1980_BYTES = 142_982_689
STUDY_ZONE_NAME = "NorthAtlanticStudyZone"
STUDY_ZONE_COORDINATES = (
    (-100.0, 5.0),
    (-100.0, 45.0),
    (-75.0, 45.0),
    (-60.0, 35.0),
    (-15.0, 35.0),
    (-15.0, 5.0),
    (-100.0, 5.0),
)


class ExperimentDependencyError(RuntimeError):
    """Raised when the optional GEOS reference dependency is unavailable."""


@dataclass(frozen=True, slots=True)
class TrackPoint:
    observed_at: datetime
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class Track:
    sid: str
    name: str
    season: int
    basin: str
    points: tuple[TrackPoint, ...]


@dataclass(frozen=True, slots=True)
class LoadedDataset:
    tracks: tuple[Track, ...]
    rows_total: int
    rows_valid: int
    rows_filtered_track_type: int
    rows_invalid: int


@dataclass(frozen=True, slots=True)
class TransitionLabel:
    sid: str
    index: int
    observed_at: datetime
    kind: str | None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_descriptor(
    path: str | Path, source_url: str | None = None
) -> tuple[str, str]:
    """Return an accurate label and official URL for a supported subset."""

    source_path = Path(path)
    evidence = f"{source_path.name} {source_url or ''}".lower()
    if "since1980" in evidence:
        return (
            "NOAA IBTrACS v04r01 since1980 list CSV",
            source_url or SINCE_1980_SOURCE_URL,
        )
    if "last3years" in evidence:
        return (
            "NOAA IBTrACS v04r01 last3years list CSV",
            source_url or SOURCE_URL,
        )
    return (
        "NOAA IBTrACS v04r01 normalized main-track snapshot",
        source_url or SOURCE_URL,
    )


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip())
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _normalize_longitude(value: float) -> float:
    normalized = value if -180 <= value <= 180 else ((value + 180) % 360) - 180
    # Stabilize decimal CSV coordinates after modulo arithmetic (for example,
    # 180.4 must round-trip as -179.6 rather than -179.60000000000002).
    return round(normalized, 12)


def load_ibtracs(path: str | Path, max_tracks: int | None = None) -> LoadedDataset:
    """Load main-track positions from an IBTrACS list CSV."""

    source_path = Path(path)
    buckets: dict[str, list[TrackPoint]] = {}
    metadata: dict[str, tuple[str, int, str]] = {}
    rows_total = 0
    rows_valid = 0
    rows_filtered = 0
    rows_invalid = 0
    with source_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {
            "SID",
            "SEASON",
            "BASIN",
            "NAME",
            "ISO_TIME",
            "LAT",
            "LON",
            "TRACK_TYPE",
        }
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"IBTrACS CSV is missing columns: {', '.join(sorted(missing))}"
            )
        for row in reader:
            rows_total += 1
            sid = (row.get("SID") or "").strip()
            if not sid:
                rows_invalid += 1
                continue
            if (row.get("TRACK_TYPE") or "").strip().lower() != "main":
                rows_filtered += 1
                continue
            try:
                season = int((row.get("SEASON") or "").strip())
                latitude = float((row.get("LAT") or "").strip())
                longitude = _normalize_longitude(
                    float((row.get("LON") or "").strip())
                )
                observed_at = _parse_time(row.get("ISO_TIME") or "")
            except (TypeError, ValueError):
                rows_invalid += 1
                continue
            if not -90 <= latitude <= 90:
                rows_invalid += 1
                continue
            point = TrackPoint(observed_at, latitude, longitude)
            buckets.setdefault(sid, []).append(point)
            metadata.setdefault(
                sid,
                (
                    (row.get("NAME") or "").strip(),
                    season,
                    (row.get("BASIN") or "").strip(),
                ),
            )
            rows_valid += 1

    tracks: list[Track] = []
    for sid in sorted(buckets):
        points = sorted(
            set(buckets[sid]),
            key=lambda point: (
                point.observed_at,
                point.longitude,
                point.latitude,
            ),
        )
        name, season, basin = metadata[sid]
        tracks.append(Track(sid, name, season, basin, tuple(points)))
    if max_tracks is not None:
        if max_tracks <= 0:
            raise ValueError("max_tracks must be positive")
        tracks = tracks[:max_tracks]
    return LoadedDataset(
        tuple(tracks),
        rows_total,
        rows_valid,
        rows_filtered,
        rows_invalid,
    )


def write_normalized_snapshot(
    dataset: LoadedDataset,
    destination: str | Path,
) -> Path:
    """Write the selected IBTrACS fields in deterministic track/time order."""

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            (
                "SID",
                "SEASON",
                "BASIN",
                "NAME",
                "ISO_TIME",
                "LAT",
                "LON",
                "TRACK_TYPE",
            )
        )
        for track in dataset.tracks:
            for point in track.points:
                writer.writerow(
                    (
                        track.sid,
                        track.season,
                        track.basin,
                        track.name,
                        point.observed_at.astimezone(UTC).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        format(point.latitude, ".10g"),
                        format(point.longitude, ".10g"),
                        "main",
                    )
                )
    return target


def download_ibtracs(
    url: str | Path,
    destination: str | Path,
    *,
    force: bool = False,
) -> Path:
    """Download a dataset atomically, preserving an existing file by default."""

    target = Path(destination)
    if target.exists() and not force:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(f"{target.suffix}.part")
    request = Request(
        str(url),
            headers={"User-Agent": "PULSE-Spatial/0.1 research"},
    )
    try:
        with urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def _internal_labels(
    tracks: Iterable[Track],
    region: Polygon,
) -> tuple[TransitionLabel, ...]:
    labels: list[TransitionLabel] = []
    for track in tracks:
        if len(track.points) < 2:
            continue
        first = track.points[0]
        world = SpatialWorld(
            regions={STUDY_ZONE_NAME: region},
            positions={track.sid: Point(first.longitude, first.latitude, CRS84)},
        )
        runtime = SpatialRuntime(world)
        for index, point in enumerate(track.points[1:], start=1):
            events = runtime.move(
                track.sid,
                Point(point.longitude, point.latitude, CRS84),
            )
            kind = events[0].kind.value if events else None
            labels.append(TransitionLabel(track.sid, index, point.observed_at, kind))
    return tuple(labels)


def _reference_labels(
    tracks: Iterable[Track],
) -> tuple[TransitionLabel, ...]:
    try:
        from shapely import Point as ReferencePoint
        from shapely import Polygon as ReferencePolygon
        from shapely import covers
    except ImportError as error:
        raise ExperimentDependencyError(
            "IBTrACS reference execution requires the optional test or validation "
            "dependencies"
        ) from error

    region = ReferencePolygon(STUDY_ZONE_COORDINATES)
    labels: list[TransitionLabel] = []
    for track in tracks:
        if len(track.points) < 2:
            continue
        first = track.points[0]
        was_inside = bool(
            covers(region, ReferencePoint(first.longitude, first.latitude))
        )
        for index, point in enumerate(track.points[1:], start=1):
            is_inside = bool(
                covers(region, ReferencePoint(point.longitude, point.latitude))
            )
            kind = None
            if not was_inside and is_inside:
                kind = "enters"
            elif was_inside and not is_inside:
                kind = "leaves"
            labels.append(TransitionLabel(track.sid, index, point.observed_at, kind))
            was_inside = is_inside
    return tuple(labels)


def _timed(function, repetitions: int):
    samples: list[float] = []
    value = None
    for _ in range(repetitions):
        started = time.perf_counter()
        value = function()
        samples.append(time.perf_counter() - started)
    return value, tuple(samples)


def _event_counts(labels: Iterable[TransitionLabel]) -> dict[str, int]:
    result = {"enters": 0, "leaves": 0}
    for label in labels:
        if label.kind is not None:
            result[label.kind] += 1
    return result


def run_experiment(
    dataset_path: str | Path,
    *,
    source_url: str = SOURCE_URL,
    repetitions: int = 3,
    max_tracks: int | None = None,
) -> dict[str, object]:
    """Execute internal and GEOS geofence derivation over real trajectories."""

    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    path = Path(dataset_path)
    loaded = load_ibtracs(path, max_tracks=max_tracks)
    region = Polygon.from_xy(STUDY_ZONE_COORDINATES, CRS84)
    internal_labels, internal_times = _timed(
        lambda: _internal_labels(loaded.tracks, region),
        repetitions,
    )
    reference_labels, reference_times = _timed(
        lambda: _reference_labels(loaded.tracks),
        repetitions,
    )
    assert internal_labels is not None
    assert reference_labels is not None
    if len(internal_labels) != len(reference_labels):
        raise RuntimeError("Internal and reference paths produced different workloads")

    mismatches: list[dict[str, object]] = []
    event_union = 0
    event_matches = 0
    eventful_tracks: set[str] = set()
    for internal, reference in zip(internal_labels, reference_labels):
        if (
            internal.sid != reference.sid
            or internal.index != reference.index
            or internal.observed_at != reference.observed_at
        ):
            raise RuntimeError("Internal and reference transition ordering differs")
        if internal.kind is not None or reference.kind is not None:
            event_union += 1
            eventful_tracks.add(internal.sid)
            if internal.kind == reference.kind:
                event_matches += 1
        if internal.kind != reference.kind and len(mismatches) < 20:
            mismatches.append(
                {
                    "sid": internal.sid,
                    "transitionIndex": internal.index,
                    "observedAt": internal.observed_at.isoformat(),
                    "internal": internal.kind,
                    "reference": reference.kind,
                }
            )

    transition_count = len(internal_labels)
    mismatch_count = sum(
        internal.kind != reference.kind
        for internal, reference in zip(internal_labels, reference_labels)
    )
    points = sum(len(track.points) for track in loaded.tracks)
    replayed_tracks = sum(len(track.points) >= 2 for track in loaded.tracks)
    timestamps = [
        point.observed_at for track in loaded.tracks for point in track.points
    ]
    seasons = [track.season for track in loaded.tracks]

    try:
        import shapely

        shapely_version = shapely.__version__
        geos_version = shapely.geos_version_string
    except ImportError as error:
        raise ExperimentDependencyError(
            "Shapely is required for the reference experiment"
        ) from error

    internal_median = statistics.median(internal_times)
    reference_median = statistics.median(reference_times)
    dataset_name, canonical_source_url = source_descriptor(path, source_url)
    return {
        "experiment": "ibtracs-geofence-parity-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "claimBoundary": (
            "Feasibility and event-label parity for Point/Polygon geofences; "
            "not GeoSPARQL conformance, geodesic accuracy, prediction, or "
            "industrial performance."
        ),
        "dataset": {
            "name": dataset_name,
            "doi": SOURCE_DOI,
            "sourceUrl": canonical_source_url,
            "path": path.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
            "rowsTotal": loaded.rows_total,
            "rowsValidMainTrack": loaded.rows_valid,
            "rowsFilteredTrackType": loaded.rows_filtered_track_type,
            "rowsInvalidOrMetadata": loaded.rows_invalid,
        },
        "selection": {
            "trackType": "main",
            "coordinateReferenceSystem": CRS84,
            "studyZone": {
                "name": STUDY_ZONE_NAME,
                "status": "experiment-defined; not an official NOAA boundary",
                "polygon": [list(coordinate) for coordinate in STUDY_ZONE_COORDINATES],
                "boundaryPolicy": "coveredBy (boundary included)",
            },
            "maxTracks": max_tracks,
        },
        "workload": {
            "tracksLoaded": len(loaded.tracks),
            "tracksReplayed": replayed_tracks,
            "eventfulTracks": len(eventful_tracks),
            "points": points,
            "transitions": transition_count,
            "seasons": [min(seasons), max(seasons)] if seasons else [],
            "timeRange": (
                [min(timestamps).isoformat(), max(timestamps).isoformat()]
                if timestamps
                else []
            ),
            "basins": sorted({track.basin for track in loaded.tracks}),
        },
        "parity": {
            "matches": mismatch_count == 0,
            "transitionMismatches": mismatch_count,
            "transitionAgreement": (
                (transition_count - mismatch_count) / transition_count
                if transition_count
                else 1.0
            ),
            "eventBearingTransitions": event_union,
            "eventAgreement": (
                event_matches / event_union if event_union else 1.0
            ),
            "internalEvents": _event_counts(internal_labels),
            "referenceEvents": _event_counts(reference_labels),
            "mismatchSample": mismatches,
        },
        "timing": {
            "repetitions": repetitions,
            "internalSeconds": list(internal_times),
            "referenceSeconds": list(reference_times),
            "internalMedianSeconds": internal_median,
            "referenceMedianSeconds": reference_median,
            "internalTransitionsPerSecond": (
                transition_count / internal_median if internal_median else None
            ),
            "referenceTransitionsPerSecond": (
                transition_count / reference_median if reference_median else None
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "shapely": shapely_version,
            "geos": geos_version,
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    dataset = result["dataset"]
    workload = result["workload"]
    parity = result["parity"]
    timing = result["timing"]
    environment = result["environment"]
    assert isinstance(dataset, dict)
    assert isinstance(workload, dict)
    assert isinstance(parity, dict)
    assert isinstance(timing, dict)
    assert isinstance(environment, dict)
    lines = [
        "# IBTrACS geofence parity result",
        "",
        f"Generated: `{result['generatedAt']}`",
        "",
        "## Dataset",
        "",
        f"- Source: {dataset['name']}",
        f"- DOI: `{dataset['doi']}`",
        f"- SHA-256: `{dataset['sha256']}`",
        f"- Valid main-track rows: {dataset['rowsValidMainTrack']:,}",
    ]
    snapshot = result.get("snapshot")
    if isinstance(snapshot, dict):
        lines.extend(
            (
                f"- Normalized snapshot: `{snapshot['path']}`",
                f"- Snapshot SHA-256: `{snapshot['sha256']}`",
            )
        )
    lines.extend(
        (
            "",
            "## Workload",
            "",
            f"- Tracks loaded: {workload['tracksLoaded']:,}",
            f"- Tracks replayed: {workload['tracksReplayed']:,}",
            f"- Points: {workload['points']:,}",
            f"- Transitions: {workload['transitions']:,}",
            f"- Event-bearing transitions: {parity['eventBearingTransitions']:,}",
            "",
            "## Result",
            "",
            f"- Exact parity: **{parity['matches']}**",
            f"- Transition mismatches: {parity['transitionMismatches']:,}",
            f"- Transition agreement: {parity['transitionAgreement']:.6%}",
            f"- Event agreement: {parity['eventAgreement']:.6%}",
            f"- Internal events: `{parity['internalEvents']}`",
            f"- Reference events: `{parity['referenceEvents']}`",
            "",
            "## Timing",
            "",
            f"- Internal median: {timing['internalMedianSeconds']:.6f} s",
            f"- GEOS median: {timing['referenceMedianSeconds']:.6f} s",
            "",
            "## Environment",
            "",
            f"- Python: `{environment['python']}`",
            f"- Shapely: `{environment['shapely']}`",
            f"- GEOS: `{environment['geos']}`",
            "",
            "## Claim boundary",
            "",
            str(result["claimBoundary"]),
            "",
        )
    )
    return "\n".join(lines)


def _write_text(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-ibtracs",
        description="Replay NOAA IBTrACS trajectories through a PULSE-S geofence.",
    )
    parser.add_argument(
        "--data",
        default=".data/ibtracs.last3years.list.v04r01.csv",
        help="local IBTrACS CSV path",
    )
    parser.add_argument("--url", default=SOURCE_URL, help="dataset source URL")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument(
        "--expect-sha256",
        help="reject the input unless its SHA-256 equals this hex digest",
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--max-tracks", type=int)
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument(
        "--output-snapshot",
        help="write a deterministic narrow CSV containing the replayed tracks",
    )
    parser.add_argument("--require-parity", action="store_true")
    arguments = parser.parse_args()

    try:
        data_path = Path(arguments.data)
        if arguments.download or arguments.force_download:
            data_path = download_ibtracs(
                arguments.url,
                data_path,
                force=arguments.force_download,
            )
        if not data_path.is_file():
            parser.error(
                f"dataset not found: {data_path}; pass --download to fetch it"
            )
        if arguments.expect_sha256:
            actual_sha256 = _sha256(data_path)
            if actual_sha256.lower() != arguments.expect_sha256.lower():
                raise ValueError(
                    "dataset SHA-256 mismatch: "
                    f"expected {arguments.expect_sha256.lower()}, got {actual_sha256}"
                )
        result = run_experiment(
            data_path,
            source_url=arguments.url,
            repetitions=arguments.repetitions,
            max_tracks=arguments.max_tracks,
        )
        if arguments.output_snapshot:
            snapshot_path = Path(arguments.output_snapshot)
            if snapshot_path.resolve() == data_path.resolve():
                raise ValueError("output snapshot must differ from the input dataset")
            snapshot_dataset = load_ibtracs(
                data_path,
                max_tracks=arguments.max_tracks,
            )
            write_normalized_snapshot(snapshot_dataset, snapshot_path)
            result["snapshot"] = {
                "path": snapshot_path.as_posix(),
                "bytes": snapshot_path.stat().st_size,
                "sha256": _sha256(snapshot_path),
                "columns": [
                    "SID",
                    "SEASON",
                    "BASIN",
                    "NAME",
                    "ISO_TIME",
                    "LAT",
                    "LON",
                    "TRACK_TYPE",
                ],
            }
    except (OSError, ValueError, ExperimentDependencyError) as error:
        parser.error(str(error))

    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if arguments.output_json:
        _write_text(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write_text(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    if arguments.require_parity and not result["parity"]["matches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
