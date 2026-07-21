"""Mutation sensitivity for four temporal execution obligations.

Each case has a manually specified exact outcome. The unmodified PULSE runtime
and an independently implemented reference workflow must both match that
oracle. The reference workflow is then rerun with one auditable semantic switch
changed. This experiment measures sensitivity and fault localization; it does
not claim language superiority or standards incapability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..geometry import CRS84, Point, Polygon
from ..model import SpatialWorld
from ..runtime import EventKind, GeofenceRule, TemporalSpatialRuntime
from .composition import (
    DEFAULT_ROOT,
    InstantRecord,
    Outcome,
    Policy,
    SustainedRecord,
    WorkflowSemantics,
    _iso,
    _reference_workflow,
)


BASE_TIME = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class WorkflowCase:
    identifier: str
    obligation: str
    policy: Policy
    timestamps: tuple[datetime, ...]
    memberships: tuple[bool, ...]
    expected: Outcome
    mutant_identifier: str
    mutant_description: str
    mutant_semantics: WorkflowSemantics


def _instant(kind: str, at_minutes: int) -> InstantRecord:
    return InstantRecord(
        kind,
        "shipment_102",
        "ColdZone",
        _iso(BASE_TIME + timedelta(minutes=at_minutes)),
    )


def _sustained(
    *,
    duration_seconds: float,
    started_minutes: int,
    effective_minutes: int,
    emitted_minutes: int,
) -> SustainedRecord:
    return SustainedRecord(
        "leaves",
        "shipment_102",
        "ColdZone",
        duration_seconds,
        _iso(BASE_TIME + timedelta(minutes=started_minutes)),
        _iso(BASE_TIME + timedelta(minutes=effective_minutes)),
        _iso(BASE_TIME + timedelta(minutes=emitted_minutes)),
    )


def _policy(initial_state: str = "Safe") -> Policy:
    return Policy(
        "shipment_102",
        "ColdZone",
        EventKind.LEAVES,
        600.0,
        "Safe",
        "AtRisk",
        initial_state,
    )


def _cases() -> tuple[WorkflowCase, ...]:
    return (
        WorkflowCase(
            "inverseCancellation",
            "An inverse crossing cancels a pending duration monitor",
            _policy(),
            tuple(BASE_TIME + timedelta(minutes=value) for value in (0, 1, 9, 12)),
            (True, False, True, True),
            Outcome("Safe", (_instant("leaves", 1), _instant("enters", 9)), ()),
            "M-CANCEL",
            "retain a pending monitor after the inverse crossing",
            WorkflowSemantics(cancel_inverse_crossing=False),
        ),
        WorkflowCase(
            "timerBeforeMoveAtTie",
            "A timer due at t fires before the sampled move at t",
            _policy(),
            tuple(BASE_TIME + timedelta(minutes=value) for value in (0, 1, 11)),
            (True, False, True),
            Outcome(
                "AtRisk",
                (_instant("leaves", 1), _instant("enters", 11)),
                (
                    _sustained(
                        duration_seconds=600.0,
                        started_minutes=1,
                        effective_minutes=11,
                        emitted_minutes=11,
                    ),
                ),
            ),
            "M-ORDER",
            "process the sampled move before timers due at the same time",
            WorkflowSemantics(timer_before_sample=False),
        ),
        WorkflowCase(
            "startGuard",
            "A duration monitor starts only when its source-state guard holds",
            _policy("Maintenance"),
            tuple(BASE_TIME + timedelta(minutes=value) for value in (0, 1, 12)),
            (True, False, False),
            Outcome("Maintenance", (_instant("leaves", 1),), ()),
            "M-START-GUARD",
            "start the monitor without checking the source-state guard",
            WorkflowSemantics(require_start_guard=False),
        ),
        WorkflowCase(
            "durationExactness",
            "A declared ten-minute duration is neither shortened nor rounded",
            _policy(),
            tuple(BASE_TIME + timedelta(minutes=value) for value in (0, 1, 2)),
            (True, False, False),
            Outcome("Safe", (_instant("leaves", 1),), ()),
            "M-DURATION",
            "scale the declared duration by 0.1",
            WorkflowSemantics(duration_scale=0.1),
        ),
    )


def _pulse_outcome(case: WorkflowCase) -> Outcome:
    inside = Point(5, 5, CRS84)
    outside = Point(12, 5, CRS84)
    world = SpatialWorld(
        regions={
            case.policy.region: Polygon.from_xy(
                [(0, 0), (10, 0), (10, 10), (0, 10)], CRS84
            )
        },
        positions={
            case.policy.subject: inside if case.memberships[0] else outside
        },
        states={case.policy.subject: case.policy.initial_state},
    )
    rule = GeofenceRule(
        "SustainedDeparture",
        case.policy.trigger,
        case.policy.subject,
        case.policy.region,
        case.policy.from_state,
        case.policy.to_state,
        case.policy.duration_seconds,
    )
    runtime = TemporalSpatialRuntime(world, case.timestamps[0], (rule,))
    instantaneous: list[InstantRecord] = []
    sustained: list[SustainedRecord] = []
    for timestamp, membership in zip(case.timestamps[1:], case.memberships[1:]):
        step = runtime.move_at(
            case.policy.subject,
            inside if membership else outside,
            timestamp,
        )
        instantaneous.extend(
            InstantRecord(
                event.kind.value,
                event.subject,
                event.region,
                _iso(timestamp),
            )
            for event in step.instantaneous
        )
        sustained.extend(
            SustainedRecord(
                event.kind.value,
                event.subject,
                event.region,
                event.duration_seconds,
                _iso(event.started_at),
                _iso(event.effective_at),
                _iso(event.emitted_at),
            )
            for event in step.sustained
        )
    return Outcome(
        runtime.world.states[case.policy.subject],
        tuple(instantaneous),
        tuple(sustained),
    )


def _difference(expected: Outcome, actual: Outcome) -> list[str]:
    changed: list[str] = []
    if actual.final_state != expected.final_state:
        changed.append("finalState")
    if actual.instantaneous != expected.instantaneous:
        changed.append("instantaneousTrace")
    if actual.sustained != expected.sustained:
        changed.append("sustainedTrace")
    return changed


def run_contract_faults(root: str | Path = DEFAULT_ROOT) -> dict[str, object]:
    # Keep the argument for CLI compatibility; the v2 corpus is self-contained.
    del root
    rendered_cases: list[dict[str, object]] = []
    for case in _cases():
        pulse = _pulse_outcome(case)
        reference = _reference_workflow(
            case.policy, case.timestamps, case.memberships
        )
        mutant = _reference_workflow(
            case.policy,
            case.timestamps,
            case.memberships,
            case.mutant_semantics,
        )
        rendered_cases.append(
            {
                "id": case.identifier,
                "obligation": case.obligation,
                "input": {
                    "timestamps": [_iso(value) for value in case.timestamps],
                    "memberships": list(case.memberships),
                    "initialState": case.policy.initial_state,
                    "durationSeconds": case.policy.duration_seconds,
                },
                "oracle": asdict(case.expected),
                "pulse": {
                    "outcome": asdict(pulse),
                    "matchesOracle": pulse == case.expected,
                },
                "referenceWorkflow": {
                    "outcome": asdict(reference),
                    "matchesOracle": reference == case.expected,
                },
                "mutant": {
                    "id": case.mutant_identifier,
                    "singleChange": case.mutant_description,
                    "outcome": asdict(mutant),
                    "killedBySameOracle": mutant != case.expected,
                    "changedFields": _difference(case.expected, mutant),
                },
            }
        )
    return {
        "experiment": "temporal-contract-mutation-sensitivity-v2",
        "generatedAt": datetime.now(UTC).isoformat(),
        "design": {
            "cases": "four pre-specified traces with manually encoded exact outcomes",
            "control": "unmodified PULSE and reference workflow run every case",
            "mutation": "one semantic switch changes per reference-workflow run",
            "oracle": "the same exact final-state and event-trace oracle for all paths",
        },
        "cases": rendered_cases,
        "summary": {
            "caseCount": len(rendered_cases),
            "pulseMatchesOracle": sum(
                bool(case["pulse"]["matchesOracle"]) for case in rendered_cases
            ),
            "referenceMatchesOracle": sum(
                bool(case["referenceWorkflow"]["matchesOracle"])
                for case in rendered_cases
            ),
            "singleChangeMutantsKilled": sum(
                bool(case["mutant"]["killedBySameOracle"])
                for case in rendered_cases
            ),
        },
        "claimBoundary": (
            "A mutation-sensitivity experiment over four selected temporal "
            "obligations. It establishes observable consequences and locates "
            "the corresponding PULSE runtime contracts. It does not compare "
            "usability, productivity, defect prevalence, or the expressive "
            "power of PULSE and standards-based workflows."
        ),
    }


def render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    cases = result["cases"]
    assert isinstance(summary, dict)
    assert isinstance(cases, list)
    lines = [
        "# Temporal contract mutation sensitivity",
        "",
        f"- PULSE matches exact oracle: **{summary['pulseMatchesOracle']}/{summary['caseCount']}**",
        "- Reference workflow matches exact oracle: "
        f"**{summary['referenceMatchesOracle']}/{summary['caseCount']}**",
        "- Single-change mutants killed by the same oracle: "
        f"**{summary['singleChangeMutantsKilled']}/{summary['caseCount']}**",
        "",
        "| Obligation | Mutant | PULSE | Reference | Mutant killed | Changed fields |",
        "|---|---|---:|---:|---:|---|",
    ]
    for case in cases:
        pulse = case["pulse"]
        reference = case["referenceWorkflow"]
        mutant = case["mutant"]
        lines.append(
            f"| {case['id']} | {mutant['id']} | "
            f"{pulse['matchesOracle']} | {reference['matchesOracle']} | "
            f"{mutant['killedBySameOracle']} | "
            f"{', '.join(mutant['changedFields'])} |"
        )
    lines.extend(("", "## Claim boundary", "", str(result["claimBoundary"]), ""))
    return "\n".join(lines)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-contract-faults",
        description="Run four temporal contract mutation-sensitivity cases.",
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-complete", action="store_true")
    arguments = parser.parse_args()
    result = run_contract_faults(arguments.root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    summary = result["summary"]
    assert isinstance(summary, dict)
    if arguments.require_complete and not (
        summary["pulseMatchesOracle"] == summary["caseCount"]
        and summary["referenceMatchesOracle"] == summary["caseCount"]
        and summary["singleChangeMutantsKilled"] == summary["caseCount"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
