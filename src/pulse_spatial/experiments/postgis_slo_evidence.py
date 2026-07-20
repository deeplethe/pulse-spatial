"""Consolidate preregistered PostGIS SLO phases without cherry-picking."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .ibtracs import _sha256
from .postgis_concurrency import _write


def _load(path: str | Path) -> dict[str, object]:
    target = Path(path)
    value = json.loads(target.read_text(encoding="utf-8"))
    if value.get("experiment") != "postgis-open-loop-slo-saturation-v1":
        raise ValueError(f"Not a PostGIS SLO result: {target}")
    return value


def consolidate(
    repeated_paths: Iterable[str | Path],
    sustained_path: str | Path,
    exploratory_path: str | Path,
) -> dict[str, object]:
    repeated_files = tuple(Path(path) for path in repeated_paths)
    if not repeated_files:
        raise ValueError("At least one repeated result is required")
    repeated_results = tuple(_load(path) for path in repeated_files)
    sustained = _load(sustained_path)
    exploratory = _load(exploratory_path)
    reference = repeated_results[0]
    reference_protocol = reference["protocol"]
    assert isinstance(reference_protocol, dict)
    for result in repeated_results:
        protocol = result["protocol"]
        assert isinstance(protocol, dict)
        comparable = (
            protocol["clients"],
            protocol["warmupSecondsPerRate"],
            protocol["measurementSecondsPerRate"],
            protocol["repetitions"],
            protocol["latencyLimitMs"],
            protocol["maximumSkipRate"],
            protocol["deviceCount"],
            protocol["scriptWeights"],
        )
        expected = (
            reference_protocol["clients"],
            reference_protocol["warmupSecondsPerRate"],
            reference_protocol["measurementSecondsPerRate"],
            reference_protocol["repetitions"],
            reference_protocol["latencyLimitMs"],
            reference_protocol["maximumSkipRate"],
            reference_protocol["deviceCount"],
            reference_protocol["scriptWeights"],
        )
        if comparable != expected:
            raise ValueError("Repeated phases do not share one protocol")

    summaries: dict[int, dict[str, object]] = {}
    repeated_transactions = 0
    for result in repeated_results:
        for summary in result["summaryByRate"]:
            target = int(summary["targetTps"])
            if target in summaries:
                raise ValueError(f"Duplicate repeated target rate: {target}")
            summaries[target] = summary
        repeated_transactions += sum(
            int(level["transactions"]) for level in result["levels"]
        )
    ordered = [summaries[target] for target in sorted(summaries)]
    lower_bound = None
    first_failure = None
    for summary in ordered:
        if summary["allSloPass"] and first_failure is None:
            lower_bound = int(summary["targetTps"])
        elif not summary["allSloPass"] and first_failure is None:
            first_failure = int(summary["targetTps"])
    isolated_passes = [
        int(summary["targetTps"])
        for summary in ordered
        if summary["allSloPass"]
        and first_failure is not None
        and int(summary["targetTps"]) > first_failure
    ]

    source_paths = (*repeated_files, Path(sustained_path), Path(exploratory_path))
    sources = [
        {
            "path": path.as_posix(),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in source_paths
    ]
    sustained_summaries = sustained["summaryByRate"]
    exploratory_summaries = exploratory["summaryByRate"]
    return {
        "experiment": "postgis-open-loop-slo-evidence-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "decisionRule": (
            "The conservative repeated-window lower bound is the highest target "
            "in the contiguous ascending prefix for which every 60-second repeat "
            "passes. A higher isolated pass after the first failed target is "
            "reported but cannot raise the lower bound."
        ),
        "protocol": reference_protocol,
        "repeatedWindowSummary": ordered,
        "repeatedWindowTransactions": repeated_transactions,
        "capacity": {
            "conservativeRepeatedWindowLowerBoundTps": lower_bound,
            "firstFailedTargetTps": first_failure,
            "isolatedPassingTargetsAfterFailureTps": isolated_passes,
        },
        "sustainedFiveMinuteSummary": sustained_summaries,
        "sustainedTransactions": sum(
            int(level["transactions"]) for level in sustained["levels"]
        ),
        "exploratorySummary": exploratory_summaries,
        "maximumObservedCompletionTps": max(
            float(summary["reportedTpsMean"]) for summary in exploratory_summaries
        ),
        "environment": reference["environment"],
        "dataset": reference["dataset"],
        "sources": sources,
    }


def render_markdown(result: dict[str, object]) -> str:
    capacity = result["capacity"]
    protocol = result["protocol"]
    repeated = result["repeatedWindowSummary"]
    sustained = result["sustainedFiveMinuteSummary"]
    assert isinstance(capacity, dict)
    assert isinstance(protocol, dict)
    assert isinstance(repeated, list)
    assert isinstance(sustained, list)
    rows = [
        "# PostGIS open-loop production evidence",
        "",
        f"- Conservative repeated-window lower bound: **{capacity['conservativeRepeatedWindowLowerBoundTps']:,} TPS**",
        f"- First failed target: **{capacity['firstFailedTargetTps']:,} TPS**",
        f"- Completed transactions in repeated windows: **{result['repeatedWindowTransactions']:,}**",
        f"- Maximum exploratory completion rate: **{result['maximumObservedCompletionTps']:,.2f} TPS**",
        "",
        "Passing requires zero database transaction failures, completion p99 at or below "
        f"{protocol['latencyLimitMs']} ms, and skipped arrivals at or below "
        f"{100 * protocol['maximumSkipRate']:.3f}% in every repeat.",
        "",
        "| Target TPS | mean completed TPS | max p99 ms | max skip rate | DB failures | all 3 pass |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    rows.extend(
        "| {targetTps} | {reportedTpsMean:.2f} | {p99MaxMs:.3f} | "
        "{skipRateMax:.4%} | {transactionFailures} | {allSloPass} |".format(**item)
        for item in repeated
    )
    rows.extend(
        (
            "",
            "## Five-minute sustained checks",
            "",
            "| Target TPS | completed TPS | p99 ms | skip rate | DB failures | pass |",
            "|---:|---:|---:|---:|---:|---:|",
        )
    )
    rows.extend(
        "| {targetTps} | {reportedTpsMean:.2f} | {p99MaxMs:.3f} | "
        "{skipRateMax:.4%} | {transactionFailures} | {allSloPass} |".format(**item)
        for item in sustained
    )
    rows.extend(("", "## Decision rule", "", str(result["decisionRule"]), ""))
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(prog="pulse-spatial-postgis-slo-evidence")
    parser.add_argument("--repeated", nargs="+", required=True)
    parser.add_argument("--sustained", required=True)
    parser.add_argument("--exploratory", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-markdown", required=True)
    arguments = parser.parse_args()
    result = consolidate(
        arguments.repeated,
        arguments.sustained,
        arguments.exploratory,
    )
    _write(arguments.output_json, json.dumps(result, indent=2) + "\n")
    _write(arguments.output_markdown, render_markdown(result))
    print(json.dumps(result["capacity"], indent=2))


if __name__ == "__main__":
    main()
