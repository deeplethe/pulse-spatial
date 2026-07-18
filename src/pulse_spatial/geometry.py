"""Small dependency-free geometry kernel for the first PULSE-S semantic slice."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, TypeAlias


CRS84 = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
_EPSILON = 1e-12


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float
    crs: str = CRS84

    def __post_init__(self) -> None:
        if not isfinite(self.x) or not isfinite(self.y):
            raise ValueError("Point coordinates must be finite")
        if not self.crs:
            raise ValueError("Point CRS must be explicit")


@dataclass(frozen=True, slots=True)
class Polygon:
    shell: tuple[Point, ...]

    def __post_init__(self) -> None:
        if len(self.shell) < 4:
            raise ValueError("Polygon shell requires at least four coordinates")
        if self.shell[0] != self.shell[-1]:
            raise ValueError("Polygon shell must be closed")
        if any(point.crs != self.shell[0].crs for point in self.shell):
            raise ValueError("Polygon coordinates must share one CRS")

    @classmethod
    def from_xy(
        cls, coordinates: Iterable[tuple[float, float]], crs: str = CRS84
    ) -> "Polygon":
        points = tuple(Point(x, y, crs) for x, y in coordinates)
        if points and points[0] != points[-1]:
            points = (*points, points[0])
        return cls(points)

    @property
    def crs(self) -> str:
        return self.shell[0].crs


Geometry: TypeAlias = Point | Polygon


def _require_same_crs(point: Point, polygon: Polygon) -> None:
    if point.crs != polygon.crs:
        raise ValueError(f"CRS mismatch: {point.crs!r} != {polygon.crs!r}")


def _point_on_segment(point: Point, start: Point, end: Point) -> bool:
    cross = (point.y - start.y) * (end.x - start.x) - (
        point.x - start.x
    ) * (end.y - start.y)
    if abs(cross) > _EPSILON:
        return False
    dot = (point.x - start.x) * (end.x - start.x) + (
        point.y - start.y
    ) * (end.y - start.y)
    if dot < -_EPSILON:
        return False
    length_squared = (end.x - start.x) ** 2 + (end.y - start.y) ** 2
    return dot <= length_squared + _EPSILON


def on_boundary(point: Point, polygon: Polygon) -> bool:
    _require_same_crs(point, polygon)
    return any(
        _point_on_segment(point, start, end)
        for start, end in zip(polygon.shell, polygon.shell[1:])
    )


def within(point: Point, polygon: Polygon) -> bool:
    """Return Simple Features-style strict containment; boundary is excluded."""

    _require_same_crs(point, polygon)
    if on_boundary(point, polygon):
        return False

    inside = False
    for start, end in zip(polygon.shell, polygon.shell[1:]):
        crosses_scanline = (start.y > point.y) != (end.y > point.y)
        if not crosses_scanline:
            continue
        x_intersection = (
            (end.x - start.x) * (point.y - start.y) / (end.y - start.y)
            + start.x
        )
        if point.x < x_intersection:
            inside = not inside
    return inside


def covered_by(point: Point, polygon: Polygon) -> bool:
    """Return containment including the polygon boundary."""

    return on_boundary(point, polygon) or within(point, polygon)


def _number(value: float) -> str:
    return format(value, ".15g")


def to_wkt(geometry: Geometry) -> str:
    if isinstance(geometry, Point):
        return f"POINT ({_number(geometry.x)} {_number(geometry.y)})"
    coordinates = ", ".join(
        f"{_number(point.x)} {_number(point.y)}" for point in geometry.shell
    )
    return f"POLYGON (({coordinates}))"


def to_geosparql_wkt(geometry: Geometry) -> str:
    return f"<{geometry.crs}> {to_wkt(geometry)}"
