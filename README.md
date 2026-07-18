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

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m unittest discover -s tests -v
```

No runtime dependency is required for the initial topological kernel. Geometry
adapters for GEOS/JTS/PostGIS are planned rather than reimplementing a full GIS
engine here.

## Repository map

- `docs/language-design.md` — semantic scope, formal sketch, and research plan
- `docs/standards-map.md` — standards alignment and non-equivalence boundaries
- `grammar/pulse-s.ebnf` — proposed PULSE-S surface syntax
- `src/pulse_spatial/` — executable geometry, modal state, runtime, and RDF view
- `examples/cold_chain_geofence.pulse` — motivating language example
- `tests/` — executable semantic contracts

## Near-term roadmap

1. Freeze the minimal spatial value and predicate model.
2. Add a parser from the PULSE-S syntax to the typed IR.
3. Project asserted geometries to GeoSPARQL and observations to SOSA/SSN.
4. Add explicit accuracy regions and coordinate transformations.
5. Replay a real trajectory dataset with chronological holdout tests.
6. Compare against GeoSPARQL + workflow glue and a Moving Features baseline.

## License

Apache-2.0.
