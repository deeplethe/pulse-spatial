"""Experimental modal spatial semantics for PULSE."""

from .compiler import (
    CompiledModel,
    PulseModelError,
    QuestionAnswer,
    ScenarioReport,
    compile_document,
    compile_pulse,
    load_pulse,
)
from .geometry import CRS84, Point, Polygon, covered_by, to_geosparql_wkt, within
from .model import (
    GeofenceConstraint,
    LocationObservation,
    SpatialViolation,
    SpatialWorld,
)
from .projection import (
    DEFAULT_BASE_IRI,
    ProjectionBundle,
    ProjectionPaths,
    project_data_graph,
    project_geosparql,
    project_shacl,
    project_sosa,
    project_standards,
    write_projection_bundle,
)
from .parser import PulseSyntaxError, parse_pulse
from .runtime import EventKind, GeofenceEvent, GeofenceRule, ScenarioResult, SpatialRuntime
from .validation import (
    CrossViewValidation,
    ReferenceBackendUnavailable,
    geosparql_reference_functions,
    validate_projection_parity,
)

__all__ = [
    "CRS84",
    "CompiledModel",
    "CrossViewValidation",
    "DEFAULT_BASE_IRI",
    "EventKind",
    "GeofenceConstraint",
    "GeofenceEvent",
    "GeofenceRule",
    "LocationObservation",
    "Point",
    "Polygon",
    "ProjectionBundle",
    "ProjectionPaths",
    "PulseModelError",
    "PulseSyntaxError",
    "QuestionAnswer",
    "ReferenceBackendUnavailable",
    "ScenarioResult",
    "ScenarioReport",
    "SpatialRuntime",
    "SpatialViolation",
    "SpatialWorld",
    "covered_by",
    "compile_document",
    "compile_pulse",
    "load_pulse",
    "geosparql_reference_functions",
    "parse_pulse",
    "project_data_graph",
    "project_geosparql",
    "project_shacl",
    "project_sosa",
    "project_standards",
    "to_geosparql_wkt",
    "validate_projection_parity",
    "within",
    "write_projection_bundle",
]
