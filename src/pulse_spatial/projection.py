"""Small deterministic GeoSPARQL Turtle projection for asserted spatial state."""

from __future__ import annotations

from urllib.parse import quote

from .geometry import Geometry, to_geosparql_wkt
from .model import SpatialWorld


def _iri(base_iri: str, kind: str, name: str) -> str:
    return f"{base_iri.rstrip('/')}/{kind}/{quote(name, safe='')}"


def _feature_block(base_iri: str, kind: str, name: str, geometry: Geometry) -> str:
    feature = _iri(base_iri, kind, name)
    geometry_iri = f"{feature}/geometry"
    literal = to_geosparql_wkt(geometry).replace('"', '\\"')
    return (
        f"<{feature}> a geo:Feature ;\n"
        f"  geo:hasGeometry <{geometry_iri}> .\n"
        f"<{geometry_iri}> a geo:Geometry ;\n"
        f'  geo:asWKT "{literal}"^^geo:wktLiteral .\n'
    )


def project_geosparql(
    world: SpatialWorld,
    base_iri: str = "https://w3id.org/pulse-spatial/resource",
) -> str:
    blocks = [
        "@prefix geo: <http://www.opengis.net/ont/geosparql#> .\n"
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
    ]
    blocks.extend(
        _feature_block(base_iri, "region", name, geometry)
        for name, geometry in sorted(world.regions.items())
    )
    blocks.extend(
        _feature_block(base_iri, "instance", name, geometry)
        for name, geometry in sorted(world.positions.items())
    )
    return "\n".join(blocks)
