"""Typed syntax model for the executable PULSE-S language slice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class Reference:
    owner: str
    member: str

    def __str__(self) -> str:
        return f"{self.owner}.{self.member}"


@dataclass(frozen=True, slots=True)
class GeometryLiteral:
    kind: str
    coordinates: tuple[tuple[float, float], ...]


ScalarValue: TypeAlias = str | int | float | bool
Value: TypeAlias = ScalarValue | GeometryLiteral


@dataclass(frozen=True, slots=True)
class Duration:
    value: float
    unit: str


@dataclass(frozen=True, slots=True)
class CrsDecl:
    name: str
    iri: str


@dataclass(frozen=True, slots=True)
class RegionDecl:
    name: str
    crs: str
    geometry: GeometryLiteral


@dataclass(frozen=True, slots=True)
class PropertyDecl:
    name: str
    type_name: str
    unit: str | None = None
    crs: str | None = None


@dataclass(frozen=True, slots=True)
class StateDecl:
    name: str
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntityDecl:
    name: str
    properties: tuple[PropertyDecl, ...]
    states: tuple[StateDecl, ...]


@dataclass(frozen=True, slots=True)
class Assignment:
    member: str
    value: Value


@dataclass(frozen=True, slots=True)
class InstanceDecl:
    name: str
    entity: str
    assignments: tuple[Assignment, ...]


@dataclass(frozen=True, slots=True)
class ObservationDecl:
    reference: Reference
    value: GeometryLiteral
    observed_at: str
    source: str
    confidence: float | None = None
    accuracy: float | None = None
    accuracy_unit: str | None = None


@dataclass(frozen=True, slots=True)
class ConstraintDecl:
    name: str
    predicate: str
    reference: Reference
    region: str
    while_reference: Reference | None = None
    while_value: str | None = None


@dataclass(frozen=True, slots=True)
class ProcessDecl:
    name: str
    parameter: str
    entity: str
    event: str
    guard_reference: Reference
    region: str
    duration: Duration | None
    transition_reference: Reference
    from_state: str
    to_state: str


@dataclass(frozen=True, slots=True)
class Assumption:
    reference: Reference
    value: Value


@dataclass(frozen=True, slots=True)
class SpatialQuestion:
    predicate: str
    reference: Reference
    region: str

    def __str__(self) -> str:
        return f"{self.predicate}({self.reference}, {self.region})"


@dataclass(frozen=True, slots=True)
class ValueQuestion:
    reference: Reference

    def __str__(self) -> str:
        return str(self.reference)


Question: TypeAlias = SpatialQuestion | ValueQuestion


@dataclass(frozen=True, slots=True)
class ScenarioDecl:
    name: str
    assumptions: tuple[Assumption, ...]
    run_for: Duration | None
    questions: tuple[Question, ...]


@dataclass(frozen=True, slots=True)
class ModelDocument:
    name: str
    version: str
    crs: tuple[CrsDecl, ...]
    regions: tuple[RegionDecl, ...]
    entities: tuple[EntityDecl, ...]
    instances: tuple[InstanceDecl, ...]
    observations: tuple[ObservationDecl, ...]
    constraints: tuple[ConstraintDecl, ...]
    processes: tuple[ProcessDecl, ...]
    scenarios: tuple[ScenarioDecl, ...]
