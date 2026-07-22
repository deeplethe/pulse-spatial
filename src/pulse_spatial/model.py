"""Role-aware spatial records and authoritative world state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .geometry import Point, Polygon, covered_by, within


@dataclass(frozen=True, slots=True)
class LocationObservation:
    subject: str
    value: Point
    observed_at: datetime
    source: str
    confidence: float | None = None
    accuracy_m: float | None = None
    property_name: str = "position"

    def __post_init__(self) -> None:
        if not self.subject or not self.source or not self.property_name:
            raise ValueError(
                "Observation subject, source, and property name are required"
            )
        if self.observed_at.utcoffset() is None:
            raise ValueError("Observation time must include a UTC offset")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("Observation confidence must be between 0 and 1")
        if self.accuracy_m is not None and self.accuracy_m < 0:
            raise ValueError("Observation accuracy cannot be negative")


@dataclass(frozen=True, slots=True)
class SpatialViolation:
    constraint: str
    subject: str
    region: str
    message: str


@dataclass(frozen=True, slots=True)
class GeofenceConstraint:
    name: str
    subject: str
    region: str
    predicate: str = "inside"
    while_state: str | None = None
    property_name: str = "position"

    def evaluate(self, world: "SpatialWorld") -> tuple[SpatialViolation, ...]:
        if self.while_state is not None and world.states.get(self.subject) != self.while_state:
            return ()
        if self.subject not in world.positions:
            return (
                SpatialViolation(
                    self.name, self.subject, self.region, "asserted position is missing"
                ),
            )
        if self.region not in world.regions:
            return (
                SpatialViolation(self.name, self.subject, self.region, "region is missing"),
            )

        predicate = {"inside": within, "coveredBy": covered_by}.get(self.predicate)
        if predicate is None:
            raise ValueError(f"Unsupported spatial predicate: {self.predicate}")
        if predicate(world.positions[self.subject], world.regions[self.region]):
            return ()
        return (
            SpatialViolation(
                self.name,
                self.subject,
                self.region,
                f"{self.predicate} predicate is false",
            ),
        )


@dataclass(slots=True)
class SpatialWorld:
    regions: dict[str, Polygon] = field(default_factory=dict)
    positions: dict[str, Point] = field(default_factory=dict)
    states: dict[str, str] = field(default_factory=dict)
    observations: list[LocationObservation] = field(default_factory=list)

    def clone(self) -> "SpatialWorld":
        return SpatialWorld(
            regions=dict(self.regions),
            positions=dict(self.positions),
            states=dict(self.states),
            observations=list(self.observations),
        )

    def assert_position(self, subject: str, value: Point) -> None:
        if not subject:
            raise ValueError("Position subject is required")
        self.positions[subject] = value

    def record_observation(self, observation: LocationObservation) -> None:
        self.observations.append(observation)

    def validate(
        self, constraints: tuple[GeofenceConstraint, ...]
    ) -> tuple[SpatialViolation, ...]:
        return tuple(
            violation
            for constraint in constraints
            for violation in constraint.evaluate(self)
        )
