"""External Apache Jena GeoSPARQL agreement experiment."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from ..geometry import Point, Polygon, covered_by, within
from ..model import SpatialWorld
from ..projection import project_geosparql
from .topology_corpus import CASES


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HARNESS_DIRECTORY = REPOSITORY_ROOT / "external" / "jena-geosparql"
DEFAULT_IMAGE = "pulse-jena-geosparql:6.1.0"
BASE_IRI = "https://w3id.org/pulse-spatial-benchmark"


def topology_world() -> SpatialWorld:
    """Build one CRS84 graph whose full cross product is externally queried."""

    world = SpatialWorld()
    for case in CASES:
        if case.crs != "http://www.opengis.net/def/crs/OGC/1.3/CRS84":
            continue
        world.regions[case.name] = Polygon.from_xy(case.shell, case.crs)
        world.positions[case.name] = Point(*case.point, case.crs)
    return world


def _local_name(iri: str) -> str:
    path = urlsplit(iri).path.rstrip("/")
    if not path:
        raise ValueError(f"Result IRI has no path component: {iri!r}")
    return unquote(path.rsplit("/", 1)[-1])


def parse_results(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, bool]]:
    bindings = payload.get("results", {}).get("bindings")
    if not isinstance(bindings, list):
        raise ValueError("Jena response has no SPARQL result bindings")
    parsed: dict[tuple[str, str], dict[str, bool]] = {}
    for binding in bindings:
        try:
            subject = _local_name(binding["subject"]["value"])
            region = _local_name(binding["region"]["value"])
            inside = binding["inside"]["value"].lower() == "true"
            covered = binding["coveredBy"]["value"].lower() == "true"
        except (KeyError, AttributeError, TypeError) as error:
            raise ValueError(f"Malformed Jena result binding: {binding!r}") from error
        key = (subject, region)
        if key in parsed:
            raise ValueError(f"Duplicate Jena result pair: {key!r}")
        parsed[key] = {"inside": inside, "coveredBy": covered}
    return parsed


def expected_results(world: SpatialWorld) -> dict[tuple[str, str], dict[str, bool]]:
    return {
        (subject, region): {
            "inside": within(point, polygon),
            "coveredBy": covered_by(point, polygon),
        }
        for subject, point in sorted(world.positions.items())
        for region, polygon in sorted(world.regions.items())
    }


def compare_results(
    expected: dict[tuple[str, str], dict[str, bool]],
    actual: dict[tuple[str, str], dict[str, bool]],
) -> list[dict[str, object]]:
    mismatches: list[dict[str, object]] = []
    for key in sorted(expected.keys() | actual.keys()):
        expected_value = expected.get(key)
        actual_value = actual.get(key)
        if expected_value != actual_value:
            mismatches.append(
                {
                    "subject": key[0],
                    "region": key[1],
                    "expected": expected_value,
                    "actual": actual_value,
                }
            )
    return mismatches


def build_image(image: str = DEFAULT_IMAGE) -> float:
    started = time.perf_counter()
    subprocess.run(
        [
            "docker",
            "build",
            "--quiet",
            "--tag",
            image,
            str(HARNESS_DIRECTORY),
        ],
        cwd=REPOSITORY_ROOT,
        check=True,
    )
    return time.perf_counter() - started


def _image_identifier(image: str) -> str:
    completed = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _timing_from_stderr(stderr: str) -> dict[str, object]:
    prefix = "PULSE_JENA_TIMING "
    for line in stderr.splitlines():
        if line.startswith(prefix):
            parsed = json.loads(line[len(prefix) :])
            if not isinstance(parsed, dict):
                break
            return parsed
    raise ValueError(f"Jena harness emitted no timing record: {stderr!r}")


def run_experiment(
    *, image: str = DEFAULT_IMAGE, rebuild: bool = False
) -> dict[str, object]:
    build_seconds = build_image(image) if rebuild else None
    world = topology_world()

    projection_started = time.perf_counter()
    graph = project_geosparql(world, BASE_IRI)
    projection_seconds = time.perf_counter() - projection_started

    with tempfile.TemporaryDirectory(prefix="pulse-jena-") as directory:
        graph_path = Path(directory) / "topology.ttl"
        graph_path.write_text(graph, encoding="utf-8", newline="\n")
        # TemporaryDirectory is mode 0700 on Linux.  The deliberately
        # unprivileged Jena container therefore cannot traverse a bind-mounted
        # directory unless we grant read/traverse access explicitly.
        graph_path.parent.chmod(0o755)
        graph_path.chmod(0o644)
        container_started = time.perf_counter()
        completed = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--volume",
                f"{graph_path.parent.resolve()}:/data:ro",
                image,
                "/data/topology.ttl",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        container_seconds = time.perf_counter() - container_started
        if completed.returncode:
            raise RuntimeError(
                "Apache Jena container failed with exit code "
                f"{completed.returncode}: {completed.stderr.strip()}"
            )
        actual = parse_results(json.loads(completed.stdout))
        jena_timing = _timing_from_stderr(completed.stderr)

    expected = expected_results(world)
    mismatches = compare_results(expected, actual)
    boundary_cases = {
        case.name
        for case in CASES
        if case.crs == "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
        and "boundary" in case.feature
    }
    boundary_pairs = [
        key for key in expected if key[0] in boundary_cases and key[0] == key[1]
    ]
    boundary_mismatches = [
        item
        for item in mismatches
        if item["subject"] == item["region"]
        and item["subject"] in boundary_cases
    ]
    return {
        "experiment": "apache-jena-geosparql-external-agreement-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "claimBoundary": (
            "Agreement with unmodified Apache Jena GeoSPARQL 6.1.0 for the "
            "checked-in CRS84 Point/Polygon graph using sfWithin and "
            "sfIntersects. This is not a complete GeoSPARQL conformance test, "
            "continuous-trajectory comparison, or like-for-like performance "
            "contest between a native event runtime and a triplestore."
        ),
        "summary": {
            "points": len(world.positions),
            "regions": len(world.regions),
            "pairs": len(expected),
            "rows": len(actual),
            "boundaryPairs": len(boundary_pairs),
            "mismatches": len(mismatches),
            "boundaryMismatches": len(boundary_mismatches),
            "allChecksPass": not mismatches,
        },
        "timingSeconds": {
            "imageBuild": build_seconds,
            "pulseProjection": projection_seconds,
            "containerProcess": container_seconds,
            "jenaInitialization": jena_timing["initializationSeconds"],
            "jenaRdfLoad": jena_timing["loadSeconds"],
            "jenaQueryMaterialization": jena_timing["querySeconds"],
        },
        "mismatches": mismatches,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "externalSystem": "Apache Jena GeoSPARQL 6.1.0",
            "containerImage": image,
            "containerImageId": _image_identifier(image),
        },
    }


def render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    timing = result["timingSeconds"]
    environment = result["environment"]
    assert isinstance(summary, dict)
    assert isinstance(timing, dict)
    assert isinstance(environment, dict)
    return "\n".join(
        (
            "# Apache Jena GeoSPARQL external agreement",
            "",
            "## Summary",
            "",
            f"- External system: {environment['externalSystem']}",
            f"- Points: {summary['points']}",
            f"- Regions: {summary['regions']}",
            f"- Cross-product pairs: {summary['pairs']}",
            f"- Returned rows: {summary['rows']}",
            f"- Boundary-focused intended pairs: {summary['boundaryPairs']}",
            f"- Mismatches: **{summary['mismatches']}**",
            f"- All checks pass: **{summary['allChecksPass']}**",
            "",
            "## Timing (seconds)",
            "",
            f"- PULSE projection: {timing['pulseProjection']:.6f}",
            f"- Container process: {timing['containerProcess']:.6f}",
            f"- Jena initialization: {timing['jenaInitialization']:.6f}",
            f"- Jena RDF load: {timing['jenaRdfLoad']:.6f}",
            f"- Jena query materialization: {timing['jenaQueryMaterialization']:.6f}",
            "",
            "## Claim boundary",
            "",
            str(result["claimBoundary"]),
            "",
        )
    )


def _write(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pulse-spatial-geosparql-external",
        description="Compare PULSE predicates with Apache Jena GeoSPARQL.",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--output-json")
    parser.add_argument("--output-markdown")
    parser.add_argument("--require-parity", action="store_true")
    arguments = parser.parse_args()
    try:
        result = run_experiment(image=arguments.image, rebuild=arguments.rebuild)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_json:
        _write(arguments.output_json, rendered)
    if arguments.output_markdown:
        _write(arguments.output_markdown, render_markdown(result))
    print(rendered, end="")
    if arguments.require_parity and not result["summary"]["allChecksPass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
