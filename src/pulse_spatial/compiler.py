"""Semantic validation and compilation from PULSE-S syntax to the runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, TypeVar

from .geometry import Point, Polygon, covered_by, within
from .language import (
    Duration,
    EntityDecl,
    GeometryLiteral,
    ModelDocument,
    Question,
    Reference,
    ScenarioDecl,
    SpatialQuestion,
    ValueQuestion,
)
from .model import (
    GeofenceConstraint,
    LocationObservation,
    SpatialViolation,
    SpatialWorld,
)
from .parser import parse_pulse
from .runtime import (
    EventKind,
    GeofenceRule,
    ScenarioResult,
    SpatialRuntime,
)


class PulseModelError(ValueError):
    """Raised when a parsed PULSE-S document is not semantically valid."""


@dataclass(frozen=True, slots=True)
class CompiledScenario:
    declaration: ScenarioDecl
    moves: tuple[tuple[str, Point], ...]


@dataclass(frozen=True, slots=True)
class QuestionAnswer:
    question: str
    value: object


@dataclass(frozen=True, slots=True)
class ScenarioReport:
    name: str
    horizon_seconds: float | None
    result: ScenarioResult
    answers: tuple[QuestionAnswer, ...]


@dataclass(slots=True)
class CompiledModel:
    document: ModelDocument
    world: SpatialWorld
    rules: tuple[GeofenceRule, ...]
    constraints: tuple[GeofenceConstraint, ...]
    scenarios: dict[str, CompiledScenario]
    instance_entities: dict[str, str]
    spatial_members: dict[str, str]
    state_members: dict[str, str]
    instance_values: dict[tuple[str, str], object]

    def runtime(self) -> SpatialRuntime:
        return SpatialRuntime(self.world, self.rules)

    def validate(self) -> tuple[SpatialViolation, ...]:
        return self.world.validate(self.constraints)

    def run_scenario(self, name: str) -> ScenarioReport:
        try:
            scenario = self.scenarios[name]
        except KeyError as error:
            raise PulseModelError(f"unknown scenario {name!r}") from error
        result = self.runtime().scenario(scenario.moves)
        answers = tuple(
            QuestionAnswer(str(question), self._answer(question, result.world))
            for question in scenario.declaration.questions
        )
        return ScenarioReport(
            name,
            _duration_seconds(scenario.declaration.run_for),
            result,
            answers,
        )

    def _answer(self, question: Question, world: SpatialWorld) -> object:
        if isinstance(question, SpatialQuestion):
            point = world.positions[question.reference.owner]
            region = world.regions[question.region]
            predicate = {"inside": within, "coveredBy": covered_by}[question.predicate]
            return predicate(point, region)

        reference = question.reference
        entity = self.instance_entities[reference.owner]
        if self.spatial_members.get(entity) == reference.member:
            return world.positions[reference.owner]
        if self.state_members.get(entity) == reference.member:
            return world.states[reference.owner]
        return self.instance_values[(reference.owner, reference.member)]


_Named = TypeVar("_Named")


def _index_unique(items: Iterable[_Named], label: str) -> dict[str, _Named]:
    result: dict[str, _Named] = {}
    for item in items:
        name = getattr(item, "name")
        if name in result:
            raise PulseModelError(f"duplicate {label} {name!r}")
        result[name] = item
    return result


def _duration_seconds(duration: Duration | None) -> float | None:
    if duration is None:
        return None
    factors = {"ms": 0.001, "s": 1.0, "min": 60.0, "h": 3600.0, "day": 86400.0}
    return duration.value * factors[duration.unit]


def _point(literal: GeometryLiteral, crs: str, context: str) -> Point:
    if literal.kind != "Point":
        raise PulseModelError(f"{context} requires a Point value")
    x, y = literal.coordinates[0]
    try:
        return Point(x, y, crs)
    except ValueError as error:
        raise PulseModelError(f"invalid geometry for {context}: {error}") from error


def _polygon(literal: GeometryLiteral, crs: str, context: str) -> Polygon:
    if literal.kind != "Polygon":
        raise PulseModelError(f"{context} requires a Polygon value")
    try:
        return Polygon.from_xy(literal.coordinates, crs)
    except ValueError as error:
        raise PulseModelError(f"invalid geometry for {context}: {error}") from error


def _entity_members(entity: EntityDecl) -> dict[str, object]:
    members: dict[str, object] = {}
    for member in (*entity.properties, *entity.states):
        if member.name in members:
            raise PulseModelError(
                f"duplicate member {member.name!r} in entity {entity.name!r}"
            )
        members[member.name] = member
    return members


def _validate_scalar(value: object, type_name: str, context: str) -> None:
    valid = {
        "String": isinstance(value, str),
        "Integer": isinstance(value, int) and not isinstance(value, bool),
        "Decimal": isinstance(value, (int, float)) and not isinstance(value, bool),
        "Boolean": isinstance(value, bool),
    }
    if type_name not in valid:
        raise PulseModelError(
            f"{context} uses unsupported scalar type {type_name!r}"
        )
    if not valid[type_name]:
        raise PulseModelError(f"{context} must have type {type_name}")


def _require_instance_reference(
    reference: Reference,
    instances: dict[str, object],
    instance_entities: dict[str, str],
    entity_members: dict[str, dict[str, object]],
) -> str:
    if reference.owner not in instances:
        raise PulseModelError(f"unknown instance {reference.owner!r} in {reference}")
    entity_name = instance_entities[reference.owner]
    if reference.member not in entity_members[entity_name]:
        raise PulseModelError(
            f"unknown member {reference.member!r} on instance {reference.owner!r}"
        )
    return entity_name


def compile_document(document: ModelDocument) -> CompiledModel:
    """Resolve and validate a parsed document, producing an executable model."""

    crs_declarations = _index_unique(document.crs, "CRS")
    if not crs_declarations:
        raise PulseModelError("the model must declare at least one CRS")
    for declaration in crs_declarations.values():
        if not declaration.iri:
            raise PulseModelError(f"CRS {declaration.name!r} has an empty IRI")

    region_declarations = _index_unique(document.regions, "region")
    regions: dict[str, Polygon] = {}
    for name, declaration in region_declarations.items():
        if declaration.crs not in crs_declarations:
            raise PulseModelError(
                f"region {name!r} references unknown CRS {declaration.crs!r}"
            )
        regions[name] = _polygon(
            declaration.geometry,
            crs_declarations[declaration.crs].iri,
            f"region {name!r}",
        )

    entities = _index_unique(document.entities, "entity")
    entity_members = {name: _entity_members(entity) for name, entity in entities.items()}
    spatial_members: dict[str, str] = {}
    state_members: dict[str, str] = {}
    for entity_name, entity in entities.items():
        for member in entity.properties:
            if member.type_name != "Point" and member.crs is not None:
                raise PulseModelError(
                    f"non-spatial property {entity_name}.{member.name} cannot declare a CRS"
                )
            if member.type_name == "Point" and member.unit is not None:
                raise PulseModelError(
                    f"spatial property {entity_name}.{member.name} cannot declare a unit"
                )
        spatial = [member for member in entity.properties if member.type_name == "Point"]
        unsupported_geometry = [
            member
            for member in entity.properties
            if member.type_name in {"LineString", "Polygon", "Trajectory"}
        ]
        if unsupported_geometry:
            names = ", ".join(member.name for member in unsupported_geometry)
            raise PulseModelError(
                f"entity {entity_name!r} uses geometry not executable in this slice: {names}"
            )
        if len(spatial) > 1:
            raise PulseModelError(
                f"entity {entity_name!r} may have at most one Point property in this slice"
            )
        if spatial:
            member = spatial[0]
            if member.crs is None:
                raise PulseModelError(
                    f"spatial property {entity_name}.{member.name} requires a CRS"
                )
            if member.crs not in crs_declarations:
                raise PulseModelError(
                    f"spatial property {entity_name}.{member.name} references unknown CRS "
                    f"{member.crs!r}"
                )
            spatial_members[entity_name] = member.name
        if len(entity.states) > 1:
            raise PulseModelError(
                f"entity {entity_name!r} may have at most one state member in this slice"
            )
        if entity.states:
            state = entity.states[0]
            if len(set(state.values)) != len(state.values):
                raise PulseModelError(
                    f"state domain {entity_name}.{state.name} contains duplicates"
                )
            state_members[entity_name] = state.name

    instances = _index_unique(document.instances, "instance")
    instance_entities: dict[str, str] = {}
    instance_values: dict[tuple[str, str], object] = {}
    positions: dict[str, Point] = {}
    states: dict[str, str] = {}
    for instance_name, instance in instances.items():
        if instance.entity not in entities:
            raise PulseModelError(
                f"instance {instance_name!r} has unknown entity {instance.entity!r}"
            )
        instance_entities[instance_name] = instance.entity
        members = entity_members[instance.entity]
        assignments: dict[str, object] = {}
        for assignment in instance.assignments:
            if assignment.member in assignments:
                raise PulseModelError(
                    f"duplicate assignment {instance_name}.{assignment.member}"
                )
            if assignment.member not in members:
                raise PulseModelError(
                    f"unknown member {instance_name}.{assignment.member}"
                )
            assignments[assignment.member] = assignment.value
        missing = set(members) - set(assignments)
        if missing:
            raise PulseModelError(
                f"instance {instance_name!r} is missing assignments: "
                f"{', '.join(sorted(missing))}"
            )

        entity = entities[instance.entity]
        for member in entity.properties:
            value = assignments[member.name]
            if member.type_name == "Point":
                assert member.crs is not None
                if not isinstance(value, GeometryLiteral):
                    raise PulseModelError(
                        f"{instance_name}.{member.name} requires a Point value"
                    )
                compiled_value = _point(
                    value,
                    crs_declarations[member.crs].iri,
                    f"{instance_name}.{member.name}",
                )
                positions[instance_name] = compiled_value
                instance_values[(instance_name, member.name)] = compiled_value
            else:
                if isinstance(value, GeometryLiteral):
                    raise PulseModelError(
                        f"{instance_name}.{member.name} does not accept geometry"
                    )
                _validate_scalar(
                    value, member.type_name, f"{instance_name}.{member.name}"
                )
                instance_values[(instance_name, member.name)] = value
        for state in entity.states:
            value = assignments[state.name]
            if not isinstance(value, str) or value not in state.values:
                raise PulseModelError(
                    f"{instance_name}.{state.name} must be one of {state.values!r}"
                )
            states[instance_name] = value
            instance_values[(instance_name, state.name)] = value

    world = SpatialWorld(regions=regions, positions=positions, states=states)
    for observation in document.observations:
        entity_name = _require_instance_reference(
            observation.reference, instances, instance_entities, entity_members
        )
        if spatial_members.get(entity_name) != observation.reference.member:
            raise PulseModelError(
                f"observation target {observation.reference} is not a Point property"
            )
        member = next(
            member
            for member in entities[entity_name].properties
            if member.name == observation.reference.member
        )
        assert member.crs is not None
        try:
            observed_at = datetime.fromisoformat(observation.observed_at)
        except ValueError as error:
            raise PulseModelError(
                f"invalid observation time {observation.observed_at!r}"
            ) from error
        accuracy_m = observation.accuracy
        if accuracy_m is not None and observation.accuracy_unit == "km":
            accuracy_m *= 1000
        try:
            world.record_observation(
                LocationObservation(
                    observation.reference.owner,
                    _point(
                        observation.value,
                        crs_declarations[member.crs].iri,
                        f"observation {observation.reference}",
                    ),
                    observed_at,
                    observation.source,
                    observation.confidence,
                    accuracy_m,
                )
            )
        except ValueError as error:
            raise PulseModelError(
                f"invalid observation for {observation.reference}: {error}"
            ) from error

    constraint_declarations = _index_unique(document.constraints, "constraint")
    constraints: list[GeofenceConstraint] = []
    for name, declaration in constraint_declarations.items():
        entity_name = _require_instance_reference(
            declaration.reference, instances, instance_entities, entity_members
        )
        if spatial_members.get(entity_name) != declaration.reference.member:
            raise PulseModelError(
                f"constraint target {declaration.reference} is not a Point property"
            )
        if declaration.region not in regions:
            raise PulseModelError(
                f"constraint {name!r} references unknown region {declaration.region!r}"
            )
        if declaration.predicate not in {"inside", "coveredBy"}:
            raise PulseModelError(
                f"constraint {name!r} has unsupported predicate {declaration.predicate!r}"
            )
        if (
            world.positions[declaration.reference.owner].crs
            != regions[declaration.region].crs
        ):
            raise PulseModelError(
                f"constraint {name!r} compares geometries in different CRSs"
            )
        while_state = None
        if declaration.while_reference is not None:
            reference = declaration.while_reference
            if reference.owner != entity_name:
                raise PulseModelError(
                    f"constraint {name!r} guard must reference entity {entity_name!r}"
                )
            if state_members.get(entity_name) != reference.member:
                raise PulseModelError(
                    f"constraint {name!r} guard is not the entity state member"
                )
            state = entities[entity_name].states[0]
            if declaration.while_value not in state.values:
                raise PulseModelError(
                    f"constraint {name!r} guard has unknown state "
                    f"{declaration.while_value!r}"
                )
            while_state = declaration.while_value
        constraints.append(
            GeofenceConstraint(
                name,
                declaration.reference.owner,
                declaration.region,
                declaration.predicate,
                while_state,
            )
        )

    process_declarations = _index_unique(document.processes, "process")
    rules: list[GeofenceRule] = []
    for name, declaration in process_declarations.items():
        if declaration.entity not in entities:
            raise PulseModelError(
                f"process {name!r} references unknown entity {declaration.entity!r}"
            )
        if declaration.event not in {"enters", "leaves"}:
            raise PulseModelError(
                f"process {name!r} requires an enters or leaves event"
            )
        if declaration.duration is not None:
            raise PulseModelError(
                f"duration-qualified event in process {name!r} is not executable yet"
            )
        if declaration.guard_reference.owner != declaration.parameter:
            raise PulseModelError(
                f"process {name!r} guard must use parameter {declaration.parameter!r}"
            )
        if spatial_members.get(declaration.entity) != declaration.guard_reference.member:
            raise PulseModelError(f"process {name!r} guard is not a Point property")
        if declaration.region not in regions:
            raise PulseModelError(
                f"process {name!r} references unknown region {declaration.region!r}"
            )
        spatial_member = next(
            member
            for member in entities[declaration.entity].properties
            if member.name == declaration.guard_reference.member
        )
        assert spatial_member.crs is not None
        if crs_declarations[spatial_member.crs].iri != regions[declaration.region].crs:
            raise PulseModelError(
                f"process {name!r} compares geometries in different CRSs"
            )
        transition = declaration.transition_reference
        if transition.owner != declaration.parameter:
            raise PulseModelError(
                f"process {name!r} transition must use parameter "
                f"{declaration.parameter!r}"
            )
        if state_members.get(declaration.entity) != transition.member:
            raise PulseModelError(f"process {name!r} transition is not a state member")
        state = entities[declaration.entity].states[0]
        if declaration.from_state not in state.values or declaration.to_state not in state.values:
            raise PulseModelError(f"process {name!r} uses a state outside {state.values!r}")
        for instance_name, instance_entity in instance_entities.items():
            if instance_entity == declaration.entity:
                rules.append(
                    GeofenceRule(
                        f"{name}@{instance_name}",
                        EventKind(declaration.event),
                        instance_name,
                        declaration.region,
                        declaration.from_state,
                        declaration.to_state,
                    )
                )

    scenario_declarations = _index_unique(document.scenarios, "scenario")
    scenarios: dict[str, CompiledScenario] = {}
    for name, declaration in scenario_declarations.items():
        moves: list[tuple[str, Point]] = []
        for assumption in declaration.assumptions:
            entity_name = _require_instance_reference(
                assumption.reference, instances, instance_entities, entity_members
            )
            if spatial_members.get(entity_name) != assumption.reference.member:
                raise PulseModelError(
                    f"scenario {name!r} currently supports only Point assumptions"
                )
            if not isinstance(assumption.value, GeometryLiteral):
                raise PulseModelError(
                    f"scenario assumption {assumption.reference} requires a Point"
                )
            member = next(
                member
                for member in entities[entity_name].properties
                if member.name == assumption.reference.member
            )
            assert member.crs is not None
            moves.append(
                (
                    assumption.reference.owner,
                    _point(
                        assumption.value,
                        crs_declarations[member.crs].iri,
                        f"scenario {name!r} assumption {assumption.reference}",
                    ),
                )
            )
        for question in declaration.questions:
            entity_name = _require_instance_reference(
                question.reference, instances, instance_entities, entity_members
            )
            if isinstance(question, SpatialQuestion):
                if question.predicate not in {"inside", "coveredBy"}:
                    raise PulseModelError(
                        f"scenario {name!r} has unsupported predicate "
                        f"{question.predicate!r}"
                    )
                if spatial_members.get(entity_name) != question.reference.member:
                    raise PulseModelError(
                        f"scenario question {question} is not over a Point property"
                    )
                if question.region not in regions:
                    raise PulseModelError(
                        f"scenario {name!r} references unknown region {question.region!r}"
                    )
                if (
                    world.positions[question.reference.owner].crs
                    != regions[question.region].crs
                ):
                    raise PulseModelError(
                        f"scenario question {question} compares different CRSs"
                    )
            elif not isinstance(question, ValueQuestion):
                raise PulseModelError(f"unsupported question in scenario {name!r}")
        scenarios[name] = CompiledScenario(declaration, tuple(moves))

    return CompiledModel(
        document,
        world,
        tuple(rules),
        tuple(constraints),
        scenarios,
        instance_entities,
        spatial_members,
        state_members,
        instance_values,
    )


def compile_pulse(source: str, source_name: str = "<string>") -> CompiledModel:
    """Parse, resolve, and validate PULSE-S source text."""

    return compile_document(parse_pulse(source, source_name))


def load_pulse(path: str | Path) -> CompiledModel:
    """Load a UTF-8 PULSE-S document from disk and compile it."""

    source_path = Path(path)
    return compile_pulse(source_path.read_text(encoding="utf-8"), str(source_path))
