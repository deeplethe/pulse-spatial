"""Complete GeoSPARQL 1.1 ATS inventory and executable probe matrix."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .geosparql_external import DEFAULT_IMAGE, _image_identifier, build_image


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    REPOSITORY_ROOT / "experiments" / "ogc-geosparql-1.1" / "ats-manifest.json"
)

PREFIXES = """
PREFIX ex:   <https://example.org/ogc-probe/>
PREFIX geo:  <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
""".strip()

VALUES = """
VALUES (?g ?h ?inside ?boundary ?line ?overlap) {
  (
    "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON((0 0,4 0,4 4,0 4,0 0))"^^geo:wktLiteral
    "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON((8 8,10 8,10 10,8 10,8 8))"^^geo:wktLiteral
    "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT(1 1)"^^geo:wktLiteral
    "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT(0 2)"^^geo:wktLiteral
    "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> LINESTRING(-1 2,5 2)"^^geo:wktLiteral
    "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON((2 2,6 2,6 6,2 6,2 2))"^^geo:wktLiteral
  )
}
""".strip()

DATA_GRAPH = (
    r"""
@prefix ex:   <https://example.org/ogc-probe/> .
@prefix geo:  <http://www.opengis.net/ont/geosparql#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

geo:Feature rdfs:subClassOf geo:SpatialObject .
ex:SpecialFeature rdfs:subClassOf geo:Feature .
ex:entailed a ex:SpecialFeature .

ex:spatial a geo:SpatialObject ;
  geo:hasSize 1 ; geo:hasMetricSize 1 ;
  geo:hasLength 1 ; geo:hasMetricLength 1 ;
  geo:hasPerimeterLength 1 ; geo:hasMetricPerimeterLength 1 ;
  geo:hasArea 1 ; geo:hasMetricArea 1 ;
  geo:hasVolume 1 ; geo:hasMetricVolume 1 .
ex:spatialCollection a geo:SpatialObjectCollection .
ex:featureCollection a geo:FeatureCollection .

ex:area a geo:Feature ; geo:hasGeometry ex:areaGeometry ;
  geo:hasDefaultGeometry ex:areaGeometry ; geo:hasLength 16 ;
  geo:hasArea 16 ; geo:hasVolume 0 ; geo:hasCentroid ex:insideGeometry ;
  geo:hasBoundingBox ex:areaGeometry ; geo:hasSpatialResolution 0.1 .
ex:inside a geo:Feature ; geo:hasGeometry ex:insideGeometry ; geo:hasDefaultGeometry ex:insideGeometry .
ex:boundary a geo:Feature ; geo:hasGeometry ex:boundaryGeometry ; geo:hasDefaultGeometry ex:boundaryGeometry .
ex:outside a geo:Feature ; geo:hasGeometry ex:outsideGeometry ; geo:hasDefaultGeometry ex:outsideGeometry .
ex:overlap a geo:Feature ; geo:hasGeometry ex:overlapGeometry ; geo:hasDefaultGeometry ex:overlapGeometry .
ex:line a geo:Feature ; geo:hasGeometry ex:lineGeometry ; geo:hasDefaultGeometry ex:lineGeometry .

ex:areaGeometry a geo:Geometry ;
  geo:dimension 2 ; geo:coordinateDimension 2 ; geo:spatialDimension 2 ;
  geo:hasSpatialResolution 0.1 ; geo:hasMetricSpatialResolution 1 ;
  geo:hasSpatialAccuracy 0.1 ; geo:hasMetricSpatialAccuracy 1 ;
  geo:isEmpty false ; geo:isSimple true ;
  geo:hasSerialization "POLYGON((0 0,4 0,4 4,0 4,0 0))"^^geo:wktLiteral ;
  geo:asWKT "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON((0 0,4 0,4 4,0 4,0 0))"^^geo:wktLiteral ;
  geo:asGML "<gml:Polygon xmlns:gml='http://www.opengis.net/gml'><gml:outerBoundaryIs><gml:LinearRing><gml:coordinates>0,0 4,0 4,4 0,4 0,0</gml:coordinates></gml:LinearRing></gml:outerBoundaryIs></gml:Polygon>"^^geo:gmlLiteral ;
  geo:asGeoJSON "{\"type\":\"Polygon\",\"coordinates\":[[[0,0],[4,0],[4,4],[0,4],[0,0]]]}"^^geo:geoJSONLiteral ;
  geo:asKML "<Polygon xmlns='http://www.opengis.net/kml/2.2'><outerBoundaryIs><LinearRing><coordinates>0,0 4,0 4,4 0,4 0,0</coordinates></LinearRing></outerBoundaryIs></Polygon>"^^geo:kmlLiteral ;
  geo:asDGGS ""^^geo:dggsLiteral .
ex:insideGeometry a geo:Geometry ;
  geo:asWKT "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT(1 1)"^^geo:wktLiteral ;
  geo:hasSerialization "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT(1 1)"^^geo:wktLiteral .
ex:boundaryGeometry a geo:Geometry ;
  geo:asWKT "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT(0 2)"^^geo:wktLiteral ;
  geo:hasSerialization "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT(0 2)"^^geo:wktLiteral .
ex:outsideGeometry a geo:Geometry ;
  geo:asWKT "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT(9 9)"^^geo:wktLiteral ;
  geo:hasSerialization "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT(9 9)"^^geo:wktLiteral .
ex:overlapGeometry a geo:Geometry ;
  geo:asWKT "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON((2 2,6 2,6 6,2 6,2 2))"^^geo:wktLiteral ;
  geo:hasSerialization "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON((2 2,6 2,6 6,2 6,2 2))"^^geo:wktLiteral .
ex:lineGeometry a geo:Geometry ;
  geo:asWKT "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> LINESTRING(-1 2,5 2)"^^geo:wktLiteral ;
  geo:hasSerialization "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> LINESTRING(-1 2,5 2)"^^geo:wktLiteral .
ex:geometryCollection a geo:GeometryCollection .

ex:area geo:sfEquals ex:area ; geo:sfDisjoint ex:outside ;
  geo:sfIntersects ex:inside ; geo:sfTouches ex:boundary ;
  geo:sfCrosses ex:line ; geo:sfWithin ex:area ;
  geo:sfContains ex:inside ; geo:sfOverlaps ex:overlap ;
  geo:ehEquals ex:area ; geo:ehDisjoint ex:outside ;
  geo:ehMeet ex:boundary ; geo:ehOverlap ex:overlap ;
  geo:ehCovers ex:inside ; geo:ehCoveredBy ex:area ;
  geo:ehInside ex:area ; geo:ehContains ex:inside ;
  geo:rcc8eq ex:area ; geo:rcc8dc ex:outside ;
  geo:rcc8ec ex:boundary ; geo:rcc8po ex:overlap ;
  geo:rcc8tppi ex:inside ; geo:rcc8tpp ex:area ;
  geo:rcc8ntpp ex:area ; geo:rcc8ntppi ex:inside .
""".strip()
    + "\n"
)


@dataclass(frozen=True, slots=True)
class Probe:
    name: str
    query: str | None = None
    manual_reason: str | None = None


def load_manifest(path: str | Path = MANIFEST_PATH) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    classes = value.get("classes")
    if not isinstance(classes, dict):
        raise ValueError("ATS manifest has no classes object")
    identifiers = [identifier for tests in classes.values() for identifier in tests]
    if len(classes) != 7 or len(identifiers) != 55 or len(set(identifiers)) != 55:
        raise ValueError("Expected seven classes and 55 unique abstract tests")
    return value


def _ask(pattern: str) -> str:
    return f"{PREFIXES}\nASK {{\n{pattern}\n}}\n"


def _expression_probe(name: str, expression: str) -> Probe:
    return Probe(
        name,
        _ask(
            f"  {VALUES}\n"
            f"  BIND(({expression}) AS ?probeValue)\n"
            "  FILTER(BOUND(?probeValue))"
        ),
    )


def _all_triples(subject: str, predicates: Iterable[str]) -> str:
    return "\n".join(
        f"  {subject} {predicate} ?v{index} ."
        for index, predicate in enumerate(predicates)
    )


SF_FUNCTIONS = {
    "sfEquals": "geof:sfEquals(?g, ?g) = true",
    "sfDisjoint": "geof:sfDisjoint(?g, ?h) = true",
    "sfIntersects": "geof:sfIntersects(?g, ?inside) = true",
    "sfTouches": "geof:sfTouches(?g, ?boundary) = true",
    "sfCrosses": "geof:sfCrosses(?line, ?g) = true",
    "sfWithin": "geof:sfWithin(?inside, ?g) = true",
    "sfContains": "geof:sfContains(?g, ?inside) = true",
    "sfOverlaps": "geof:sfOverlaps(?g, ?overlap) = true",
}

EH_FUNCTIONS = {
    "ehEquals": "geof:ehEquals(?g, ?g) = true",
    "ehDisjoint": "geof:ehDisjoint(?g, ?h) = true",
    "ehMeet": "geof:ehMeet(?g, ?boundary) = true",
    "ehOverlap": "geof:ehOverlap(?g, ?overlap) = true",
    "ehCovers": "geof:ehCovers(?g, ?inside) = true",
    "ehCoveredBy": "geof:ehCoveredBy(?inside, ?g) = true",
    "ehInside": "geof:ehInside(?inside, ?g) = true",
    "ehContains": "geof:ehContains(?g, ?inside) = true",
}

RCC8_FUNCTIONS = {
    "rcc8eq": "geof:rcc8eq(?g, ?g) = true",
    "rcc8dc": "geof:rcc8dc(?g, ?h) = true",
    "rcc8ec": "geof:rcc8ec(?g, ?boundary) = true",
    "rcc8po": "geof:rcc8po(?g, ?overlap) = true",
    "rcc8tppi": "geof:rcc8tppi(?g, ?boundary) = true",
    "rcc8tpp": "geof:rcc8tpp(?boundary, ?g) = true",
    "rcc8ntpp": "geof:rcc8ntpp(?inside, ?g) = true",
    "rcc8ntppi": "geof:rcc8ntppi(?g, ?inside) = true",
}

QUERY_FUNCTIONS = {
    "boundary": "STR(geof:boundary(?g)) != ''",
    "boundingCircle": "STR(geof:boundingCircle(?g)) != ''",
    "metricBuffer": "STR(geof:metricBuffer(?inside, 100.0)) != ''",
    "buffer": "STR(geof:buffer(?inside, 100.0, <http://www.opengis.net/def/uom/OGC/1.0/metre>)) != ''",
    "centroid": "STR(geof:centroid(?g)) != ''",
    "convexHull": "STR(geof:convexHull(?overlap)) != ''",
    "concaveHull": "STR(geof:concaveHull(?overlap)) != ''",
    "coordinateDimension": "geof:coordinateDimension(?g) = 2",
    "difference": "STR(geof:difference(?g, ?overlap)) != ''",
    "dimension": "geof:dimension(?g) = 2",
    "metricDistance": "geof:metricDistance(?inside, ?boundary) >= 0",
    "distance": "geof:distance(?inside, ?boundary, <http://www.opengis.net/def/uom/OGC/1.0/metre>) >= 0",
    "envelope": "STR(geof:envelope(?g)) != ''",
    "geometryType": "STR(geof:geometryType(?g)) != ''",
    "intersection": "STR(geof:intersection(?g, ?overlap)) != ''",
    "is3D": "geof:is3D(?g) = false",
    "isEmpty": "geof:isEmpty(?g) = false",
    "isMeasured": "geof:isMeasured(?g) = false",
    "isSimple": "geof:isSimple(?g) = true",
    "spatialDimension": "geof:spatialDimension(?g) = 2",
    "symDifference": "STR(geof:symDifference(?g, ?overlap)) != ''",
    "transform": "STR(geof:transform(?g, <http://www.opengis.net/def/crs/OGC/1.3/CRS84>)) != ''",
    "union": "STR(geof:union(?g, ?overlap)) != ''",
}

AGGREGATES = {
    "aggBoundingBox": "geof:aggBoundingBox(?item)",
    "aggBoundingCircle": "geof:aggBoundingCircle(?item)",
    "aggCentroid": "geof:aggCentroid(?item)",
    "aggConcaveHull": "geof:aggConcaveHull(?item, 0.8)",
    "aggConvexHull": "geof:aggConvexHull(?item)",
    "aggUnion": "geof:aggUnion(?item)",
}


def _aggregate_probe(name: str, expression: str) -> Probe:
    query = f"""{PREFIXES}
ASK {{
  {{
    SELECT ({expression} AS ?aggregateValue)
    WHERE {{
      VALUES ?item {{
        "POINT(0 0)"^^geo:wktLiteral
        "POINT(1 1)"^^geo:wktLiteral
      }}
    }}
  }}
  FILTER(BOUND(?aggregateValue))
}}
"""
    return Probe(name, query)


def probes_for(identifier: str) -> tuple[Probe, ...]:
    direct = {
        "/conf/core/sparql-protocol": _ask("  VALUES ?value { 1 } FILTER(?value = 1)"),
        "/conf/core/spatial-object-class": _ask("  ex:spatial a geo:SpatialObject ."),
        "/conf/core/feature-class": _ask("  ex:area a geo:Feature ."),
        "/conf/core/spatial-object-collection-class": _ask(
            "  ex:spatialCollection a geo:SpatialObjectCollection ."
        ),
        "/conf/core/feature-collection-class": _ask(
            "  ex:featureCollection a geo:FeatureCollection ."
        ),
        "/conf/core/spatial-object-properties": _ask(
            _all_triples(
                "ex:spatial",
                (
                    "geo:hasSize",
                    "geo:hasMetricSize",
                    "geo:hasLength",
                    "geo:hasMetricLength",
                    "geo:hasPerimeterLength",
                    "geo:hasMetricPerimeterLength",
                    "geo:hasArea",
                    "geo:hasMetricArea",
                    "geo:hasVolume",
                    "geo:hasMetricVolume",
                ),
            )
        ),
        "/conf/geometry-extension/geometry-class": _ask(
            "  ex:areaGeometry a geo:Geometry ."
        ),
        "/conf/geometry-extension/geometry-collection-class": _ask(
            "  ex:geometryCollection a geo:GeometryCollection ."
        ),
        "/conf/geometry-extension/feature-properties": _ask(
            _all_triples(
                "ex:area",
                (
                    "geo:hasGeometry",
                    "geo:hasDefaultGeometry",
                    "geo:hasLength",
                    "geo:hasArea",
                    "geo:hasVolume",
                    "geo:hasCentroid",
                    "geo:hasBoundingBox",
                    "geo:hasSpatialResolution",
                ),
            )
        ),
        "/conf/geometry-extension/geometry-properties": _ask(
            _all_triples(
                "ex:areaGeometry",
                (
                    "geo:dimension",
                    "geo:coordinateDimension",
                    "geo:spatialDimension",
                    "geo:hasSpatialResolution",
                    "geo:hasMetricSpatialResolution",
                    "geo:hasSpatialAccuracy",
                    "geo:hasMetricSpatialAccuracy",
                    "geo:isEmpty",
                    "geo:isSimple",
                    "geo:hasSerialization",
                ),
            )
        ),
        "/conf/geometry-extension/wkt-literal": _ask(
            '  BIND("POINT(1 1)"^^geo:wktLiteral AS ?v) FILTER(DATATYPE(?v) = geo:wktLiteral)'
        ),
        "/conf/geometry-extension/wkt-literal-default-srs": _ask(
            f'  {VALUES}\n  BIND("POINT(1 1)"^^geo:wktLiteral AS ?default) FILTER(geof:sfEquals(?default, ?inside))'
        ),
        "/conf/geometry-extension/wkt-axis-order": _ask(
            f'  {VALUES}\n  BIND("<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT(1 1)"^^geo:wktLiteral AS ?explicit) FILTER(geof:sfEquals(?explicit, ?inside))'
        ),
        "/conf/geometry-extension/wkt-literal-empty": _ask(
            '  BIND(""^^geo:wktLiteral AS ?empty) FILTER(geof:isEmpty(?empty))'
        ),
        "/conf/geometry-extension/geometry-as-wkt-literal": _ask(
            "  ex:areaGeometry geo:asWKT ?v . FILTER(DATATYPE(?v) = geo:wktLiteral)"
        ),
        "/conf/geometry-extension/gml-literal": _ask(
            "  ex:areaGeometry geo:asGML ?v . FILTER(DATATYPE(?v) = geo:gmlLiteral)"
        ),
        "/conf/geometry-extension/gml-literal-empty": _ask(
            '  BIND(""^^geo:gmlLiteral AS ?empty) FILTER(geof:isEmpty(?empty))'
        ),
        "/conf/geometry-extension/geometry-as-gml-literal": _ask(
            "  ex:areaGeometry geo:asGML ?v . FILTER(DATATYPE(?v) = geo:gmlLiteral)"
        ),
        "/conf/geometry-extension/geojson-literal": _ask(
            "  ex:areaGeometry geo:asGeoJSON ?v . FILTER(DATATYPE(?v) = geo:geoJSONLiteral)"
        ),
        "/conf/geometry-extension/geojson-literal-srs": _ask(
            "  ex:areaGeometry geo:asGeoJSON ?v . FILTER(!CONTAINS(STR(?v), '\"crs\"'))"
        ),
        "/conf/geometry-extension/geojson-literal-empty": _ask(
            '  BIND(""^^geo:geoJSONLiteral AS ?empty) FILTER(geof:isEmpty(?empty))'
        ),
        "/conf/geometry-extension/geometry-as-geojson-literal": _ask(
            "  ex:areaGeometry geo:asGeoJSON ?v . FILTER(DATATYPE(?v) = geo:geoJSONLiteral)"
        ),
        "/conf/geometry-extension/kml-literal": _ask(
            "  ex:areaGeometry geo:asKML ?v . FILTER(DATATYPE(?v) = geo:kmlLiteral)"
        ),
        "/conf/geometry-extension/kml-literal-srs": _ask(
            "  ex:areaGeometry geo:asKML ?v . FILTER(!CONTAINS(STR(?v), 'srsName'))"
        ),
        "/conf/geometry-extension/kml-literal-empty": _ask(
            '  BIND(""^^geo:kmlLiteral AS ?empty) FILTER(geof:isEmpty(?empty))'
        ),
        "/conf/geometry-extension/geometry-as-kml-literal": _ask(
            "  ex:areaGeometry geo:asKML ?v . FILTER(DATATYPE(?v) = geo:kmlLiteral)"
        ),
        "/conf/geometry-extension-dggs/dggs-literal": _ask(
            '  BIND("cell"^^geo:dggsLiteral AS ?v) FILTER(DATATYPE(?v) = geo:dggsLiteral)'
        ),
        "/conf/geometry-extension-dggs/dggs-literal-empty": _ask(
            '  BIND(""^^geo:dggsLiteral AS ?v) FILTER(DATATYPE(?v) = geo:dggsLiteral)'
        ),
        "/conf/geometry-extension-dggs/geometry-as-dggs-literal": _ask(
            "  ex:areaGeometry geo:asDGGS ?v . FILTER(DATATYPE(?v) = geo:dggsLiteral)"
        ),
        "/conf/rdfs-entailment-extension/bgp-rdfs-ent": _ask(
            "  ex:entailed a geo:SpatialObject ."
        ),
        "/conf/rdfs-entailment-extension/wkt-geometry-types": _ask(
            "  ex:areaGeometry geo:asWKT ?v . FILTER(DATATYPE(?v) = geo:wktLiteral)"
        ),
        "/conf/rdfs-entailment-extension/gml-geometry-types": _ask(
            "  ex:areaGeometry geo:asGML ?v . FILTER(DATATYPE(?v) = geo:gmlLiteral)"
        ),
    }
    if identifier in direct:
        return (Probe(identifier.rsplit("/", 1)[-1], direct[identifier]),)
    if identifier == "/conf/geometry-extension/gml-profile":
        return (
            Probe(
                "documented-gml-profile",
                manual_reason="Implementation documentation must state its supported GML profile.",
            ),
        )
    if identifier == "/conf/geometry-extension/query-functions":
        return tuple(
            _expression_probe(name, expression)
            for name, expression in QUERY_FUNCTIONS.items()
        )
    if identifier == "/conf/geometry-extension/srid-function":
        return (
            _expression_probe(
                "getSRID",
                "geof:getSRID(?g) = <http://www.opengis.net/def/crs/OGC/1.3/CRS84>",
            ),
        )
    if identifier == "/conf/geometry-extension/sa-functions":
        return tuple(
            _aggregate_probe(name, expression)
            for name, expression in AGGREGATES.items()
        )
    serialization_functions = {
        "/conf/geometry-extension/asWKT-function": (
            "asWKT",
            "STR(geof:asWKT(?g)) != ''",
        ),
        "/conf/geometry-extension/asGML-function": (
            "asGML",
            "STR(geof:asGML(?g)) != ''",
        ),
        "/conf/geometry-extension/asGeoJSON-function": (
            "asGeoJSON",
            "STR(geof:asGeoJSON(?g)) != ''",
        ),
        "/conf/geometry-extension/asKML-function": (
            "asKML",
            "STR(geof:asKML(?g)) != ''",
        ),
        "/conf/geometry-extension-dggs/asDGGS-function": (
            "asDGGS",
            "STR(geof:asDGGS(?g)) != ''",
        ),
    }
    if identifier in serialization_functions:
        name, expression = serialization_functions[identifier]
        return (_expression_probe(name, expression),)
    if identifier.startswith("/conf/topology-vocab-extension/"):
        family = identifier.split("/")[-1].split("-")[0]
        predicates = {
            "sf": SF_FUNCTIONS,
            "eh": EH_FUNCTIONS,
            "rcc8": RCC8_FUNCTIONS,
        }[family]
        return tuple(
            Probe(
                name,
                _ask(f"  ex:area ?predicate ?target . FILTER(?predicate = geo:{name})"),
            )
            for name in predicates
        )
    if identifier.startswith("/conf/geometry-topology-extension/"):
        if identifier.endswith("relate-query-function"):
            return (
                _expression_probe(
                    "relate", 'geof:relate(?inside, ?g, "T*F**F***") = true'
                ),
            )
        family = identifier.split("/")[-1].split("-")[0]
        functions = {"sf": SF_FUNCTIONS, "eh": EH_FUNCTIONS, "rcc8": RCC8_FUNCTIONS}[
            family
        ]
        return tuple(
            _expression_probe(name, expression)
            for name, expression in functions.items()
        )
    if identifier.startswith("/conf/query-rewrite-extension/"):
        family = identifier.split("/")[-1].split("-")[0]
        relation = {"sf": "sfWithin", "eh": "ehInside", "rcc8": "rcc8ntpp"}[family]
        return (Probe(relation, _ask(f"  ex:inside geo:{relation} ex:area .")),)
    if identifier.startswith("/conf/geometry-extension-dggs/"):
        return (
            Probe(
                identifier.rsplit("/", 1)[-1],
                _ask(
                    '  BIND("cell"^^geo:dggsLiteral AS ?cell) BIND(geof:getSRID(?cell) AS ?srid) FILTER(BOUND(?srid))'
                ),
            ),
        )
    raise KeyError(f"No probe design for {identifier}")


def build_probe_plan(manifest: dict[str, object]) -> dict[str, tuple[Probe, ...]]:
    classes = manifest["classes"]
    assert isinstance(classes, dict)
    return {
        identifier: probes_for(identifier)
        for identifiers in classes.values()
        for identifier in identifiers
    }


def _run_probe(
    image: str, directory: Path, probe: Probe, index: int
) -> dict[str, object]:
    if probe.manual_reason:
        return {
            "name": probe.name,
            "status": "manual",
            "reason": probe.manual_reason,
        }
    assert probe.query is not None
    query_path = directory / f"probe-{index:04d}.rq"
    query_path.write_text(probe.query, encoding="utf-8", newline="\n")
    query_path.chmod(0o644)
    started = time.perf_counter()
    completed = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--volume",
            f"{directory.resolve()}:/data:ro",
            image,
            "--query",
            "/data/data.ttl",
            f"/data/{query_path.name}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    seconds = time.perf_counter() - started
    if completed.returncode:
        return {
            "name": probe.name,
            "status": "error",
            "seconds": seconds,
            "detail": completed.stderr.strip()[-2000:],
        }
    try:
        value = json.loads(completed.stdout)
        passed = value.get("boolean") is True
    except (json.JSONDecodeError, AttributeError):
        return {
            "name": probe.name,
            "status": "error",
            "seconds": seconds,
            "detail": "Harness returned invalid JSON",
        }
    return {
        "name": probe.name,
        "status": "pass" if passed else "fail",
        "seconds": seconds,
    }


def _aggregate_status(results: Iterable[dict[str, object]]) -> str:
    statuses = {str(result["status"]) for result in results}
    if statuses == {"pass"}:
        return "pass"
    if "error" in statuses:
        return "error"
    if "fail" in statuses:
        return "fail"
    return "manual"


def run_experiment(
    *, image: str = DEFAULT_IMAGE, rebuild: bool = False
) -> dict[str, object]:
    manifest = load_manifest()
    plan = build_probe_plan(manifest)
    build_seconds = build_image(image) if rebuild else None
    classes = manifest["classes"]
    assert isinstance(classes, dict)
    records: list[dict[str, object]] = []
    probe_index = 0
    with tempfile.TemporaryDirectory(prefix="pulse-ogc-ats-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o755)
        data_path = directory / "data.ttl"
        data_path.write_text(DATA_GRAPH, encoding="utf-8", newline="\n")
        data_path.chmod(0o644)
        for class_id, identifiers in classes.items():
            test_records = []
            for identifier in identifiers:
                component_results = []
                for probe in plan[identifier]:
                    probe_index += 1
                    component_results.append(
                        _run_probe(image, directory, probe, probe_index)
                    )
                test_records.append(
                    {
                        "identifier": identifier,
                        "status": _aggregate_status(component_results),
                        "components": component_results,
                    }
                )
            records.append(
                {
                    "identifier": class_id,
                    "status": _aggregate_status(test_records),
                    "claimable": all(test["status"] == "pass" for test in test_records),
                    "tests": test_records,
                }
            )
    abstract_tests = [test for record in records for test in record["tests"]]
    component_results = [
        component for test in abstract_tests for component in test["components"]
    ]
    counts = {
        status: sum(result["status"] == status for result in component_results)
        for status in ("pass", "fail", "error", "manual")
    }
    return {
        "experiment": "ogc-geosparql-1.1-complete-ats-coverage-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "claimBoundary": (
            "Complete coverage of all 55 normative GeoSPARQL 1.1 abstract-test "
            "identifiers with researcher-authored executable refinements. "
            "A class is claimable only when all its abstract tests pass. This "
            "is not an OGC-issued certificate, and manual requirements remain "
            "manual rather than being silently counted as passes."
        ),
        "normativeInventory": {
            "document": manifest["document"],
            "source": manifest["normativeSource"],
            "publishedTag": manifest["publishedTag"],
            "publishedTagCommit": manifest["publishedTagCommit"],
            "conformanceClasses": len(classes),
            "abstractTests": len(plan),
            "coverageComplete": len(plan) == 55,
        },
        "summary": {
            "componentProbes": len(component_results),
            "componentStatus": counts,
            "claimableClasses": [
                record["identifier"] for record in records if record["claimable"]
            ],
        },
        "classes": records,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "externalSystem": "Apache Jena GeoSPARQL 6.1.0",
            "containerImage": image,
            "containerImageId": _image_identifier(image),
            "imageBuildSeconds": build_seconds,
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    inventory = result["normativeInventory"]
    summary = result["summary"]
    classes = result["classes"]
    assert isinstance(inventory, dict)
    assert isinstance(summary, dict)
    assert isinstance(classes, list)
    rows = [
        "# OGC GeoSPARQL 1.1 complete ATS coverage",
        "",
        f"- Conformance classes: {inventory['conformanceClasses']}",
        f"- Normative abstract tests: {inventory['abstractTests']}",
        f"- Executable/manual component probes: {summary['componentProbes']}",
        f"- Inventory coverage complete: **{inventory['coverageComplete']}**",
        f"- Claimable classes: {', '.join(summary['claimableClasses']) or 'none'}",
        "",
        "| Conformance class | Status | Claimable |",
        "|---|---:|---:|",
    ]
    rows.extend(
        f"| `{record['identifier']}` | {record['status']} | {record['claimable']} |"
        for record in classes
    )
    rows.extend(("", "## Claim boundary", "", str(result["claimBoundary"]), ""))
    return "\n".join(rows)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-ogc-conformance",
        description="Run complete GeoSPARQL 1.1 ATS coverage probes.",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-complete-coverage", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_experiment(image=arguments.image, rebuild=arguments.rebuild)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    if arguments.require_complete_coverage:
        inventory = result["normativeInventory"]
        assert isinstance(inventory, dict)
        if not inventory["coverageComplete"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
