"""Finite exhaustive mutation analysis for temporal execution contracts.

The experiment enumerates every Boolean membership trace of length two through
five over a declared time-increment grid, two initial states, and the presence
or absence of a same-trigger immediate transition.  PULSE is checked against an
independent workflow oracle on every generated trace.  Ten single-field
semantic mutants are then compared with that oracle over the same corpus.

This is exhaustive only for the declared finite input and mutation domains. It
does not claim language superiority, defect prevalence, or general correctness.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime, timedelta
from itertools import product
from pathlib import Path
from typing import Iterator

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
TRACE_LENGTHS = (2, 3, 4, 5)
INCREMENT_MINUTES = (1, 5, 10, 11)
INITIAL_STATES = ("Safe", "Maintenance")
IMMEDIATE_TARGETS: tuple[str | None, ...] = (None, "Maintenance")


@dataclass(frozen=True, slots=True)
class GeneratedTrace:
    identifier: str
    timestamps: tuple[datetime, ...]
    memberships: tuple[bool, ...]
    initial_state: str
    immediate_to_state: str | None


@dataclass(frozen=True, slots=True)
class MutationOperator:
    identifier: str
    description: str
    semantics: WorkflowSemantics


def _policy(initial_state: str) -> Policy:
    return Policy(
        "shipment_102",
        "ColdZone",
        EventKind.LEAVES,
        600.0,
        "Safe",
        "AtRisk",
        initial_state,
    )


def _generated_traces() -> Iterator[GeneratedTrace]:
    sequence = 0
    for length in TRACE_LENGTHS:
        for memberships in product((False, True), repeat=length):
            for increments in product(INCREMENT_MINUTES, repeat=length - 1):
                elapsed = 0
                offsets = [elapsed]
                for increment in increments:
                    elapsed += increment
                    offsets.append(elapsed)
                timestamps = tuple(
                    BASE_TIME + timedelta(minutes=offset) for offset in offsets
                )
                for initial_state in INITIAL_STATES:
                    for immediate_to_state in IMMEDIATE_TARGETS:
                        sequence += 1
                        yield GeneratedTrace(
                            f"T{sequence:05d}",
                            timestamps,
                            tuple(memberships),
                            initial_state,
                            immediate_to_state,
                        )


def _mutation_operators() -> tuple[MutationOperator, ...]:
    return (
        MutationOperator(
            "M-CANCEL",
            "retain a pending monitor after an inverse crossing",
            WorkflowSemantics(cancel_inverse_crossing=False),
        ),
        MutationOperator(
            "M-ORDER",
            "process the sampled move before timers due at the same time",
            WorkflowSemantics(timer_before_sample=False),
        ),
        MutationOperator(
            "M-START-GUARD",
            "start a monitor without checking its source-state guard",
            WorkflowSemantics(require_start_guard=False),
        ),
        MutationOperator(
            "M-DEADLINE-GUARD",
            "apply the delayed transition without rechecking its guard",
            WorkflowSemantics(require_deadline_guard=False),
        ),
        MutationOperator(
            "M-STRICT-DEADLINE",
            "fire only strictly after, rather than at, the deadline",
            WorkflowSemantics(inclusive_deadline=False),
        ),
        MutationOperator(
            "M-DURATION-SHORT",
            "halve every declared monitor duration",
            WorkflowSemantics(duration_scale=0.5),
        ),
        MutationOperator(
            "M-DURATION-LONG",
            "double every declared monitor duration",
            WorkflowSemantics(duration_scale=2.0),
        ),
        MutationOperator(
            "M-EMISSION-TIME",
            "record the deadline instead of the observation as emission time",
            WorkflowSemantics(deadline_as_emission_time=True),
        ),
        MutationOperator(
            "M-TRANSITION-ON-START",
            "apply a duration rule transition when its monitor starts",
            WorkflowSemantics(transition_on_start=True),
        ),
        MutationOperator(
            "M-POSTSTATE-START",
            "evaluate monitor eligibility after a same-event immediate rule",
            WorkflowSemantics(monitor_after_immediate_rule=True),
        ),
    )


def _changed_semantic_fields(semantics: WorkflowSemantics) -> list[str]:
    baseline = WorkflowSemantics()
    return [
        field.name
        for field in fields(WorkflowSemantics)
        if getattr(semantics, field.name) != getattr(baseline, field.name)
    ]


def _pulse_outcome(case: GeneratedTrace) -> Outcome:
    policy = _policy(case.initial_state)
    inside = Point(5, 5, CRS84)
    outside = Point(12, 5, CRS84)
    world = SpatialWorld(
        regions={
            policy.region: Polygon.from_xy(
                [(0, 0), (10, 0), (10, 10), (0, 10)], CRS84
            )
        },
        positions={policy.subject: inside if case.memberships[0] else outside},
        states={policy.subject: policy.initial_state},
    )
    rules: list[GeofenceRule] = []
    if case.immediate_to_state is not None:
        rules.append(
            GeofenceRule(
                "ImmediateDeparture",
                policy.trigger,
                policy.subject,
                policy.region,
                policy.from_state,
                case.immediate_to_state,
            )
        )
    rules.append(
        GeofenceRule(
            "SustainedDeparture",
            policy.trigger,
            policy.subject,
            policy.region,
            policy.from_state,
            policy.to_state,
            policy.duration_seconds,
        )
    )
    runtime = TemporalSpatialRuntime(world, case.timestamps[0], rules)
    instantaneous: list[InstantRecord] = []
    sustained: list[SustainedRecord] = []
    for timestamp, membership in zip(case.timestamps[1:], case.memberships[1:]):
        step = runtime.move_at(
            policy.subject,
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
        runtime.world.states[policy.subject],
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


def _input_record(case: GeneratedTrace) -> dict[str, object]:
    return {
        "traceId": case.identifier,
        "timestamps": [_iso(value) for value in case.timestamps],
        "memberships": list(case.memberships),
        "initialState": case.initial_state,
        "immediateToState": case.immediate_to_state,
        "durationSeconds": 600.0,
    }


def run_contract_faults(root: str | Path = DEFAULT_ROOT) -> dict[str, object]:
    # Keep the argument for CLI compatibility; the generated corpus is self-contained.
    del root
    operators = _mutation_operators()
    covered_fields: set[str] = set()
    for operator in operators:
        changed = _changed_semantic_fields(operator.semantics)
        if len(changed) != 1:
            raise AssertionError(
                f"{operator.identifier} must change exactly one semantic field: {changed}"
            )
        covered_fields.update(changed)
    semantic_fields = {field.name for field in fields(WorkflowSemantics)}
    if covered_fields != semantic_fields:
        raise AssertionError(
            "Mutation operators must cover every workflow semantic field: "
            f"covered={sorted(covered_fields)}, expected={sorted(semantic_fields)}"
        )

    trace_count = 0
    pulse_mismatches = 0
    killed_counts = {operator.identifier: 0 for operator in operators}
    witnesses: dict[str, dict[str, object] | None] = {
        operator.identifier: None for operator in operators
    }
    for case in _generated_traces():
        trace_count += 1
        policy = _policy(case.initial_state)
        reference = _reference_workflow(
            policy,
            case.timestamps,
            case.memberships,
            immediate_to_state=case.immediate_to_state,
        )
        pulse = _pulse_outcome(case)
        if pulse != reference:
            pulse_mismatches += 1
        for operator in operators:
            mutant = _reference_workflow(
                policy,
                case.timestamps,
                case.memberships,
                operator.semantics,
                case.immediate_to_state,
            )
            if mutant == reference:
                continue
            killed_counts[operator.identifier] += 1
            if witnesses[operator.identifier] is None:
                witnesses[operator.identifier] = {
                    "input": _input_record(case),
                    "reference": asdict(reference),
                    "mutant": asdict(mutant),
                    "changedOutcomeFields": _difference(reference, mutant),
                }

    expected_count = sum(
        (2**length)
        * (len(INCREMENT_MINUTES) ** (length - 1))
        * len(INITIAL_STATES)
        * len(IMMEDIATE_TARGETS)
        for length in TRACE_LENGTHS
    )
    if trace_count != expected_count:
        raise AssertionError(f"Generated {trace_count} traces, expected {expected_count}")

    operator_results = []
    baseline = WorkflowSemantics()
    for operator in operators:
        field_name = _changed_semantic_fields(operator.semantics)[0]
        operator_results.append(
            {
                "id": operator.identifier,
                "singleChange": operator.description,
                "changedSemanticField": field_name,
                "baselineValue": getattr(baseline, field_name),
                "mutantValue": getattr(operator.semantics, field_name),
                "tracesDistinguished": killed_counts[operator.identifier],
                "killed": killed_counts[operator.identifier] > 0,
                "firstWitness": witnesses[operator.identifier],
            }
        )

    return {
        "experiment": "generated-temporal-mutation-matrix-v3",
        "generatedAt": datetime.now(UTC).isoformat(),
        "design": {
            "traceLengths": list(TRACE_LENGTHS),
            "membershipDomain": [False, True],
            "timeIncrementMinutes": list(INCREMENT_MINUTES),
            "initialStates": list(INITIAL_STATES),
            "sameTriggerImmediateTargets": list(IMMEDIATE_TARGETS),
            "generation": "Cartesian product over every declared finite domain",
            "oracle": "independent executable workflow with the unmodified contract",
            "mutation": (
                "each operator changes exactly one checked semantic field; the set "
                "covers every field, with short and long variants for duration_scale"
            ),
        },
        "summary": {
            "generatedTraceCount": trace_count,
            "pulseMatchesReference": trace_count - pulse_mismatches,
            "pulseReferenceMismatches": pulse_mismatches,
            "mutationOperatorCount": len(operators),
            "mutantsKilled": sum(
                killed_counts[operator.identifier] > 0 for operator in operators
            ),
        },
        "operators": operator_results,
        "claimBoundary": (
            "Exhaustive mutation sensitivity only over the declared finite trace "
            "grid and ten single-field operators. It does not establish general "
            "correctness, real-world defect prevalence, usability, productivity, "
            "or expressive superiority over standards-based workflows."
        ),
    }


def render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    operators = result["operators"]
    assert isinstance(summary, dict)
    assert isinstance(operators, list)
    lines = [
        "# Generated temporal mutation matrix",
        "",
        f"- Generated traces: **{summary['generatedTraceCount']:,}**",
        "- PULSE/reference exact matches: "
        f"**{summary['pulseMatchesReference']:,}/{summary['generatedTraceCount']:,}**",
        "- Single-field mutation operators killed: "
        f"**{summary['mutantsKilled']}/{summary['mutationOperatorCount']}**",
        "",
        "| Mutant | Single semantic field | Distinguished traces | Killed | First witness |",
        "|---|---|---:|---:|---|",
    ]
    for operator in operators:
        witness = operator["firstWitness"]
        assert isinstance(witness, dict)
        witness_input = witness["input"]
        assert isinstance(witness_input, dict)
        lines.append(
            f"| {operator['id']} | {operator['changedSemanticField']} | "
            f"{operator['tracesDistinguished']:,} | {operator['killed']} | "
            f"{witness_input['traceId']} |"
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
        description="Run the finite exhaustive temporal mutation matrix.",
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
        summary["pulseReferenceMismatches"] == 0
        and summary["mutantsKilled"] == summary["mutationOperatorCount"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
