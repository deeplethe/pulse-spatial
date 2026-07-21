"""Matched RDF/SHACL plus executable-statechart comparison.

The baseline validates the checked-in SOSA/GeoSPARQL/OWL-Time graph with SHACL,
then executes the temporal policy with the third-party Sismic 1.6.11 statechart
interpreter.  Four fault injections locate identifier, effect, clock-order, and
scenario-isolation obligations across PULSE, an unprofiled composition, and the
same composition with explicit binding/adapter contracts.

The experiment compares where selected faults are prevented or detected.  It
does not measure usability, productivity, or general language superiority.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..compiler import PulseModelError, compile_pulse, load_pulse
from ..runtime import EventKind
from ..validation import geosparql_reference_functions
from .composition import (
    DEFAULT_ROOT,
    InstantRecord,
    Outcome,
    Policy,
    SustainedRecord,
    _iso,
    _local_name,
    _parse_time,
    run_pulse,
)


DEFAULT_EXPERIMENT_ROOT = Path("experiments/statechart-comparison")


class BindingContractError(ValueError):
    """Raised when independently authored artifact bindings disagree."""


class AdapterContractError(ValueError):
    """Raised when an adapter violates the declared timestamp/isolation policy."""


@dataclass(frozen=True, slots=True)
class StandardsTrace:
    policy: Policy
    timestamps: tuple[datetime, ...]
    memberships: tuple[bool, ...]
    shacl_conforms: bool
    rdf_triples: int
    shape_triples: int


@dataclass(frozen=True, slots=True)
class StatechartBinding:
    subject: str
    region: str
    trigger: str
    from_state: str
    to_state: str
    duration_seconds: float
    state_domain: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Detection:
    stage: str
    detected: bool
    detail: str


def _require_statechart_runtime() -> tuple[object, object, object, type[Exception]]:
    try:
        from sismic.clock import SimulatedClock
        from sismic.exceptions import ContractError
        from sismic.interpreter import Interpreter
        from sismic.io import import_from_yaml
    except ImportError as error:
        raise RuntimeError(
            "Statechart comparison requires the 'statechart' optional dependency"
        ) from error
    return import_from_yaml, Interpreter, SimulatedClock, ContractError


def _load_binding(path: Path) -> StatechartBinding:
    value = json.loads(path.read_text(encoding="utf-8"))
    return StatechartBinding(
        str(value["subject"]),
        str(value["region"]),
        str(value["trigger"]),
        str(value["fromState"]),
        str(value["toState"]),
        float(value["durationSeconds"]),
        tuple(str(item) for item in value["stateDomain"]),
    )


def _load_standards_trace(root: Path) -> StandardsTrace:
    try:
        from pyshacl import validate
        from rdflib import Graph, Namespace
        from rdflib.namespace import RDF
    except ImportError as error:
        raise RuntimeError(
            "Statechart comparison requires the validation dependencies"
        ) from error

    directory = root / "semantic-web"
    graph = Graph().parse(directory / "data.ttl")
    graph.parse(directory / "policy.ttl")
    shapes = Graph().parse(directory / "shapes.ttl")
    conforms, _, report = validate(graph, shacl_graph=shapes, advanced=True)
    if not conforms:
        raise ValueError(f"Semantic Web input fails SHACL:\n{report}")

    ex = Namespace("https://example.org/cold-chain/")
    time_ns = Namespace("http://www.w3.org/2006/time#")
    policy_node = next(graph.subjects(RDF.type, ex.GeofencePolicy))
    subject = graph.value(policy_node, ex.subject)
    region = graph.value(policy_node, ex.region)
    trigger = graph.value(policy_node, ex.trigger)
    from_state = graph.value(policy_node, ex.fromState)
    to_state = graph.value(policy_node, ex.toState)
    duration = graph.value(policy_node, time_ns.hasDuration)
    duration_value = graph.value(duration, time_ns.numericDuration)
    duration_unit = graph.value(duration, time_ns.unitType)
    initial_state = graph.value(subject, ex.initialState)
    required = (
        subject,
        region,
        trigger,
        from_state,
        to_state,
        duration,
        duration_value,
        duration_unit,
        initial_state,
    )
    if any(value is None for value in required):
        raise ValueError("Semantic Web statechart policy is incomplete")
    units = {"unitMinute": 60.0}
    unit_name = _local_name(duration_unit)
    if unit_name not in units:
        raise ValueError(f"Unsupported duration unit: {unit_name}")
    policy = Policy(
        _local_name(subject),
        _local_name(region),
        EventKind(_local_name(trigger)),
        float(duration_value) * units[unit_name],
        _local_name(from_state),
        _local_name(to_state),
        _local_name(initial_state),
    )
    query = """
PREFIX ex: <https://example.org/cold-chain/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
SELECT ?time ?inside WHERE {
  ex:SustainedDeparturePolicy ex:subject ?subject ; ex:region ?region .
  ?region geo:hasGeometry/geo:asWKT ?regionWkt .
  ?observation a sosa:Observation ;
    sosa:hasFeatureOfInterest ?subject ;
    sosa:resultTime ?time ;
    sosa:hasResult/geo:asWKT ?pointWkt .
  BIND(geof:sfIntersects(?pointWkt, ?regionWkt) AS ?inside)
}
ORDER BY ?time
"""
    with geosparql_reference_functions():
        rows = tuple(graph.query(query))
    return StandardsTrace(
        policy,
        tuple(_parse_time(str(row.time)) for row in rows),
        tuple(bool(row.inside.toPython()) for row in rows),
        True,
        len(graph),
        len(shapes),
    )


def _validate_binding(policy: Policy, binding: StatechartBinding) -> None:
    expected: dict[str, object] = {
        "subject": policy.subject,
        "region": policy.region,
        "trigger": policy.trigger.value,
        "fromState": policy.from_state,
        "toState": policy.to_state,
        "durationSeconds": policy.duration_seconds,
    }
    actual: dict[str, object] = {
        "subject": binding.subject,
        "region": binding.region,
        "trigger": binding.trigger,
        "fromState": binding.from_state,
        "toState": binding.to_state,
        "durationSeconds": binding.duration_seconds,
    }
    differences = [name for name in expected if expected[name] != actual[name]]
    if (
        policy.from_state not in binding.state_domain
        or policy.to_state not in binding.state_domain
    ):
        differences.append("stateDomain")
    if differences:
        raise BindingContractError(
            "RDF/statechart binding mismatch: " + ", ".join(differences)
        )


def _crossing_name(kind: EventKind, subject: str, region: str) -> str:
    return f"{kind.value}__{subject}__{region}"


def _statechart_outcome(
    trace: StandardsTrace,
    statechart_text: str,
    *,
    check_contracts: bool,
    sample_before_clock: bool = False,
    enforce_adapter_contract: bool = False,
) -> Outcome:
    import_from_yaml, Interpreter, SimulatedClock, _ = _require_statechart_runtime()
    chart = import_from_yaml(text=statechart_text)
    clock = SimulatedClock()
    interpreter = Interpreter(
        chart,
        clock=clock,
        initial_context={
            "domain_state": trace.policy.initial_state,
            "allowed_states": ("Safe", "AtRisk", "Maintenance"),
        },
        ignore_contract=not check_contracts,
    )
    interpreter.execute()
    first = trace.timestamps[0]
    previous = trace.memberships[0]
    instantaneous: list[InstantRecord] = []

    for timestamp, current in zip(trace.timestamps[1:], trace.memberships[1:]):
        offset = (timestamp - first).total_seconds()
        if current == previous:
            clock.time = offset
            interpreter.execute()
            continue
        kind = EventKind.ENTERS if current else EventKind.LEAVES
        event_name = _crossing_name(
            kind,
            trace.policy.subject,
            trace.policy.region,
        )
        if sample_before_clock:
            if enforce_adapter_contract:
                raise AdapterContractError(
                    "sample event cannot execute before its observation clock"
                )
            interpreter.queue(event_name)
            interpreter.execute()
            clock.time = offset
            interpreter.execute()
        else:
            clock.time = offset
            interpreter.queue(event_name)
            interpreter.execute()
        instantaneous.append(
            InstantRecord(
                kind.value,
                trace.policy.subject,
                trace.policy.region,
                _iso(timestamp),
            )
        )
        previous = current

    sustained = tuple(
        SustainedRecord(
            trace.policy.trigger.value,
            trace.policy.subject,
            trace.policy.region,
            trace.policy.duration_seconds,
            _iso(first + timedelta(seconds=float(started))),
            _iso(first + timedelta(seconds=float(effective))),
            _iso(first + timedelta(seconds=float(emitted))),
        )
        for started, effective, emitted in interpreter.context["sustained"]
    )
    return Outcome(
        str(interpreter.context["domain_state"]),
        tuple(instantaneous),
        sustained,
    )


def _outcome_changed(expected: Outcome, actual: Outcome) -> list[str]:
    changed: list[str] = []
    if actual.final_state != expected.final_state:
        changed.append("finalState")
    if actual.instantaneous != expected.instantaneous:
        changed.append("instantaneousTrace")
    if actual.sustained != expected.sustained:
        changed.append("sustainedTrace")
    return changed


def _pulse_compile_detection(source: str) -> Detection:
    try:
        compile_pulse(source, "fault-injection.pulse")
    except PulseModelError as error:
        return Detection("compile", True, str(error))
    return Detection("none", False, "mutated model compiled")


def _scenario_source_after(
    statechart_text: str,
    *,
    clone_source: bool,
) -> str:
    import_from_yaml, Interpreter, _, _ = _require_statechart_runtime()
    source = {"status": "Safe"}
    branch = copy.deepcopy(source) if clone_source else source
    interpreter = Interpreter(
        import_from_yaml(text=statechart_text),
        initial_context={"world": branch},
    )
    interpreter.execute()
    interpreter.queue("assume_departure")
    interpreter.execute()
    return str(source["status"])


def _tie_trace(policy: Policy) -> StandardsTrace:
    first = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)
    return StandardsTrace(
        policy,
        (first, first + timedelta(minutes=1), first + timedelta(minutes=11)),
        (True, False, True),
        True,
        0,
        0,
    )


def run_statechart_comparison(
    composition_root: str | Path = DEFAULT_ROOT,
    experiment_root: str | Path = DEFAULT_EXPERIMENT_ROOT,
) -> dict[str, object]:
    composition = Path(composition_root)
    experiment = Path(experiment_root)
    standards = _load_standards_trace(composition)
    chart_path = experiment / "cold-chain" / "statechart.yaml"
    binding_path = experiment / "cold-chain" / "bindings.json"
    scenario_path = experiment / "scenario-isolation.yaml"
    chart_text = chart_path.read_text(encoding="utf-8")
    scenario_text = scenario_path.read_text(encoding="utf-8")
    binding = _load_binding(binding_path)
    _validate_binding(standards.policy, binding)

    pulse = run_pulse(composition).outcome
    statechart = _statechart_outcome(
        standards,
        chart_text,
        check_contracts=True,
    )

    pulse_source = (composition / "pulse" / "model.pulse").read_text("utf-8")
    identifier_pulse = _pulse_compile_detection(
        pulse_source.replace(
            "leaves(s.position, ColdZone)",
            "leaves(s.position, ColdStorage)",
        )
    )
    effect_pulse = _pulse_compile_detection(
        pulse_source.replace("Safe -> AtRisk", "Safe -> Quarantined")
    )

    identifier_chart = chart_text.replace("ColdZone", "ColdStorage")
    identifier_basic_outcome = _statechart_outcome(
        standards,
        identifier_chart,
        check_contracts=False,
    )
    identifier_basic = Detection(
        "outcome-oracle",
        identifier_basic_outcome != pulse,
        "changed: " + ", ".join(_outcome_changed(pulse, identifier_basic_outcome)),
    )
    identifier_profiled: Detection
    try:
        _validate_binding(
            standards.policy,
            StatechartBinding(
                binding.subject,
                "ColdStorage",
                binding.trigger,
                binding.from_state,
                binding.to_state,
                binding.duration_seconds,
                binding.state_domain,
            ),
        )
    except BindingContractError as error:
        identifier_profiled = Detection("load-binding", True, str(error))
    else:
        identifier_profiled = Detection("none", False, "binding accepted")

    effect_chart = chart_text.replace(
        "domain_state = 'AtRisk'",
        "domain_state = 'Quarantined'",
    )
    effect_basic_outcome = _statechart_outcome(
        standards,
        effect_chart,
        check_contracts=False,
    )
    effect_basic = Detection(
        "outcome-oracle",
        effect_basic_outcome != pulse,
        "changed: " + ", ".join(_outcome_changed(pulse, effect_basic_outcome)),
    )
    _, _, _, contract_error = _require_statechart_runtime()
    try:
        _statechart_outcome(standards, effect_chart, check_contracts=True)
    except contract_error as error:
        effect_profiled = Detection("statechart-invariant", True, type(error).__name__)
    else:
        effect_profiled = Detection("none", False, "invariant did not fire")

    tie = _tie_trace(standards.policy)
    tie_expected = _statechart_outcome(tie, chart_text, check_contracts=True)
    order_basic_outcome = _statechart_outcome(
        tie,
        chart_text,
        check_contracts=False,
        sample_before_clock=True,
    )
    order_basic = Detection(
        "outcome-oracle",
        order_basic_outcome != tie_expected,
        "changed: " + ", ".join(
            _outcome_changed(tie_expected, order_basic_outcome)
        ),
    )
    try:
        _statechart_outcome(
            tie,
            chart_text,
            check_contracts=True,
            sample_before_clock=True,
            enforce_adapter_contract=True,
        )
    except AdapterContractError as error:
        order_profiled = Detection("adapter-precondition", True, str(error))
    else:
        order_profiled = Detection("none", False, "adapter accepted bad order")

    scenario_basic_state = _scenario_source_after(
        scenario_text,
        clone_source=False,
    )
    scenario_profiled_state = _scenario_source_after(
        scenario_text,
        clone_source=True,
    )
    isolation_basic = Detection(
        "source-state-oracle",
        scenario_basic_state != "Safe",
        f"authoritative source ended in {scenario_basic_state}",
    )
    isolation_profiled = Detection(
        "prevented-by-clone-adapter",
        scenario_profiled_state == "Safe",
        f"authoritative source remained {scenario_profiled_state}",
    )
    paper_model = load_pulse(Path("examples/paper_cold_chain_st.pulse"))
    source_state = paper_model.world.states["batch"]
    paper_model.run_scenario("Reroute")
    pulse_isolated = paper_model.world.states["batch"] == source_state

    faults = (
        {
            "id": "F-IDENTIFIER-DRIFT",
            "fault": "statechart region binding differs from the RDF/PULSE region",
            "pulse": asdict(identifier_pulse),
            "unprofiledRdfStatechart": asdict(identifier_basic),
            "profiledRdfStatechart": asdict(identifier_profiled),
        },
        {
            "id": "F-EFFECT-DOMAIN",
            "fault": "workflow action writes a value outside the RDF/PULSE state domain",
            "pulse": asdict(effect_pulse),
            "unprofiledRdfStatechart": asdict(effect_basic),
            "profiledRdfStatechart": asdict(effect_profiled),
        },
        {
            "id": "F-SAMPLE-BEFORE-CLOCK",
            "fault": "adapter executes a sampled crossing before advancing its clock",
            "pulse": asdict(
                Detection(
                    "prevented-by-runtime-api",
                    True,
                    "move_at advances due timers before deriving the crossing",
                )
            ),
            "unprofiledRdfStatechart": asdict(order_basic),
            "profiledRdfStatechart": asdict(order_profiled),
        },
        {
            "id": "F-SCENARIO-ALIAS",
            "fault": "scenario interpreter receives the authoritative state by alias",
            "pulse": asdict(
                Detection(
                    "prevented-by-scenario-runtime",
                    pulse_isolated,
                    "source world remained unchanged",
                )
            ),
            "unprofiledRdfStatechart": asdict(isolation_basic),
            "profiledRdfStatechart": asdict(isolation_profiled),
        },
    )

    return {
        "experiment": "rdf-shacl-sismic-fault-location-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "baseline": {
            "task": "cold-chain cancellation and ten-minute sustained departure",
            "statechartEngine": "Sismic 1.6.11",
            "statechartSemantics": "SCXML-oriented run-to-completion interpreter",
            "shaclConforms": standards.shacl_conforms,
            "rdfTriples": standards.rdf_triples,
            "shapeTriples": standards.shape_triples,
            "pulseOutcome": asdict(pulse),
            "rdfStatechartOutcome": asdict(statechart),
            "exactOutcomeMatch": statechart == pulse,
        },
        "faultDesign": {
            "paths": [
                "PULSE compiler/runtime",
                "RDF+SHACL+Sismic without cross-artifact profile",
                "RDF+SHACL+Sismic with binding, invariant, and adapter contracts",
            ],
            "unchangedOracle": "exact final state and event traces",
            "detectionStages": [
                "compile/load",
                "statechart or adapter contract",
                "outcome oracle",
                "prevented by fixed runtime/adapter",
            ],
        },
        "faults": list(faults),
        "summary": {
            "faultCount": len(faults),
            "pulsePreventedOrDetected": sum(
                bool(fault["pulse"]["detected"]) for fault in faults
            ),
            "unprofiledDetectedByOracle": sum(
                fault["unprofiledRdfStatechart"]["stage"]
                in {"outcome-oracle", "source-state-oracle"}
                and bool(fault["unprofiledRdfStatechart"]["detected"])
                for fault in faults
            ),
            "profiledPreventedOrDetected": sum(
                bool(fault["profiledRdfStatechart"]["detected"])
                for fault in faults
            ),
        },
        "claimBoundary": (
            "One matched task and four deliberately injected integration faults. "
            "The result locates enforcement and shows that an explicit statechart "
            "profile can recover the checked obligations with extra binding, "
            "invariant, and adapter contracts. It is not a usability, maintenance, "
            "fault-prevalence, or language-superiority study."
        ),
    }


def render_markdown(result: dict[str, object]) -> str:
    baseline = result["baseline"]
    faults = result["faults"]
    summary = result["summary"]
    assert isinstance(baseline, dict)
    assert isinstance(faults, list)
    assert isinstance(summary, dict)
    lines = [
        "# RDF/SHACL + Sismic comparison",
        "",
        f"- Exact baseline outcome match: **{baseline['exactOutcomeMatch']}**",
        f"- PULSE prevented/detected: **{summary['pulsePreventedOrDetected']}/{summary['faultCount']}**",
        "- Unprofiled composition detected only by outcome oracle: "
        f"**{summary['unprofiledDetectedByOracle']}/{summary['faultCount']}**",
        "- Profiled composition prevented/detected: "
        f"**{summary['profiledPreventedOrDetected']}/{summary['faultCount']}**",
        "",
        "| Fault | PULSE | RDF+Sismic | Profiled RDF+Sismic |",
        "|---|---|---|---|",
    ]
    for fault in faults:
        lines.append(
            f"| {fault['id']} | {fault['pulse']['stage']} | "
            f"{fault['unprofiledRdfStatechart']['stage']} | "
            f"{fault['profiledRdfStatechart']['stage']} |"
        )
    lines.extend(("", "## Claim boundary", "", str(result["claimBoundary"]), ""))
    return "\n".join(lines)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-statechart-comparison",
        description="Run the matched RDF/SHACL plus Sismic comparison.",
    )
    parser.add_argument("--composition-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-complete", action="store_true")
    arguments = parser.parse_args()
    result = run_statechart_comparison(
        arguments.composition_root,
        arguments.experiment_root,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    baseline = result["baseline"]
    summary = result["summary"]
    assert isinstance(baseline, dict)
    assert isinstance(summary, dict)
    if arguments.require_complete and not (
        baseline["exactOutcomeMatch"]
        and summary["pulsePreventedOrDetected"] == summary["faultCount"]
        and summary["unprofiledDetectedByOracle"] == summary["faultCount"]
        and summary["profiledPreventedOrDetected"] == summary["faultCount"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
