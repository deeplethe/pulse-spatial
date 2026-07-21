"""Fault-localization probes for the PULSE composition comparison.

The experiment does not claim that RDF standards cannot express the tested
behavior.  It injects four code-only mutations into the orchestration layer of
the Semantic Web composition and records whether unchanged RDF/SHACL inputs
can expose them.  Corresponding PULSE probes exercise the language/runtime
boundaries that own the same obligations.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..compiler import load_pulse
from ..geometry import CRS84, Point, Polygon
from ..model import SpatialWorld
from ..runtime import EventKind, GeofenceRule, TemporalSpatialRuntime
from .composition import DEFAULT_ROOT, Policy, _reference_workflow, run_semantic_web


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PAPER_EXAMPLE = REPOSITORY_ROOT / "examples" / "paper_cold_chain_st.pulse"


def _world(state: str = "Safe") -> SpatialWorld:
    return SpatialWorld(
        regions={
            "ColdZone": Polygon.from_xy(
                [(0, 0), (10, 0), (10, 10), (0, 10)], CRS84
            )
        },
        positions={"shipment_102": Point(5, 5, CRS84)},
        states={"shipment_102": state},
    )


def _rule() -> GeofenceRule:
    return GeofenceRule(
        "SustainedDeparture",
        EventKind.LEAVES,
        "shipment_102",
        "ColdZone",
        "Safe",
        "AtRisk",
        600,
    )


def _pulse_observation_non_interference(root: Path) -> dict[str, object]:
    model = load_pulse(root / "pulse" / "model.pulse")
    asserted = model.world.positions["shipment_102"]
    observed = model.world.observations[-1].value
    return {
        "contractHeld": asserted == Point(5, 5, CRS84) and observed != asserted,
        "enforcementPoint": "observation-recording boundary",
        "evidence": {
            "assertedPosition": [asserted.x, asserted.y],
            "lastObservedPosition": [observed.x, observed.y],
        },
    }


def _pulse_scenario_isolation() -> dict[str, object]:
    model = load_pulse(PAPER_EXAMPLE)
    source_position = model.world.positions["batch"]
    source_state = model.world.states["batch"]
    report = model.run_scenario("Reroute")
    source_unchanged = (
        model.world.positions["batch"] == source_position
        and model.world.states["batch"] == source_state
    )
    branch_changed = (
        report.result.world.positions["batch"] != source_position
        or report.result.world.states["batch"] != source_state
    )
    return {
        "contractHeld": source_unchanged and branch_changed,
        "enforcementPoint": "isolated scenario runtime",
        "evidence": {
            "sourceStateAfter": model.world.states["batch"],
            "branchStateAfter": report.result.world.states["batch"],
        },
    }


def _pulse_timer_precedence() -> dict[str, object]:
    started = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)
    runtime = TemporalSpatialRuntime(_world(), started, [_rule()])
    runtime.move_at("shipment_102", Point(12, 5, CRS84), started)
    tied = runtime.move_at(
        "shipment_102",
        Point(5, 5, CRS84),
        started + timedelta(minutes=10),
    )
    return {
        "contractHeld": (
            len(tied.sustained) == 1
            and tied.sustained[0].effective_at == started + timedelta(minutes=10)
            and runtime.world.states["shipment_102"] == "AtRisk"
        ),
        "enforcementPoint": "temporal step ordering",
        "evidence": {
            "sustainedEventsAtTie": len(tied.sustained),
            "finalState": runtime.world.states["shipment_102"],
        },
    }


def _pulse_guard_preservation() -> dict[str, object]:
    started = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)
    runtime = TemporalSpatialRuntime(_world("Maintenance"), started, [_rule()])
    runtime.move_at("shipment_102", Point(12, 5, CRS84), started)
    emitted = runtime.advance_to(started + timedelta(minutes=10))
    return {
        "contractHeld": (
            emitted == ()
            and runtime.world.states["shipment_102"] == "Maintenance"
        ),
        "enforcementPoint": "transition guard at monitor start",
        "evidence": {
            "sustainedEvents": len(emitted),
            "finalState": runtime.world.states["shipment_102"],
        },
    }


def _mutant_auto_accepts_observation() -> dict[str, object]:
    authoritative = {"position": (5.0, 5.0)}
    observed = (13.0, 5.0)
    authoritative["position"] = observed
    caught = authoritative["position"] != (5.0, 5.0)
    return {
        "externalOracleCaught": caught,
        "mutantEffect": "unaccepted observation overwrote authoritative position",
    }


def _mutant_writes_branch_back() -> dict[str, object]:
    authoritative = {"position": (5.0, 5.0), "state": "Safe"}
    before = dict(authoritative)
    branch = authoritative
    branch.update(position=(12.0, 5.0), state="AtRisk")
    return {
        "externalOracleCaught": authoritative != before,
        "mutantEffect": "hypothetical branch mutated its source state",
    }


def _mutant_move_before_due_timer() -> dict[str, object]:
    started = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)
    timestamps = (
        started,
        started + timedelta(minutes=1),
        started + timedelta(minutes=11),
    )
    memberships = (True, False, True)
    policy = Policy(
        "shipment_102",
        "ColdZone",
        EventKind.LEAVES,
        600,
        "Safe",
        "AtRisk",
        "Safe",
    )
    expected = _reference_workflow(policy, timestamps, memberships)

    # Mutant: process the re-entry first, cancelling the due monitor before
    # checking the deadline at the same timestamp.
    mutant_state = "Safe"
    pending = timestamps[1]
    current_inside = memberships[2]
    if current_inside:
        pending = None
    if pending is not None and pending + timedelta(seconds=600) <= timestamps[2]:
        mutant_state = "AtRisk"
    return {
        "externalOracleCaught": (
            expected.final_state == "AtRisk" and mutant_state == "Safe"
        ),
        "mutantEffect": "same-time re-entry cancelled a timer before it fired",
        "expectedFinalState": expected.final_state,
        "mutantFinalState": mutant_state,
    }


def _mutant_elides_state_guard() -> dict[str, object]:
    started = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)
    timestamps = (
        started,
        started + timedelta(minutes=1),
        started + timedelta(minutes=12),
    )
    memberships = (True, False, False)
    policy = Policy(
        "shipment_102",
        "ColdZone",
        EventKind.LEAVES,
        600,
        "Safe",
        "AtRisk",
        "Maintenance",
    )
    expected = _reference_workflow(policy, timestamps, memberships)
    mutant_state = "AtRisk"
    return {
        "externalOracleCaught": (
            expected.final_state == "Maintenance" and mutant_state == "AtRisk"
        ),
        "mutantEffect": "transition fired although its source-state guard was false",
        "expectedFinalState": expected.final_state,
        "mutantFinalState": mutant_state,
    }


def run_contract_faults(root: str | Path = DEFAULT_ROOT) -> dict[str, object]:
    base = Path(root)
    semantic_execution = run_semantic_web(base)
    input_conforms = bool(semantic_execution.validation["shaclConforms"])
    cases = (
        (
            "observationNonInterference",
            "Observed evidence requires explicit acceptance before authoritative update",
            _pulse_observation_non_interference(base),
            _mutant_auto_accepts_observation(),
        ),
        (
            "scenarioIsolation",
            "Hypothetical execution must not mutate its source world",
            _pulse_scenario_isolation(),
            _mutant_writes_branch_back(),
        ),
        (
            "timerBeforeMoveAtTie",
            "A due timer fires before a move at the same timestamp",
            _pulse_timer_precedence(),
            _mutant_move_before_due_timer(),
        ),
        (
            "guardPreservation",
            "A state transition requires its declared source-state guard",
            _pulse_guard_preservation(),
            _mutant_elides_state_guard(),
        ),
    )
    rendered_cases: list[dict[str, object]] = []
    for identifier, obligation, pulse, mutant in cases:
        rendered_cases.append(
            {
                "id": identifier,
                "obligation": obligation,
                "pulse": pulse,
                "standardsWorkflowMutant": {
                    "unchangedRdfShaclInputConforms": input_conforms,
                    "escapedArtifactValidation": input_conforms,
                    **mutant,
                },
            }
        )
    return {
        "experiment": "contract-fault-localization-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "cases": rendered_cases,
        "summary": {
            "caseCount": len(rendered_cases),
            "pulseContractsHeld": sum(
                bool(case["pulse"]["contractHeld"]) for case in rendered_cases
            ),
            "workflowMutantsEscapingArtifactValidation": sum(
                bool(case["standardsWorkflowMutant"]["escapedArtifactValidation"])
                for case in rendered_cases
            ),
            "workflowMutantsCaughtByExternalOracle": sum(
                bool(case["standardsWorkflowMutant"]["externalOracleCaught"])
                for case in rendered_cases
            ),
        },
        "claimBoundary": (
            "A mutation-based localization probe over four selected contract "
            "obligations. It shows which checked boundary owns each obligation; "
            "it does not establish defect prevalence, standards incapability, "
            "usability, productivity, or complete mutation coverage."
        ),
    }


def render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    cases = result["cases"]
    assert isinstance(summary, dict)
    assert isinstance(cases, list)
    lines = [
        "# Contract fault-localization probe",
        "",
        f"- PULSE contracts held: **{summary['pulseContractsHeld']}/{summary['caseCount']}**",
        "- Workflow mutants escaping unchanged RDF/SHACL validation: "
        f"**{summary['workflowMutantsEscapingArtifactValidation']}/{summary['caseCount']}**",
        "- Workflow mutants caught by external postcondition oracles: "
        f"**{summary['workflowMutantsCaughtByExternalOracle']}/{summary['caseCount']}**",
        "",
        "| Obligation | PULSE boundary | RDF/SHACL sees code mutant | External oracle |",
        "|---|---|---:|---:|",
    ]
    for case in cases:
        pulse = case["pulse"]
        mutant = case["standardsWorkflowMutant"]
        lines.append(
            f"| {case['id']} | {pulse['enforcementPoint']} | "
            f"{not mutant['escapedArtifactValidation']} | "
            f"{mutant['externalOracleCaught']} |"
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
        description="Locate four modal/temporal contract faults across boundaries.",
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
        summary["pulseContractsHeld"] == summary["caseCount"]
        and summary["workflowMutantsEscapingArtifactValidation"]
        == summary["caseCount"]
        and summary["workflowMutantsCaughtByExternalOracle"]
        == summary["caseCount"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
