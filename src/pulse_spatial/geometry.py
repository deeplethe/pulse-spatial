"""Small dependency-free geometry kernel for the first PULSE-S semantic slice."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import isfinite
from typing import Iterable, TypeAlias


CRS84 = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
_ORIENTATION_ERROR_FACTOR = 4.0 * 2.220446049250313e-16


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
        vertices = self.shell[:-1]
        if len(set(vertices)) < 3:
            raise ValueError("Polygon shell requires three distinct vertices")
        if any(start == end for start, end in zip(self.shell, self.shell[1:])):
            raise ValueError("Polygon shell cannot contain zero-length edges")
        if not any(
            _orientation(vertices[0], vertices[index], vertices[index + 1])
            for index in range(1, len(vertices) - 1)
        ):
            raise ValueError("Polygon shell cannot be collinear")
        edges = tuple(zip(self.shell, self.shell[1:]))
        for first_index, first in enumerate(edges):
            for second_index in range(first_index + 1, len(edges)):
                adjacent = second_index == first_index + 1 or (
                    first_index == 0 and second_index == len(edges) - 1
                )
                if adjacent:
                    continue
                if _segments_intersect(*first, *edges[second_index]):
                    raise ValueError("Polygon shell must be simple")

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


def _orientation(first: Point, second: Point, third: Point) -> int:
    """Return the robust orientation sign for three binary64 points.

    The common floating-point path is used unless its determinant is within a
    conservative rounding-error bound. Ambiguous cases fall back to exact
    rational arithmetic over the supplied binary64 values. This keeps topology
    independent of an arbitrary coordinate-unit epsilon.
    """

    left = (second.x - first.x) * (third.y - first.y)
    right = (second.y - first.y) * (third.x - first.x)
    determinant = left - right
    error_bound = _ORIENTATION_ERROR_FACTOR * (abs(left) + abs(right))
    if determinant > error_bound:
        return 1
    if determinant < -error_bound:
        return -1

    fx = Fraction
    exact = (fx(second.x) - fx(first.x)) * (fx(third.y) - fx(first.y)) - (
        fx(second.y) - fx(first.y)
    ) * (fx(third.x) - fx(first.x))
    return (exact > 0) - (exact < 0)


def _point_on_segment(point: Point, start: Point, end: Point) -> bool:
    return _orientation(start, end, point) == 0 and (
        min(start.x, end.x) <= point.x <= max(start.x, end.x)
        and min(start.y, end.y) <= point.y <= max(start.y, end.y)
    )


def _segments_intersect(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
) -> bool:
    first_a = _orientation(first_start, first_end, second_start)
    first_b = _orientation(first_start, first_end, second_end)
    second_a = _orientation(second_start, second_end, first_start)
    second_b = _orientation(second_start, second_end, first_end)
    if first_a != first_b and second_a != second_b:
        return True
    return (
        (first_a == 0 and _point_on_segment(second_start, first_start, first_end))
        or (first_b == 0 and _point_on_segment(second_end, first_start, first_end))
        or (second_a == 0 and _point_on_segment(first_start, second_start, second_end))
        or (second_b == 0 and _point_on_segment(first_end, second_start, second_end))
    )


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
