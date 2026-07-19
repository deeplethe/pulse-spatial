"""Deterministic geofence event and scenario runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Iterable

from .geometry import Point, covered_by
from .model import SpatialWorld


class EventKind(str, Enum):
    ENTERS = "enters"
    LEAVES = "leaves"


@dataclass(frozen=True, slots=True)
class GeofenceEvent:
    kind: EventKind
    subject: str
    region: str


@dataclass(frozen=True, slots=True)
class GeofenceRule:
    name: str
    kind: EventKind
    subject: str
    region: str
    from_state: str
    to_state: str
    minimum_duration_seconds: float | None = None

    def __post_init__(self) -> None:
        if (
            self.minimum_duration_seconds is not None
            and self.minimum_duration_seconds <= 0
        ):
            raise ValueError("Rule duration must be positive")


@dataclass(frozen=True, slots=True)
class SustainedEventSpec:
    name: str
    kind: EventKind
    subject: str
    region: str
    duration_seconds: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Sustained event name is required")
        if self.duration_seconds <= 0:
            raise ValueError("Sustained event duration must be positive")


@dataclass(frozen=True, slots=True)
class SustainedGeofenceEvent:
    specification: str
    kind: EventKind
    subject: str
    region: str
    started_at: datetime
    effective_at: datetime
    emitted_at: datetime
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class TemporalStepResult:
    observed_at: datetime
    instantaneous: tuple[GeofenceEvent, ...]
    sustained: tuple[SustainedGeofenceEvent, ...]


@dataclass(frozen=True, slots=True)
class _PendingSustainedEvent:
    specification: SustainedEventSpec
    started_at: datetime
    rule: GeofenceRule | None = None


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    world: SpatialWorld
    events: tuple[GeofenceEvent, ...]


class SpatialRuntime:
    def __init__(
        self, world: SpatialWorld, rules: Iterable[GeofenceRule] = ()
    ) -> None:
        self.world = world
        self.rules = tuple(rules)
        if any(rule.minimum_duration_seconds is not None for rule in self.rules):
            raise ValueError(
                "Duration-qualified rules require TemporalSpatialRuntime"
            )

    def move(self, subject: str, target: Point) -> tuple[GeofenceEvent, ...]:
        source = self.world.positions.get(subject)
        if source is None:
            self.world.assert_position(subject, target)
            return ()
        if source.crs != target.crs:
            raise ValueError(
                f"Cannot move {subject!r} between CRSs: "
                f"{source.crs!r} != {target.crs!r}"
            )

        events: list[GeofenceEvent] = []
        for region_name, region in self.world.regions.items():
            if region.crs != source.crs:
                continue
            was_inside = covered_by(source, region)
            is_inside = covered_by(target, region)
            if not was_inside and is_inside:
                events.append(GeofenceEvent(EventKind.ENTERS, subject, region_name))
            elif was_inside and not is_inside:
                events.append(GeofenceEvent(EventKind.LEAVES, subject, region_name))

        self.world.assert_position(subject, target)
        for rule in self.rules:
            if self.world.states.get(rule.subject) != rule.from_state:
                continue
            if any(
                event.kind is rule.kind
                and event.subject == rule.subject
                and event.region == rule.region
                for event in events
            ):
                self.world.states[rule.subject] = rule.to_state
        return tuple(events)

    def scenario(self, moves: Iterable[tuple[str, Point]]) -> ScenarioResult:
        scenario_world = self.world.clone()
        scenario_runtime = SpatialRuntime(scenario_world, self.rules)
        events = tuple(
            event
            for subject, target in moves
            for event in scenario_runtime.move(subject, target)
        )
        return ScenarioResult(scenario_world, events)


def _require_aware(value: datetime, label: str) -> None:
    if value.utcoffset() is None:
        raise ValueError(f"{label} must include a UTC offset")


class TemporalSpatialRuntime:
    """Discrete-time geofence runtime with sample-and-hold duration semantics."""

    def __init__(
        self,
        world: SpatialWorld,
        initial_time: datetime,
        rules: Iterable[GeofenceRule] = (),
        sustained_events: Iterable[SustainedEventSpec] = (),
    ) -> None:
        _require_aware(initial_time, "Initial time")
        self.world = world
        self.current_time = initial_time
        self.rules = tuple(rules)
        self.immediate_rules = tuple(
            rule for rule in self.rules if rule.minimum_duration_seconds is None
        )
        rule_specs = tuple(
            SustainedEventSpec(
                rule.name,
                rule.kind,
                rule.subject,
                rule.region,
                float(rule.minimum_duration_seconds),
            )
            for rule in self.rules
            if rule.minimum_duration_seconds is not None
        )
        self.specifications = (*tuple(sustained_events), *rule_specs)
        names = [specification.name for specification in self.specifications]
        if len(names) != len(set(names)):
            raise ValueError("Sustained event names must be unique")
        rules_by_name = {
            rule.name: rule
            for rule in self.rules
            if rule.minimum_duration_seconds is not None
        }
        self._rules_by_specification = rules_by_name
        self._pending: dict[str, _PendingSustainedEvent] = {}

    def advance_to(self, target_time: datetime) -> tuple[SustainedGeofenceEvent, ...]:
        _require_aware(target_time, "Target time")
        if target_time < self.current_time:
            raise ValueError("Temporal runtime cannot move backwards")
        due = sorted(
            (
                pending
                for pending in self._pending.values()
                if pending.started_at
                + timedelta(seconds=pending.specification.duration_seconds)
                <= target_time
            ),
            key=lambda pending: (
                pending.started_at
                + timedelta(seconds=pending.specification.duration_seconds),
                pending.specification.name,
            ),
        )
        emitted: list[SustainedGeofenceEvent] = []
        for pending in due:
            specification = pending.specification
            effective_at = pending.started_at + timedelta(
                seconds=specification.duration_seconds
            )
            event = SustainedGeofenceEvent(
                specification.name,
                specification.kind,
                specification.subject,
                specification.region,
                pending.started_at,
                effective_at,
                target_time,
                specification.duration_seconds,
            )
            emitted.append(event)
            if (
                pending.rule is not None
                and self.world.states.get(pending.rule.subject)
                == pending.rule.from_state
            ):
                self.world.states[pending.rule.subject] = pending.rule.to_state
            del self._pending[specification.name]
        self.current_time = target_time
        return tuple(emitted)

    def move_at(
        self,
        subject: str,
        target: Point,
        observed_at: datetime,
    ) -> TemporalStepResult:
        source = self.world.positions.get(subject)
        if source is not None and source.crs != target.crs:
            raise ValueError(
                f"Cannot move {subject!r} between CRSs: "
                f"{source.crs!r} != {target.crs!r}"
            )
        sustained = self.advance_to(observed_at)
        instantaneous = SpatialRuntime(
            self.world,
            self.immediate_rules,
        ).move(subject, target)
        for event in instantaneous:
            cancelled = tuple(
                name
                for name, pending in self._pending.items()
                if pending.specification.subject == event.subject
                and pending.specification.region == event.region
                and pending.specification.kind is not event.kind
            )
            for name in cancelled:
                del self._pending[name]
            for specification in self.specifications:
                if (
                    specification.kind is not event.kind
                    or specification.subject != event.subject
                    or specification.region != event.region
                ):
                    continue
                rule = self._rules_by_specification.get(specification.name)
                if (
                    rule is not None
                    and self.world.states.get(rule.subject) != rule.from_state
                ):
                    continue
                self._pending[specification.name] = _PendingSustainedEvent(
                    specification,
                    observed_at,
                    rule,
                )
        return TemporalStepResult(observed_at, instantaneous, sustained)
