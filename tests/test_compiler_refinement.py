import json
import unittest
from pathlib import Path

from pulse_spatial import compile_pulse, load_pulse
from pulse_spatial.canonical_ir import canonical_ir, canonical_ir_text


ROOT = Path(__file__).resolve().parents[1]
PAPER_EXAMPLE = ROOT / "examples" / "paper_cold_chain_st.pulse"
LEAN_FIXTURE = ROOT / "formal" / "lean" / "paper-cold-chain-ir.json"


class CompilerRefinementTests(unittest.TestCase):
    def test_python_compiler_matches_lean_exported_core_ir(self) -> None:
        model = load_pulse(PAPER_EXAMPLE)
        expected = LEAN_FIXTURE.read_text(encoding="utf-8")

        self.assertEqual(canonical_ir_text(model), expected)

    def test_canonical_ir_preserves_guard_deadline_and_horizon(self) -> None:
        value = canonical_ir(load_pulse(PAPER_EXAMPLE))
        symbols = value["symbols"]
        rule = value["durationRules"][0]
        actions = value["scenarios"][0]["actions"]

        self.assertEqual(symbols[rule["fromState"]], "Safe")
        self.assertEqual(symbols[rule["toState"]], "AtRisk")
        self.assertEqual(rule["durationSeconds"], 600)
        self.assertEqual(value["immediateRules"], [])
        self.assertEqual(actions[-1], {"kind": "advance", "time": 1200})
        json.dumps(value)

    def test_grounded_rule_ids_follow_declaration_order_under_alpha_renaming(
        self,
    ) -> None:
        def source(first: str, second: str) -> str:
            return f"""
model MultiAsset version "0.1"
crs C = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
region Z crs C = polygon [[0,0], [10,0], [10,10], [0,10], [0,0]]
entity Shipment {{
  property position: Point crs C
  state condition oneof [Safe, AtRisk]
}}
instance {first}: Shipment {{ position = point(5,5) condition = Safe }}
instance {second}: Shipment {{ position = point(5,5) condition = Safe }}
process Departure(s: Shipment) {{
  when leaves(s.position,Z) for 1 min
  changes s.condition: Safe -> AtRisk
}}
"""

        for names in (("zeta", "alpha"), ("aardvark", "omega")):
            value = canonical_ir(compile_pulse(source(*names)))
            self.assertEqual(
                [rule["name"] for rule in value["durationRules"]],
                [0, 1],
            )
            self.assertEqual(
                value["symbols"][:2],
                [f"Departure@{names[0]}", f"Departure@{names[1]}"],
            )


if __name__ == "__main__":
    unittest.main()
