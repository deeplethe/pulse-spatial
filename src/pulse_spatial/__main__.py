"""Command-line inspection and scenario execution for PULSE-S models."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from enum import Enum

from .compiler import PulseModelError, load_pulse
from .parser import PulseSyntaxError
from .projection import project_standards, write_projection_bundle


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def main() -> None:
    argument_parser = argparse.ArgumentParser(
        prog="pulse-spatial",
        description="Compile a PULSE-S model and optionally execute one scenario.",
    )
    argument_parser.add_argument("source", help="path to a .pulse model")
    argument_parser.add_argument("--scenario", help="scenario name to execute")
    argument_parser.add_argument(
        "--emit-projections",
        metavar="DIRECTORY",
        help="write standards-oriented Turtle data and SHACL shapes graphs",
    )
    arguments = argument_parser.parse_args()

    try:
        model = load_pulse(arguments.source)
        output: dict[str, object] = {
            "model": model.document.name,
            "version": model.document.version,
            "regions": sorted(model.world.regions),
            "instances": sorted(model.instance_entities),
            "observations": len(model.world.observations),
            "constraintViolations": _json_value(model.validate()),
        }
        if arguments.scenario:
            report = model.run_scenario(arguments.scenario)
            output["scenario"] = {
                "name": report.name,
                "horizonSeconds": report.horizon_seconds,
                "events": _json_value(report.result.events),
                "answers": _json_value(report.answers),
            }
        if arguments.emit_projections:
            paths = write_projection_bundle(
                project_standards(model.world, model.constraints),
                arguments.emit_projections,
                model.document.name,
            )
            output["projections"] = {
                "dataGraph": str(paths.data_graph.resolve()),
                "shapesGraph": str(paths.shapes_graph.resolve()),
            }
    except (OSError, PulseSyntaxError, PulseModelError) as error:
        argument_parser.error(str(error))
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
