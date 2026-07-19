"""Optional SHACL-SPARQL/GEOS reference validation for projected models."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, Iterator

from .geometry import CRS84
from .model import GeofenceConstraint, SpatialViolation, SpatialWorld
from .projection import DEFAULT_BASE_IRI, project_standards


_GEOF = "http://www.opengis.net/def/function/geosparql/"
_GEO_WKT_LITERAL = "http://www.opengis.net/ont/geosparql#wktLiteral"
_SH = "http://www.w3.org/ns/shacl#"


class ReferenceBackendUnavailable(RuntimeError):
    """Raised when optional projection-validation dependencies are absent."""


@dataclass(frozen=True, slots=True)
class CrossViewValidation:
    matches: bool
    internal_conforms: bool
    projected_conforms: bool
    internal_violations: tuple[SpatialViolation, ...]
    projected_result_count: int
    report_text: str


def _dependency_error(error: ImportError) -> ReferenceBackendUnavailable:
    return ReferenceBackendUnavailable(
        "Projection validation requires the optional validation dependencies; "
        "install with `python -m pip install -e .[validation]`"
    )


@contextmanager
def geosparql_reference_functions() -> Iterator[None]:
    """Register the two projected GeoSPARQL functions using Shapely/GEOS.

    Existing registrations are preserved. Registrations created here are
    process-global in RDFLib and are removed when the context exits.
    """

    try:
        from rdflib import Literal, URIRef
        from rdflib.plugins.sparql.operators import (
            register_custom_function,
            unregister_custom_function,
        )
        from rdflib.plugins.sparql.sparql import SPARQLError
        from shapely import from_wkt, intersects, within
        from shapely.errors import GEOSException
    except ImportError as error:
        raise _dependency_error(error) from error

    def parse_geometry(term):
        if not isinstance(term, Literal) or str(term.datatype) != _GEO_WKT_LITERAL:
            raise SPARQLError("GeoSPARQL reference functions require geo:wktLiteral")
        lexical = str(term).strip()
        crs = CRS84
        if lexical.startswith("<"):
            closing = lexical.find(">")
            if closing <= 1:
                raise SPARQLError(f"Malformed GeoSPARQL WKT literal: {lexical!r}")
            crs = lexical[1:closing]
            lexical = lexical[closing + 1 :].strip()
        if not lexical:
            raise SPARQLError("GeoSPARQL WKT literal has no geometry value")
        try:
            return crs, from_wkt(lexical)
        except GEOSException as error:
            raise SPARQLError(f"Invalid WKT geometry: {error}") from error

    def operands(left, right):
        left_crs, left_geometry = parse_geometry(left)
        right_crs, right_geometry = parse_geometry(right)
        if left_crs != right_crs:
            raise SPARQLError(
                f"GeoSPARQL reference adapter rejects mixed CRSs: "
                f"{left_crs!r} != {right_crs!r}"
            )
        return left_geometry, right_geometry

    def sf_within(left, right):
        left_geometry, right_geometry = operands(left, right)
        return Literal(bool(within(left_geometry, right_geometry)))

    def sf_intersects(left, right):
        left_geometry, right_geometry = operands(left, right)
        return Literal(bool(intersects(left_geometry, right_geometry)))

    functions = (
        (URIRef(f"{_GEOF}sfWithin"), sf_within),
        (URIRef(f"{_GEOF}sfIntersects"), sf_intersects),
    )
    registered = []
    try:
        for iri, function in functions:
            try:
                register_custom_function(iri, function)
            except ValueError:
                continue
            registered.append(iri)
        yield
    finally:
        for iri in registered:
            unregister_custom_function(iri)


def validate_projection_parity(
    world: SpatialWorld,
    constraints: Iterable[GeofenceConstraint],
    base_iri: str = DEFAULT_BASE_IRI,
) -> CrossViewValidation:
    """Compare internal geofence validation with the projected SHACL result."""

    try:
        from pyshacl import validate
        from rdflib import Graph, Namespace
        from rdflib.namespace import RDF
    except ImportError as error:
        raise _dependency_error(error) from error

    constraint_values = tuple(constraints)
    internal_violations = world.validate(constraint_values)
    bundle = project_standards(world, constraint_values, base_iri)
    data_graph = Graph().parse(data=bundle.data_graph, format="turtle")
    shapes_graph = Graph().parse(data=bundle.shapes_graph, format="turtle")
    with geosparql_reference_functions():
        projected_conforms, report_graph, report_text = validate(
            data_graph,
            shacl_graph=shapes_graph,
            advanced=True,
        )
    if not isinstance(report_graph, Graph):
        message = getattr(report_graph, "message", report_text)
        raise RuntimeError(f"SHACL validation failed: {message}")
    sh = Namespace(_SH)
    result_count = len(set(report_graph.subjects(RDF.type, sh.ValidationResult)))
    internal_conforms = not internal_violations
    projected_conforms = bool(projected_conforms)
    matches = (
        internal_conforms == projected_conforms
        and len(internal_violations) == result_count
    )
    return CrossViewValidation(
        matches,
        internal_conforms,
        projected_conforms,
        internal_violations,
        result_count,
        str(report_text),
    )
