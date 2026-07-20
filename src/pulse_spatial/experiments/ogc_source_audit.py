"""Audit the pinned OGC GeoSPARQL 1.1 auxiliary RDF registers.

Annex A of OGC 22-047r1 remains the normative Abstract Test Suite. The local
manifest is a researcher transcription of that inventory, not an independent
parser for the specification HTML. The RDF
requirements register and SPARQL service-description graph are useful official
corroborating sources, but they are not an executable ETS and are not identical
encodings of the Annex A inventory.  This module makes that distinction
reproducible instead of silently treating the three inventories as equivalent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from rdflib import Graph, Namespace, RDF

from .ogc_conformance import MANIFEST_PATH, load_manifest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
UPSTREAM_ROOT = REPOSITORY_ROOT / "external" / "ogc-geosparql-1.1"
REQUIREMENTS_PATH = UPSTREAM_ROOT / "reqs.ttl"
SERVICE_DESCRIPTION_PATH = (
    UPSTREAM_ROOT / "servicedescription_conformanceclasses.ttl"
)

UPSTREAM_REPOSITORY = "https://github.com/opengeospatial/ogc-geosparql"
UPSTREAM_TAG = "1.1.0-ghpages"
UPSTREAM_COMMIT = "cd53678be2e9775066d63791c84c3fa010fc29ff"
EXPECTED_HASHES = {
    "reqs.ttl": "4b76c1318db09be0077fa9134203c24078f3d3afee055ccefd1e73daf46036c1",
    "servicedescription_conformanceclasses.ttl": (
        "416d27f614374630df5ae3c3429340fb790f94dc71d1247d332d860c908d4803"
    ),
}

SPEC = Namespace("http://www.opengis.net/def/spec-element/")
SD = Namespace("http://www.w3.org/ns/sparql-service-description#")

LOCAL_NAME_ALIASES = {
    "asWKT-function": "geometry-as-wkt-function",
    "asGML-function": "geometry-as-gml-function",
    "asGeoJSON-function": "geometry-as-geojson-function",
    "asKML-function": "geometry-as-kml-function",
    "asDGGS-function": "geometry-as-dggs-function",
}


def _sha256(path: Path) -> str:
    # Git stores and distributes these text assets with LF endings. Normalize
    # Windows checkouts before hashing so the pinned digest is portable.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _version(uri: str) -> str:
    if "/geosparql/1.0/" in uri:
        return "1.0"
    if "/geosparql/1.1/" in uri:
        return "1.1"
    return "other"


def _allocation_local_name(identifier: str) -> str:
    local_name = identifier.rsplit("/", 1)[-1]
    if identifier.startswith("/conf/geometry-extension-dggs/") and local_name in {
        "query-functions",
        "query-functions-non-sf",
    }:
        local_name += "-dggs"
    return LOCAL_NAME_ALIASES.get(local_name, local_name)


def _parse(path: Path) -> Graph:
    return Graph().parse(path, format="turtle")


def run_source_audit(
    manifest_path: str | Path = MANIFEST_PATH,
    requirements_path: str | Path = REQUIREMENTS_PATH,
    service_description_path: str | Path = SERVICE_DESCRIPTION_PATH,
) -> dict[str, object]:
    manifest = load_manifest(manifest_path)
    classes = manifest["classes"]
    assert isinstance(classes, dict)
    allocations = [identifier for tests in classes.values() for identifier in tests]

    requirements_file = Path(requirements_path)
    service_file = Path(service_description_path)
    hashes = {
        requirements_file.name: _sha256(requirements_file),
        service_file.name: _sha256(service_file),
    }

    requirements = _parse(requirements_file)
    service_description = _parse(service_file)
    conformance_tests = {
        str(subject)
        for subject in requirements.subjects(RDF.type, SPEC.ConformanceTest)
    }
    service_features = {
        str(feature)
        for feature in service_description.objects(None, SD.feature)
    }

    by_local_name: dict[str, set[str]] = defaultdict(set)
    for uri in conformance_tests:
        by_local_name[uri.rsplit("/", 1)[-1]].add(uri)

    crosswalk = []
    matched_register_tests: set[str] = set()
    for identifier in allocations:
        local_name = _allocation_local_name(identifier)
        candidates = sorted(by_local_name.get(local_name, ()))
        matched_register_tests.update(candidates)
        crosswalk.append(
            {
                "annexIdentifier": identifier,
                "registerLocalName": local_name,
                "candidateRegisterTests": candidates,
                "status": (
                    "unmatched"
                    if not candidates
                    else "ambiguous-version"
                    if len(candidates) > 1
                    else "corroborated"
                ),
            }
        )

    feature_not_typed = sorted(service_features - conformance_tests)
    typed_not_featured = sorted(conformance_tests - service_features)
    register_not_allocated = sorted(conformance_tests - matched_register_tests)
    statuses = Counter(item["status"] for item in crosswalk)
    test_versions = Counter(_version(uri) for uri in conformance_tests)
    feature_versions = Counter(_version(uri) for uri in service_features)

    checks = {
        "pinnedFileHashesMatch": hashes == EXPECTED_HASHES,
        "manifestHasSevenClassesAnd55UniqueAllocations": (
            len(classes) == 7
            and len(allocations) == 55
            and len(set(allocations)) == 55
        ),
        "allAnnexAllocationsHaveRegisterCandidates": statuses["unmatched"] == 0,
        "registerShapeMatchesPinnedSource": (
            len(conformance_tests) == 58
            and test_versions == Counter({"1.0": 30, "1.1": 28})
            and statuses["ambiguous-version"] == 4
            and len(register_not_allocated) == 1
        ),
        "serviceDescriptionShapeMatchesPinnedSource": (
            len(service_features) == 52
            and feature_versions == Counter({"1.0": 23, "1.1": 29})
            and len(feature_not_typed) == 2
            and len(typed_not_featured) == 8
        ),
    }
    audit_passed = all(checks.values())

    return {
        "experiment": "ogc-geosparql-1.1-official-source-audit-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "normativeAuthority": {
            "document": "OGC 22-047r1",
            "annex": "Annex A — Abstract Test Suite",
            "url": str(manifest["normativeSource"]),
            "statement": (
                "Annex A is normative. The two pinned RDF files are official "
                "auxiliary registers, not an executable OGC ETS."
            ),
            "inventoryEncoding": (
                "Researcher-authored manifest transcribed from Annex A; the "
                "audit does not independently parse the specification HTML."
            ),
        },
        "upstream": {
            "repository": UPSTREAM_REPOSITORY,
            "tag": UPSTREAM_TAG,
            "commit": UPSTREAM_COMMIT,
            "files": {
                name: {"sha256": value, "expectedSha256": EXPECTED_HASHES[name]}
                for name, value in hashes.items()
            },
        },
        "inventories": {
            "annexA": {
                "source": "researcher-authored Annex A manifest transcription",
                "classCount": len(classes),
                "testAllocations": len(allocations),
                "uniqueIdentifiers": len(set(allocations)),
            },
            "requirementsRegister": {
                "conformanceTestResources": len(conformance_tests),
                "byVersion": dict(sorted(test_versions.items())),
            },
            "serviceDescription": {
                "features": len(service_features),
                "byVersion": dict(sorted(feature_versions.items())),
            },
        },
        "crosswalkSummary": {
            "annexAllocationsCorroborated": len(allocations) - statuses["unmatched"],
            "unambiguous": statuses["corroborated"],
            "ambiguousAcrossVersionedUris": statuses["ambiguous-version"],
            "unmatched": statuses["unmatched"],
        },
        "sourceDivergences": {
            "registerTestsNotSelectedByAnnexNameCrosswalk": register_not_allocated,
            "serviceFeaturesNotTypedAsConformanceTests": feature_not_typed,
            "conformanceTestsNotListedAsServiceFeatures": typed_not_featured,
        },
        "checks": checks,
        "auditPassed": audit_passed,
        "claimBoundary": (
            "Passing this audit establishes integrity of the two pinned official "
            "RDF files and explicit accounting against a researcher-authored "
            "Annex A manifest transcription. It does not independently parse "
            "Annex A, execute an OGC ETS, or establish GeoSPARQL conformance."
        ),
        "crosswalk": crosswalk,
    }


def render_markdown(result: dict[str, object]) -> str:
    inventories = result["inventories"]
    crosswalk = result["crosswalkSummary"]
    divergences = result["sourceDivergences"]
    checks = result["checks"]
    assert isinstance(inventories, dict)
    assert isinstance(crosswalk, dict)
    assert isinstance(divergences, dict)
    assert isinstance(checks, dict)
    annex = inventories["annexA"]
    register = inventories["requirementsRegister"]
    service = inventories["serviceDescription"]
    assert isinstance(annex, dict)
    assert isinstance(register, dict)
    assert isinstance(service, dict)
    lines = [
        "# OGC GeoSPARQL 1.1 official-source audit",
        "",
        "## Audited inventory counts",
        "",
        f"- Researcher-transcribed Annex A manifest: {annex['classCount']} classes, "
        f"{annex['testAllocations']} test allocations",
        f"- Official requirements register: "
        f"{register['conformanceTestResources']} `spec:ConformanceTest` resources",
        f"- Official service description: {service['features']} `sd:feature` resources",
        f"- Annex allocations corroborated by local-name crosswalk: "
        f"{crosswalk['annexAllocationsCorroborated']}/{annex['testAllocations']}",
        f"- Version-ambiguous inherited names: "
        f"{crosswalk['ambiguousAcrossVersionedUris']}",
        "",
        "## Cross-source divergences retained by the audit",
        "",
    ]
    for name, values in divergences.items():
        assert isinstance(values, list)
        lines.append(f"- {name}: {len(values)}")
        lines.extend(f"  - `{value}`" for value in values)
    lines.extend(("", "## Integrity checks", ""))
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} — {name}"
        for name, passed in checks.items()
    )
    lines.extend(
        (
            "",
            f"Overall audit: **{'PASS' if result['auditPassed'] else 'FAIL'}**",
            "",
            "## Claim boundary",
            "",
            str(result["claimBoundary"]),
            "",
        )
    )
    return "\n".join(lines)


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-ogc-source-audit",
        description="Audit pinned official GeoSPARQL 1.1 RDF source registers.",
    )
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--requirements", default=str(REQUIREMENTS_PATH))
    parser.add_argument("--service-description", default=str(SERVICE_DESCRIPTION_PATH))
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-audit-pass", action="store_true")
    arguments = parser.parse_args()
    result = run_source_audit(
        arguments.manifest,
        arguments.requirements,
        arguments.service_description,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    if arguments.require_audit_pass and not result["auditPassed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
