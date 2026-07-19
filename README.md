# PULSE spatiotemporal research

This repository incubates first-class time and space semantics for PULSE 1.0.
The PULSE-S name identifies the spatial implementation module; it is not
intended to become a separate language. The work studies how one
spatiotemporal proposition can be treated differently when it is asserted,
observed, normative, or hypothetical, and how topological and temporal changes
can drive deterministic process transitions.

The repository is intentionally separate from the PULSE v0.1 paper artifact.
It is a pre-alpha research workspace, not a GeoSPARQL, OGC Moving Features, or
ISO conformance implementation.

## Research thesis

PULSE-S aims to answer four distinct questions in one authoritative model:

| Mode | Spatial question |
|---|---|
| Asserted | Where is the object authoritatively believed to be? |
| Observed | Where was it measured, by which source, with what uncertainty? |
| Normative | Where must or must not it be? |
| Hypothetical | What would happen if it were somewhere else? |

The executable slice derives `enters` and `leaves` events from position
changes, applies declaration-ordered geofence rules, keeps observations from
overwriting asserted positions, and evaluates scenarios on cloned worlds.
PULSE-S source is parsed into an immutable typed document and then compiled
into a validated runtime model; syntax and semantic failures are kept distinct.
Duration-qualified spatial events use an explicit discrete sample-and-hold
clock: an inverse crossing before the deadline cancels the pending event, while
a reached deadline records start, effective, and emission times separately.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[test]
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Compile the example and execute its counterfactual reroute:

```powershell
.\.venv\Scripts\pulse-spatial examples\cold_chain_geofence.pulse `
  --scenario EmergencyReroute `
  --emit-projections build\projections `
  --validate-projections
```

The command reports the model inventory, normative violations, derived
`leaves` event, and scenario answers as JSON. The example's asserted position
remains inside `ColdZone`; its later GPS observation is outside but does not
silently replace that assertion. The scenario moves an isolated copy and
changes its state from `Safe` to `AtRisk`.

Projection export writes two UTF-8 Turtle files. The data graph combines
asserted GeoSPARQL geometry and SOSA observations while retaining PULSE-S modal
annotations. The shapes graph expresses normative geofences as SHACL-SPARQL.
Executing those shapes requires a SHACL engine with GeoSPARQL function support;
SHACL Core alone is insufficient.

The optional reference validator executes the generated shapes with pySHACL
and supplies `geof:sfWithin` and `geof:ehCoveredBy` through Shapely/GEOS. It
compares conformance and violation counts with the internal PULSE-S validator.
This is a cross-view parity backend, not a claim of full GeoSPARQL conformance.

No runtime dependency is required for the core topological kernel. The
`validation` extra adds pySHACL and Shapely/GEOS for independent projection
checks; server adapters for Jena/PostGIS-class engines remain planned.

## Executed real-trajectory experiment

The repository includes an executed NOAA IBTrACS experiment, not only toy
examples. It replays 223 tropical-cyclone tracks (13,784 points and 13,561
consecutive transitions) through an experiment-defined geofence and compares
the complete event-label trace with an independent Shapely/GEOS implementation.
The two paths produced 0 mismatches across all transitions, including 38
event-bearing transitions. See the
[`experiments/ibtracs` protocol and provenance](experiments/ibtracs/README.md)
and the
[`machine-readable result`](experiments/ibtracs/results/ibtracs-last3years-2026-07-19.json).

This result supports execution feasibility and event-label parity for the
tested Point/Polygon workload. It is not a claim of full GeoSPARQL conformance,
geodesic accuracy, prediction quality, or industrial performance.

A second executed experiment covers five overlapping study zones and
duration-qualified events. Across 67,805 transition-zone pairs, PULSE and an
independent GEOS plus event-sweep baseline had zero membership, instantaneous
event, or sustained-event mismatches. The run produced 175 instantaneous and
475 sustained events at 6, 12, and 24-hour thresholds. See the
[`spatiotemporal experiment`](experiments/spatiotemporal/README.md).

A third experiment freezes one cold-chain trajectory and policy, then executes
it as PULSE, a GeoSPARQL/SOSA/OWL-Time + SHACL + workflow composition, and an
MF-JSON Prism + workflow composition. All three reproduce the same cancellation,
duration-qualified event, and final state. The checked-in artifact metrics are
descriptive rather than a usability claim; see the
[`composition comparison`](experiments/composition/README.md).

## Repository map

- `docs/language-design.md` — semantic scope, formal sketch, and research plan
- `docs/projections.md` — RDF projection contract and portability boundary
- `docs/reference-validation.md` — cross-view parity protocol and limitations
- `docs/standards-map.md` — standards alignment and non-equivalence boundaries
- `docs/evaluation-plan.md` — research questions, experiment matrix, and claims
- `experiments/ibtracs/` — real-data protocol, snapshot, results, and provenance
- `experiments/spatiotemporal/` — multizone duration protocol and results
- `experiments/composition/` — three-path executable composition comparison
- `grammar/pulse-s.ebnf` — proposed PULSE-S surface syntax
- `src/pulse_spatial/language.py` — immutable typed syntax model
- `src/pulse_spatial/parser.py` — lexer and recursive-descent parser
- `src/pulse_spatial/compiler.py` — name resolution and semantic validation
- `src/pulse_spatial/` — geometry, modal runtime, CLI, and RDF view
- `examples/cold_chain_geofence.pulse` — motivating language example
- `tests/` — executable semantic contracts

## Near-term roadmap

1. Add a full external GeoSPARQL service adapter and conformance corpus.
2. Add explicit accuracy regions and coordinate transformations.
3. Add polygon holes, multipolygons, and explicit antimeridian handling.
4. Project temporal events and intervals through an OWL-Time profile.
5. Add chronological rule-freezing and holdout evaluation.
6. Repeat the composition comparison with an external GeoSPARQL service and
   larger frozen workloads.

## License

Apache-2.0.
