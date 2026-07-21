# Executable composition comparison

This experiment implements one frozen cold-chain task through three paths:

1. one typed PULSE model, runner inputs, and the PULSE temporal runtime;
2. GeoSPARQL + SOSA + OWL-Time RDF, SHACL validation, a GeoSPARQL function
   adapter, and an explicit duration workflow;
3. OGC MF-JSON Prism with `MovingPoint`/`Step`, a separate policy document,
   a geometry engine, and the same duration-workflow semantics.

The task contains a brief geofence departure that must be cancelled, followed
by a departure that lasts at least ten minutes and changes `Safe` to `AtRisk`.
All paths use boundary-inclusive `coveredBy`, sample-and-hold positions, and
timer-before-move ordering at equal timestamps.

## Why MF-JSON Prism rather than Trajectory

MF-JSON Trajectory represents linear trajectories. That interpolation would
place boundary crossings between the recorded samples and would not match the
frozen PULSE sample-and-hold policy. MF-JSON Prism explicitly supports `Step`
interpolation, so the checked-in moving-feature document uses Prism. The local
validator checks the relevant structural subset; it is not an OGC conformance
suite.

## Standard roles

- GeoSPARQL represents/query geometries but does not directly supply temporal
  operations.
- SOSA represents the observations.
- OWL-Time represents instants and the ten-minute duration.
- SHACL validates RDF structure; it does not perform the state transition.
- MF-JSON Prism exchanges the step-interpolated movement.
- Both composed paths therefore require explicit workflow code for timer
  cancellation and the `Safe -> AtRisk` transition.

Authoritative references:

- <https://docs.ogc.org/is/22-047r1/22-047r1.html>
- <https://www.w3.org/TR/shacl/>
- <https://www.w3.org/TR/owl-time/>
- <https://docs.ogc.org/is/19-045r3/19-045r3.html>

## Recorded result

All three paths produced the frozen expected trace:

- `leaves` at 08:05, cancelled by `enters` at 08:12;
- `leaves` at 08:20;
- sustained departure effective at 08:30 and emitted at 08:31;
- final state `AtRisk`.

| Path | Input files | Substantive lines | Execution components | Median |
|---|---:|---:|---:|---:|
| PULSE | 1 | 40 | 3 | 0.000673 s |
| Semantic Web composition | 3 | 123 | 5 | 0.017651 s |
| MF-JSON Prism composition | 2 | 48 | 3 | 0.000415 s |

Timings are a five-repetition, warm-process local microbenchmark that includes
parsing and validation. MF-JSON was faster than PULSE in this tiny task. The
file and line counts cover only checked-in input artifacts; shared Python
workflow and adapter source is excluded. The table is retained for
reproducibility, not as evidence of usability, maintainability, concision, or
developer productivity.

The Semantic Web path uses RDFLib, pySHACL, and a Shapely/GEOS implementation
of the referenced GeoSPARQL function. It is not an external GeoSPARQL server or
a GeoSPARQL conformance result.

## Reproduce

```powershell
python -m pip install -e .[test]
pulse-spatial-composition `
  --repetitions 5 `
  --require-equivalence
```

The machine-readable and Markdown reports are in [`results/`](results/).

## Temporal contract mutation sensitivity

The companion experiment exhaustively generates 37,440 traces from the declared
finite grid: lengths 2--5, every Boolean membership sequence, time increments
of 1/5/10/11 minutes, two initial states, and presence/absence of a same-trigger
immediate transition. The unmodified PULSE runtime and an independently
implemented reference workflow must match on every trace. Ten mutants are then
run over the same corpus; each changes exactly one checked semantic field,
covering cancellation, timer order, start/deadline guards, equality at the
deadline, short/long durations, emission time, transition timing, and
pre- versus post-immediate monitor eligibility.

```powershell
pulse-spatial-contract-faults `
  --require-complete `
  --output-json experiments/composition/results/temporal-contract-mutation-sensitivity-2026-07-21.json `
  --output-markdown experiments/composition/results/temporal-contract-mutation-sensitivity-2026-07-21.md
```

This is exhaustive only over the declared finite trace and mutation domains.
It does not establish general correctness or compare language expressiveness,
standards capability, usability, defect prevalence, or developer productivity.
