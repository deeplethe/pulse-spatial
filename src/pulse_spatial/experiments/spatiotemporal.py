"""Multi-zone, duration-qualified real-trajectory parity experiment."""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, TypeVar

from ..geometry import CRS84, Point, Polygon, covered_by
from ..model import SpatialWorld
from ..runtime import (
    EventKind,
    SustainedEventSpec,
    TemporalSpatialRuntime,
)
from .ibtracs import SOURCE_DOI, Track, _sha256, load_ibtracs, source_descriptor


STUDY_ZONES: tuple[tuple[str, tuple[tuple[float, float], ...]], ...] = (
    (
        "EquatorialBand",
        (
            (-179.999, -10.0),
            (179.999, -10.0),
            (179.999, 10.0),
            (-179.999, 10.0),
            (-179.999, -10.0),
        ),
    ),
    (
        "NorthernTropics",
        (
            (-179.999, 10.0),
            (179.999, 10.0),
            (179.999, 30.0),
            (-179.999, 30.0),
            (-179.999, 10.0),
        ),
    ),
    (
        "NorthAtlanticStudyZone",
        (
            (-100.0, 5.0),
            (-100.0, 45.0),
            (-75.0, 45.0),
            (-60.0, 35.0),
            (-15.0, 35.0),
            (-15.0, 5.0),
            (-100.0, 5.0),
        ),
    ),
    (
        "WesternPacificStudyZone",
        (
            (100.0, 0.0),
            (179.999, 0.0),
            (179.999, 45.0),
            (100.0, 45.0),
            (100.0, 0.0),
        ),
    ),
    (
        "SouthIndianStudyZone",
        (
            (20.0, -50.0),
            (120.0, -50.0),
            (120.0, 0.0),
            (20.0, 0.0),
            (20.0, -50.0),
        ),
    ),
)
DURATIONS_HOURS = (6, 12, 24)


@dataclass(frozen=True, slots=True, order=True)
class MembershipLabel:
    sid: str
    transition_index: int
    observed_at: str
    region: str
    is_covered_by: bool


@dataclass(frozen=True, slots=True, order=True)
class InstantEventLabel:
    sid: str
    transition_index: int
    observed_at: str
    region: str
    kind: str


@dataclass(frozen=True, slots=True, order=True)
class SustainedEventLabel:
    sid: str
    region: str
    kind: str
    duration_seconds: float
    started_at: str
    effective_at: str
    emitted_at: str


@dataclass(frozen=True, slots=True)
class ExperimentTrace:
    memberships: tuple[MembershipLabel, ...]
    instantaneous: tuple[InstantEventLabel, ...]
    sustained: tuple[SustainedEventLabel, ...]


def _regions() -> dict[str, Polygon]:
    return {
        name: Polygon.from_xy(coordinates, CRS84)
        for name, coordinates in STUDY_ZONES
    }


def _specifications(subject: str) -> tuple[SustainedEventSpec, ...]:
    return tuple(
        SustainedEventSpec(
            f"{region}:{kind.value}:{hours}h",
            kind,
            subject,
            region,
            hours * 3600,
        )
        for region, _ in STUDY_ZONES
        for kind in (EventKind.ENTERS, EventKind.LEAVES)
        for hours in DURATIONS_HOURS
    )


def _internal_trace(tracks: Iterable[Track]) -> ExperimentTrace:
    memberships: list[MembershipLabel] = []
    instantaneous: list[InstantEventLabel] = []
    sustained: list[SustainedEventLabel] = []
    regions = _regions()
    for track in tracks:
        if len(track.points) < 2:
            continue
        first = track.points[0]
        world = SpatialWorld(
            regions=regions,
            positions={
                track.sid: Point(first.longitude, first.latitude, CRS84)
            },
        )
        runtime = TemporalSpatialRuntime(
            world,
            first.observed_at,
            sustained_events=_specifications(track.sid),
        )
        for index, point in enumerate(track.points[1:], start=1):
            result = runtime.move_at(
                track.sid,
                Point(point.longitude, point.latitude, CRS84),
                point.observed_at,
            )
            observed_at = point.observed_at.isoformat()
            for region_name, region in regions.items():
                memberships.append(
                    MembershipLabel(
                        track.sid,
                        index,
                        observed_at,
                        region_name,
                        covered_by(world.positions[track.sid], region),
                    )
                )
            instantaneous.extend(
                InstantEventLabel(
                    track.sid,
                    index,
                    observed_at,
                    event.region,
                    event.kind.value,
                )
                for event in result.instantaneous
            )
            sustained.extend(
                SustainedEventLabel(
                    track.sid,
                    event.region,
                    event.kind.value,
                    event.duration_seconds,
                    event.started_at.isoformat(),
                    event.effective_at.isoformat(),
                    event.emitted_at.isoformat(),
                )
                for event in result.sustained
            )
    return ExperimentTrace(
        tuple(sorted(memberships)),
        tuple(sorted(instantaneous)),
        tuple(sorted(sustained)),
    )


def _reference_trace(tracks: Iterable[Track]) -> ExperimentTrace:
    try:
        from shapely import Point as ReferencePoint
        from shapely import Polygon as ReferencePolygon
        from shapely import covers
    except ImportError as error:
        raise RuntimeError("Shapely is required for reference execution") from error

    polygons = {
        name: ReferencePolygon(coordinates)
        for name, coordinates in STUDY_ZONES
    }
    memberships: list[MembershipLabel] = []
    instantaneous: list[InstantEventLabel] = []
    sustained: list[SustainedEventLabel] = []
    for track in tracks:
        if len(track.points) < 2:
            continue
        first = track.points[0]
        first_point = ReferencePoint(first.longitude, first.latitude)
        previous = {
            name: bool(covers(polygon, first_point))
            for name, polygon in polygons.items()
        }
        pending: dict[
            str,
            tuple[str, EventKind, float, datetime],
        ] = {}
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

            reference_point = ReferencePoint(point.longitude, point.latitude)
            for region_name, polygon in polygons.items():
                is_inside = bool(covers(polygon, reference_point))
                memberships.append(
                    MembershipLabel(
                        track.sid,
                        index,
                        now.isoformat(),
                        region_name,
                        is_inside,
                    )
                )
                if previous[region_name] == is_inside:
                    continue
                kind = EventKind.ENTERS if is_inside else EventKind.LEAVES
                instantaneous.append(
                    InstantEventLabel(
                        track.sid,
                        index,
                        now.isoformat(),
                        region_name,
                        kind.value,
                    )
                )
                cancelled = tuple(
                    name
                    for name, value in pending.items()
                    if value[0] == region_name and value[1] is not kind
                )
                for name in cancelled:
                    del pending[name]
                for hours in DURATIONS_HOURS:
                    name = f"{region_name}:{kind.value}:{hours}h"
                    pending[name] = (region_name, kind, hours * 3600, now)
                previous[region_name] = is_inside
    return ExperimentTrace(
        tuple(sorted(memberships)),
        tuple(sorted(instantaneous)),
        tuple(sorted(sustained)),
    )


_T = TypeVar("_T")


def _timed(function: Callable[[], _T], repetitions: int) -> tuple[_T, list[float]]:
    samples: list[float] = []
    value: _T | None = None
    for _ in range(repetitions):
        started = time.perf_counter()
        value = function()
        samples.append(time.perf_counter() - started)
    assert value is not None
    return value, samples


def _difference_sample(
    internal: Iterable[object],
    reference: Iterable[object],
) -> list[dict[str, object]]:
    difference = sorted(set(internal) ^ set(reference))
    return [asdict(value) for value in difference[:20]]


def _counts_by_duration(labels: Iterable[SustainedEventLabel]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in labels:
        key = f"{int(label.duration_seconds / 3600)}h:{label.kind}"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _workload_breakdown(trace: ExperimentTrace) -> list[dict[str, object]]:
    """Disaggregate the workload so parity is not hidden by non-events."""

    rows: list[dict[str, object]] = []
    for region_name, _ in STUDY_ZONES:
        memberships = tuple(
            label for label in trace.memberships if label.region == region_name
        )
        instantaneous = tuple(
            label for label in trace.instantaneous if label.region == region_name
        )
        sustained = tuple(
            label for label in trace.sustained if label.region == region_name
        )
        rows.append(
            {
                "region": region_name,
                "transitionPairs": len(memberships),
                "insidePairs": sum(label.is_covered_by for label in memberships),
                "outsidePairs": sum(
                    not label.is_covered_by for label in memberships
                ),
                "eventPairs": len(instantaneous),
                "nonEventPairs": len(memberships) - len(instantaneous),
                "tracksWithEvents": len({label.sid for label in instantaneous}),
                "enters": sum(
                    label.kind == EventKind.ENTERS.value
                    for label in instantaneous
                ),
                "leaves": sum(
                    label.kind == EventKind.LEAVES.value
                    for label in instantaneous
                ),
                "sustainedEvents": len(sustained),
                "sustainedCounts": _counts_by_duration(sustained),
            }
        )
    return rows


def _lag_summary(labels: Iterable[SustainedEventLabel]) -> dict[str, float | int]:
    lags = sorted(
        (
            datetime.fromisoformat(label.emitted_at)
            - datetime.fromisoformat(label.effective_at)
        ).total_seconds()
        for label in labels
    )
    if not lags:
        return {
            "emittedAtDeadline": 0,
            "medianSeconds": 0.0,
            "p95Seconds": 0.0,
            "maximumSeconds": 0.0,
        }
    p95_index = max(math.ceil(len(lags) * 0.95) - 1, 0)
    return {
        "emittedAtDeadline": sum(lag == 0 for lag in lags),
        "medianSeconds": statistics.median(lags),
        "p95Seconds": lags[p95_index],
        "maximumSeconds": lags[-1],
    }


def run_experiment(
    dataset_path: str | Path,
    *,
    repetitions: int = 3,
    max_tracks: int | None = None,
) -> dict[str, object]:
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    path = Path(dataset_path)
    dataset = load_ibtracs(path, max_tracks=max_tracks)
    internal, internal_times = _timed(
        lambda: _internal_trace(dataset.tracks),
        repetitions,
    )
    reference, reference_times = _timed(
        lambda: _reference_trace(dataset.tracks),
        repetitions,
    )
    membership_mismatches = len(
        set(internal.memberships) ^ set(reference.memberships)
    )
    instant_mismatches = len(
        set(internal.instantaneous) ^ set(reference.instantaneous)
    )
    sustained_mismatches = len(
        set(internal.sustained) ^ set(reference.sustained)
    )
    matches = not (
        membership_mismatches
        or instant_mismatches
        or sustained_mismatches
    )

    try:
        import shapely
    except ImportError as error:
        raise RuntimeError("Shapely is required for reference execution") from error

    dataset_name, source_url = source_descriptor(path)
    transitions = sum(max(len(track.points) - 1, 0) for track in dataset.tracks)
    monitor_starts = len(internal.instantaneous) * len(DURATIONS_HOURS)
    internal_median = statistics.median(internal_times)
    reference_median = statistics.median(reference_times)
    return {
        "experiment": "ibtracs-multizone-duration-parity-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "claimBoundary": (
            "Exact discrete sample-and-hold parity for five experiment-defined "
            "Point/Polygon zones and 6/12/24-hour sustained events; not "
            "continuous trajectory, geodesic, or full GeoSPARQL conformance."
        ),
        "dataset": {
            "name": dataset_name,
            "doi": SOURCE_DOI,
            "sourceUrl": source_url,
            "path": path.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
            "tracks": len(dataset.tracks),
            "points": sum(len(track.points) for track in dataset.tracks),
            "transitions": transitions,
        },
        "semantics": {
            "clock": "timestamp-ordered discrete event time",
            "betweenSamples": "sample-and-hold",
            "deadlineOrdering": "due timers fire before a move at the same time",
            "regions": [
                {
                    "name": name,
                    "coordinates": [list(value) for value in coordinates],
                    "status": "experiment-defined; not an official boundary",
                }
                for name, coordinates in STUDY_ZONES
            ],
            "durationsHours": list(DURATIONS_HOURS),
        },
        "workload": {
            "transitionZonePairs": transitions * len(STUDY_ZONES),
            "instantaneousEvents": len(internal.instantaneous),
            "eventTransitionZonePairs": len(internal.instantaneous),
            "nonEventTransitionZonePairs": (
                transitions * len(STUDY_ZONES) - len(internal.instantaneous)
            ),
            "tracksWithInstantaneousEvents": len(
                {label.sid for label in internal.instantaneous}
            ),
            "sustainedMonitorStarts": monitor_starts,
            "sustainedEvents": len(internal.sustained),
            "unemittedByTrackEndOrInverseCrossing": (
                monitor_starts - len(internal.sustained)
            ),
            "sustainedCounts": _counts_by_duration(internal.sustained),
            "byRegion": _workload_breakdown(internal),
            "emissionLag": _lag_summary(internal.sustained),
        },
        "parity": {
            "matches": matches,
            "membershipMismatches": membership_mismatches,
            "instantaneousEventMismatches": instant_mismatches,
            "sustainedEventMismatches": sustained_mismatches,
            "membershipDifferenceSample": _difference_sample(
                internal.memberships,
                reference.memberships,
            ),
            "instantaneousDifferenceSample": _difference_sample(
                internal.instantaneous,
                reference.instantaneous,
            ),
            "sustainedDifferenceSample": _difference_sample(
                internal.sustained,
                reference.sustained,
            ),
        },
        "timing": {
            "repetitions": repetitions,
            "internalSeconds": internal_times,
            "referenceSeconds": reference_times,
            "internalMedianSeconds": internal_median,
            "referenceMedianSeconds": reference_median,
            "internalTransitionZonePairsPerSecond": (
                transitions * len(STUDY_ZONES) / internal_median
            ),
            "referenceTransitionZonePairsPerSecond": (
                transitions * len(STUDY_ZONES) / reference_median
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    dataset = result["dataset"]
    workload = result["workload"]
    parity = result["parity"]
    timing = result["timing"]
    assert isinstance(dataset, dict)
    assert isinstance(workload, dict)
    assert isinstance(parity, dict)
    assert isinstance(timing, dict)
    return "\n".join(
        (
            "# IBTrACS multizone duration result",
            "",
            "## Workload",
            "",
            f"- Tracks: {dataset['tracks']:,}",
            f"- Points: {dataset['points']:,}",
            f"- Transitions: {dataset['transitions']:,}",
            f"- Transition-zone pairs: {workload['transitionZonePairs']:,}",
            f"- Instantaneous events: {workload['instantaneousEvents']:,}",
            "- Event/non-event transition-zone pairs: "
            f"{workload['eventTransitionZonePairs']:,} / "
            f"{workload['nonEventTransitionZonePairs']:,}",
            "- Tracks with an instantaneous event: "
            f"{workload['tracksWithInstantaneousEvents']:,}",
            f"- Sustained monitor starts: {workload['sustainedMonitorStarts']:,}",
            f"- Sustained events: {workload['sustainedEvents']:,}",
            "- Unemitted by track end or inverse crossing: "
            f"{workload['unemittedByTrackEndOrInverseCrossing']:,}",
            f"- Sustained counts: `{workload['sustainedCounts']}`",
            f"- Emission lag: `{workload['emissionLag']}`",
            f"- Per-region breakdown: `{workload['byRegion']}`",
            "",
            "## Exact parity",
            "",
            f"- All layers match: **{parity['matches']}**",
            f"- Membership mismatches: {parity['membershipMismatches']:,}",
            "- Instantaneous-event mismatches: "
            f"{parity['instantaneousEventMismatches']:,}",
            f"- Sustained-event mismatches: {parity['sustainedEventMismatches']:,}",
            "",
            "## Timing",
            "",
            f"- PULSE median: {timing['internalMedianSeconds']:.6f} s",
            f"- GEOS/event-sweep median: {timing['referenceMedianSeconds']:.6f} s",
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
        prog="pulse-spatial-spatiotemporal",
        description="Run the IBTrACS multizone duration parity experiment.",
    )
    parser.add_argument(
        "--data",
        default=(
            "experiments/ibtracs/snapshots/"
            "ibtracs-last3years-main-2026-07-16.csv"
        ),
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--max-tracks", type=int)
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-parity", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_experiment(
            arguments.data,
            repetitions=arguments.repetitions,
            max_tracks=arguments.max_tracks,
        )
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    if arguments.require_parity and not result["parity"]["matches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
