"""Canonical compiler IR shared with the Lean-checked paper subset."""

from __future__ import annotations

import json
import math
from pathlib import Path

from .compiler import CompiledModel, PulseModelError


SCHEMA_VERSION = 1
MICRODEGREES = 1_000_000


def _exact_integer(value: float, label: str) -> int:
    rounded = round(value)
    if not math.isclose(value, rounded, rel_tol=0.0, abs_tol=1e-9):
        raise PulseModelError(
            f"canonical compiler IR requires integral {label}; got {value!r}"
        )
    return int(rounded)


def _microdegrees(value: float, label: str) -> int:
    return _exact_integer(value * MICRODEGREES, f"microdegree {label}")


def _symbol_table(model: CompiledModel) -> tuple[tuple[str, ...], dict[str, int]]:
    names: set[str] = set()
    for rule in model.rules:
        names.update(
            (
                rule.name,
                rule.subject,
                rule.region,
                rule.from_state,
                rule.to_state,
            )
        )
    for name, scenario in model.scenarios.items():
        names.add(name)
        for subject, position in scenario.moves:
            names.update((subject, position.crs))
    symbols = tuple(sorted(names))
    return symbols, {name: index for index, name in enumerate(symbols)}


def canonical_ir(model: CompiledModel) -> dict[str, object]:
    """Lower the verified duration/scenario subset to deterministic Core IR.

    The IR intentionally covers the constructs connected to ``Compiler.lean``:
    resolved duration-qualified geofence rules and Point-valued scenario
    assumptions with an optional finite horizon. Immediate and duration rules
    are kept in distinct declaration-ordered lists.
    """

    symbols, symbol_ids = _symbol_table(model)
    duration_rules: list[dict[str, object]] = []
    immediate_rules: list[dict[str, object]] = []
    for rule in model.rules:
        if rule.minimum_duration_seconds is None:
            immediate_rules.append(
                {
                    "name": symbol_ids[rule.name],
                    "trigger": rule.kind.value,
                    "subject": symbol_ids[rule.subject],
                    "region": symbol_ids[rule.region],
                    "fromState": symbol_ids[rule.from_state],
                    "toState": symbol_ids[rule.to_state],
                }
            )
        else:
            duration_rules.append(
                {
                    "name": symbol_ids[rule.name],
                    "trigger": rule.kind.value,
                    "subject": symbol_ids[rule.subject],
                    "region": symbol_ids[rule.region],
                    "fromState": symbol_ids[rule.from_state],
                    "toState": symbol_ids[rule.to_state],
                    "durationSeconds": _exact_integer(
                        rule.minimum_duration_seconds,
                        f"duration for {rule.name}",
                    ),
                }
            )

    scenarios: list[dict[str, object]] = []
    for name, scenario in model.scenarios.items():
        actions: list[dict[str, object]] = []
        for subject, position in scenario.moves:
            actions.append(
                {
                    "kind": "move",
                    "subject": symbol_ids[subject],
                    "position": {
                        "xMicrodegrees": _microdegrees(
                            position.x, f"x coordinate for {subject}"
                        ),
                        "yMicrodegrees": _microdegrees(
                            position.y, f"y coordinate for {subject}"
                        ),
                        "crs": symbol_ids[position.crs],
                    },
                    "time": 0,
                }
            )
        run_for = scenario.declaration.run_for
        if run_for is not None:
            unit_seconds = {"s": 1, "min": 60, "h": 3600}
            try:
                multiplier = unit_seconds[run_for.unit]
            except KeyError as error:
                raise PulseModelError(
                    f"unsupported canonical duration unit {run_for.unit!r}"
                ) from error
            actions.append(
                {
                    "kind": "advance",
                    "time": _exact_integer(
                        run_for.value * multiplier,
                        f"scenario horizon for {name}",
                    ),
                }
            )
        scenarios.append({"name": symbol_ids[name], "actions": actions})

    return {
        "schemaVersion": SCHEMA_VERSION,
        "symbols": list(symbols),
        "durationRules": duration_rules,
        "immediateRules": immediate_rules,
        "scenarios": scenarios,
    }


def canonical_ir_text(model: CompiledModel) -> str:
    """Serialize canonical IR exactly as the Lean exporter does."""

    return json.dumps(
        canonical_ir(model),
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "\n"


def write_canonical_ir(model: CompiledModel, path: str | Path) -> Path:
    """Write an LF-terminated canonical IR fixture."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_ir_text(model), encoding="utf-8", newline="\n")
    return output
