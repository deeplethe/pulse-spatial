"""Deterministic standards-oriented RDF projections for PULSE-S."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urlsplit

from .geometry import Geometry, to_geosparql_wkt
from .model import GeofenceConstraint, LocationObservation, SpatialWorld


DEFAULT_BASE_IRI = "https://w3id.org/pulse-spatial/resource"
_GEO = "http://www.opengis.net/ont/geosparql#"
_GEOF = "http://www.opengis.net/def/function/geosparql/"
_PULSE = "https://w3id.org/pulse-spatial/vocab#"
_SH = "http://www.w3.org/ns/shacl#"
_SOSA = "http://www.w3.org/ns/sosa/"
_XSD = "http://www.w3.org/2001/XMLSchema#"


@dataclass(frozen=True, slots=True)
class ProjectionBundle:
    data_graph: str
    shapes_graph: str


@dataclass(frozen=True, slots=True)
class ProjectionPaths:
    data_graph: Path
    shapes_graph: Path


def _validate_base_iri(base_iri: str) -> None:
    invalid_character = any(
        character.isspace() or character in '<>"{}|\\^`'
        for character in base_iri
    )
    if not base_iri or invalid_character or not urlsplit(base_iri).scheme:
        raise ValueError(f"Invalid base IRI: {base_iri!r}")


def _iri(base_iri: str, kind: str, name: str) -> str:
    _validate_base_iri(base_iri)
    return f"{base_iri.rstrip('/')}/{kind}/{quote(name, safe='')}"


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _number(value: float) -> str:
    return format(value, ".15g")


def _block(subject: str, predicates: Iterable[str]) -> str:
    values = tuple(predicates)
    return f"<{subject}> " + " ;\n  ".join(values) + " .\n"


def _feature_block(
    base_iri: str,
    kind: str,
    name: str,
    geometry: Geometry,
    *,
    include_modal_annotation: bool = False,
    include_sosa_type: bool = False,
) -> str:
    feature = _iri(base_iri, kind, name)
    geometry_iri = f"{feature}/geometry"
    feature_types = "geo:Feature"
    if include_sosa_type:
        feature_types += ", sosa:FeatureOfInterest"
    geometry_predicates = [
        "a geo:Geometry",
        f"geo:asWKT {_string(to_geosparql_wkt(geometry))}^^geo:wktLiteral",
    ]
    if include_modal_annotation:
        geometry_predicates.append("pulse:modality pulse:Asserted")
    return _block(
        feature,
        (f"a {feature_types}", f"geo:hasGeometry <{geometry_iri}>"),
    ) + _block(geometry_iri, geometry_predicates)


def _observation_block(
    observation: LocationObservation,
    index: int,
    base_iri: str,
) -> str:
    observation_iri = _iri(base_iri, "observation", f"{index:04d}")
    result_iri = f"{observation_iri}/result"
    feature_iri = _iri(base_iri, "instance", observation.subject)
    property_iri = _iri(base_iri, "property", observation.property_name)
    sensor_iri = _iri(base_iri, "sensor", observation.source)
    predicates = [
        "a sosa:Observation",
        f"sosa:hasFeatureOfInterest <{feature_iri}>",
        f"sosa:observedProperty <{property_iri}>",
        f"sosa:madeBySensor <{sensor_iri}>",
        f"sosa:hasResult <{result_iri}>",
        f"sosa:resultTime {_string(observation.observed_at.isoformat())}^^xsd:dateTime",
        "pulse:modality pulse:Observed",
    ]
    if observation.confidence is not None:
        predicates.append(
            f'pulse:confidence "{_number(observation.confidence)}"^^xsd:decimal'
        )
    if observation.accuracy_m is not None:
        predicates.append(
            f'pulse:accuracyMetres "{_number(observation.accuracy_m)}"^^xsd:decimal'
        )
    return _block(observation_iri, predicates) + _block(
        result_iri,
        (
            "a geo:Geometry, sosa:Result",
            f"geo:asWKT {_string(to_geosparql_wkt(observation.value))}^^geo:wktLiteral",
        ),
    )


def _observation_resources(world: SpatialWorld, base_iri: str) -> str:
    properties = sorted(
        {observation.property_name for observation in world.observations}
    )
    sensors = sorted({observation.source for observation in world.observations})
    features = sorted({observation.subject for observation in world.observations})
    blocks = [
        _block(
            _iri(base_iri, "property", property_name),
            ("a sosa:Property",),
        )
        for property_name in properties
    ]
    blocks.extend(
        _block(_iri(base_iri, "sensor", sensor), ("a sosa:Sensor",))
        for sensor in sensors
    )
    blocks.extend(
        _block(
            _iri(base_iri, "instance", feature),
            ("a sosa:FeatureOfInterest",),
        )
        for feature in features
    )
    return "\n".join(blocks)


def _observation_graph(world: SpatialWorld, base_iri: str) -> str:
    blocks = [_observation_resources(world, base_iri)]
    blocks.extend(
        _observation_block(observation, index, base_iri)
        for index, observation in enumerate(world.observations, start=1)
    )
    return "\n".join(block for block in blocks if block)


def project_geosparql(
    world: SpatialWorld,
    base_iri: str = DEFAULT_BASE_IRI,
) -> str:
    """Project asserted regions and positions to a GeoSPARQL Turtle graph."""

    _validate_base_iri(base_iri)
    blocks = [f"@prefix geo: <{_GEO}> .\n"]
    blocks.extend(
        _feature_block(base_iri, "region", name, geometry)
        for name, geometry in sorted(world.regions.items())
    )
    blocks.extend(
        _feature_block(base_iri, "instance", name, geometry)
        for name, geometry in sorted(world.positions.items())
    )
    return "\n".join(blocks)


def project_sosa(
    world: SpatialWorld,
    base_iri: str = DEFAULT_BASE_IRI,
) -> str:
    """Project evidence records using SOSA with PULSE-S quality annotations."""

    _validate_base_iri(base_iri)
    prefixes = (
        f"@prefix geo: <{_GEO}> .\n"
        f"@prefix pulse: <{_PULSE}> .\n"
        f"@prefix sosa: <{_SOSA}> .\n"
        f"@prefix xsd: <{_XSD}> .\n"
    )
    graph = _observation_graph(world, base_iri)
    return prefixes if not graph else f"{prefixes}\n{graph}"


def project_data_graph(
    world: SpatialWorld,
    base_iri: str = DEFAULT_BASE_IRI,
) -> str:
    """Project asserted state and observations into one modal RDF data graph."""

    _validate_base_iri(base_iri)
    prefixes = (
        f"@prefix geo: <{_GEO}> .\n"
        f"@prefix pulse: <{_PULSE}> .\n"
        f"@prefix sosa: <{_SOSA}> .\n"
        f"@prefix xsd: <{_XSD}> .\n"
    )
    blocks = [
        _block(f"{_PULSE}Asserted", ("a pulse:Modality",)),
        _block(f"{_PULSE}Observed", ("a pulse:Modality",)),
    ]
    blocks.extend(
        _feature_block(
            base_iri,
            "region",
            name,
            geometry,
            include_modal_annotation=True,
        )
        for name, geometry in sorted(world.regions.items())
    )
    blocks.extend(
        _feature_block(
            base_iri,
            "instance",
            name,
            geometry,
            include_modal_annotation=True,
            include_sosa_type=True,
        )
        for name, geometry in sorted(world.positions.items())
    )
    blocks.extend(
        _block(
            _iri(base_iri, "instance", name),
            (f"pulse:state {_string(state)}",),
        )
        for name, state in sorted(world.states.items())
    )
    observation_graph = _observation_graph(world, base_iri)
    if observation_graph:
        blocks.append(observation_graph)
    return f"{prefixes}\n" + "\n".join(blocks)


def _constraint_query(
    constraint: GeofenceConstraint,
    base_iri: str,
) -> str:
    region_iri = _iri(base_iri, "region", constraint.region)
    function = {
        "inside": "geof:sfWithin",
        "coveredBy": "geof:ehCoveredBy",
    }.get(constraint.predicate)
    if function is None:
        raise ValueError(
            f"Unsupported SHACL spatial predicate: {constraint.predicate!r}"
        )
    state_clause = ""
    if constraint.while_state is not None:
        state_clause = (
            f"  $this pulse:state {_string(constraint.while_state)} .\n"
        )
    return (
        f"PREFIX geo: <{_GEO}>\n"
        f"PREFIX geof: <{_GEOF}>\n"
        f"PREFIX pulse: <{_PULSE}>\n"
        "SELECT $this\n"
        "WHERE {\n"
        "  $this geo:hasGeometry/geo:asWKT ?subjectWkt .\n"
        f"  <{region_iri}> geo:hasGeometry/geo:asWKT ?regionWkt .\n"
        f"{state_clause}"
        f"  FILTER (!{function}(?subjectWkt, ?regionWkt))\n"
        "}"
    )


def project_shacl(
    constraints: Iterable[GeofenceConstraint],
    base_iri: str = DEFAULT_BASE_IRI,
) -> str:
    """Project normative geofences to GeoSPARQL-enabled SHACL-SPARQL."""

    _validate_base_iri(base_iri)
    prefixes = (
        f"@prefix geo: <{_GEO}> .\n"
        f"@prefix pulse: <{_PULSE}> .\n"
        f"@prefix sh: <{_SH}> .\n"
    )
    blocks: list[str] = []
    for constraint in sorted(constraints, key=lambda item: item.name):
        shape_iri = _iri(base_iri, "shape", constraint.name)
        subject_iri = _iri(base_iri, "instance", constraint.subject)
        message = (
            f"PULSE-S constraint {constraint.name} violated: expected "
            f"{constraint.predicate} relation to region {constraint.region}."
        )
        query = _constraint_query(constraint, base_iri)
        blocks.append(
            _block(
                shape_iri,
                (
                    "a sh:NodeShape",
                    f"sh:targetNode <{subject_iri}>",
                    "sh:sparql [\n"
                    "    a sh:SPARQLConstraint ;\n"
                    f"    sh:message {_string(message)} ;\n"
                    f'    sh:select """{query}"""\n'
                    "  ]",
                ),
            )
        )
    return prefixes if not blocks else f"{prefixes}\n" + "\n".join(blocks)


def project_standards(
    world: SpatialWorld,
    constraints: Iterable[GeofenceConstraint] = (),
    base_iri: str = DEFAULT_BASE_IRI,
) -> ProjectionBundle:
    """Create the interoperable data and shapes graphs as one bundle."""

    return ProjectionBundle(
        project_data_graph(world, base_iri),
        project_shacl(constraints, base_iri),
    )


def write_projection_bundle(
    bundle: ProjectionBundle,
    directory: str | Path,
    stem: str = "pulse",
) -> ProjectionPaths:
    """Write UTF-8 Turtle data and shapes graphs to a directory."""

    if not stem or stem in {".", ".."} or any(
        separator in stem for separator in ("/", "\\")
    ):
        raise ValueError(f"Invalid projection file stem: {stem!r}")
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    data_path = target / f"{stem}-data.ttl"
    shapes_path = target / f"{stem}-shapes.ttl"
    data_path.write_text(bundle.data_graph, encoding="utf-8", newline="\n")
    shapes_path.write_text(bundle.shapes_graph, encoding="utf-8", newline="\n")
    return ProjectionPaths(data_path, shapes_path)
