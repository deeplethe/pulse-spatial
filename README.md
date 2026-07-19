# PULSE Spatial

PULSE Spatial (PULSE-S) is an experimental spatial extension of the PULSE
process-aware semantic language. It studies how one spatial proposition can be
treated differently when it is asserted, observed, normative, or hypothetical,
and how topological changes can drive deterministic process transitions.

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

The first executable slice derives `enters` and `leaves` events from position
changes, applies declaration-ordered geofence rules, keeps observations from
overwriting asserted positions, and evaluates scenarios on cloned worlds.
PULSE-S source is parsed into an immutable typed document and then compiled
into a validated runtime model; syntax and semantic failures are kept distinct.

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

## Repository map

- `docs/language-design.md` — semantic scope, formal sketch, and research plan
- `docs/projections.md` — RDF projection contract and portability boundary
- `docs/reference-validation.md` — cross-view parity protocol and limitations
- `docs/standards-map.md` — standards alignment and non-equivalence boundaries
- `grammar/pulse-s.ebnf` — proposed PULSE-S surface syntax
- `src/pulse_spatial/language.py` — immutable typed syntax model
- `src/pulse_spatial/parser.py` — lexer and recursive-descent parser
- `src/pulse_spatial/compiler.py` — name resolution and semantic validation
- `src/pulse_spatial/` — geometry, modal runtime, CLI, and RDF view
- `examples/cold_chain_geofence.pulse` — motivating language example
- `tests/` — executable semantic contracts

## Near-term roadmap

1. Freeze the minimal spatial value and predicate model.
2. Add a full external GeoSPARQL service adapter and conformance corpus.
3. Add explicit accuracy regions and coordinate transformations.
4. Add duration-qualified spatial event semantics.
5. Replay a real trajectory dataset with chronological holdout tests.
6. Compare against GeoSPARQL + workflow glue and a Moving Features baseline.

## License

Apache-2.0.
