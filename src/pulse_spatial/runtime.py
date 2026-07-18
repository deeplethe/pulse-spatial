"""Deterministic geofence event and scenario runtime."""

from __future__ import annotations

from dataclasses import dataclass
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
