# PULSE-S language design

## Objective

Add first-class spatial values and predicates to PULSE without collapsing the
four semantic modes or turning the language runtime into a GIS engine.

The central semantic distinction is:

- an asserted position belongs to authoritative state;
- an observation is timestamped evidence and does not overwrite that state;
- a geofence constraint states what must hold;
- a scenario position is an isolated counterfactual override.

## Minimal spatial domain

Let `G_c` be the geometry domain of coordinate reference system `c`. Every
geometry value carries exactly one explicit CRS. Spatial predicates are partial
across CRSs: evaluation fails rather than silently comparing coordinates from
different reference systems.

The first slice contains:

- `Point` and `Polygon` values;
- `within` and `coveredBy` predicates;
- `enters` and `leaves` derived events;
- observations with time, source, confidence, and optional accuracy;
- normative geofence constraints;
- scenario-local position overrides.

Line strings, trajectories, coordinate transformation, buffers, metric
distance, and uncertain geometry are deliberately deferred.

## Executable alpha boundary

The current implementation tokenizes and parses the checked-in EBNF subset,
then resolves names and validates geometry types, state domains, CRS use,
observations, constraints, processes, and scenarios before constructing a
runtime world. `Point` instance properties and `Polygon` regions are executable.
Duration-qualified `enters` and `leaves` process guards are executable under a
timestamp-ordered, discrete sample-and-hold clock. The position asserted at one
sample is retained until the next move. An inverse crossing before the deadline
cancels a pending qualification. Timers due at the same time as a move fire
first. `started_at` records the crossing, `effective_at` the duration deadline,
and `emitted_at` the runtime clock advance that exposed the event. A scenario
`run` duration remains a horizon annotation; it does not imply continuous
simulation.

## Operational sketch

Let `A_t(i)` be the asserted position of instance `i` at step `t`, and let
`inside(g, r)` denote a topological predicate over geometries with the same CRS.

```text
enters(i, r, t) = not inside(A_(t-1)(i), r) and inside(A_t(i), r)
leaves(i, r, t) = inside(A_(t-1)(i), r) and not inside(A_t(i), r)
```

An event may trigger a declaration-ordered state rule. Recording an observation
adds evidence to `O`; it does not modify `A`. A scenario creates an isolated
copy `A_s`, applies assumptions and transitions to that copy, and leaves `A`
unchanged.

## Projection contract

- Asserted geometry projects to GeoSPARQL `geo:hasGeometry` / `geo:asWKT`.
- Observation projection uses SOSA and retains result time, source,
  confidence, and accuracy.
- Normative geofences project to SHACL-SPARQL with GeoSPARQL functions.
- Scenario state remains a JSON/runtime view unless explicitly published.
- OWL/RDF views are descriptive and are not the execution substrate.

The checked-in tests parse both Turtle graphs and their embedded SPARQL with
RDFLib. Optional integration tests execute the shapes with pySHACL and a
Shapely/GEOS implementation of the referenced functions, then compare results
with internal validation. This does not establish full GeoSPARQL conformance.

## Safety properties to test

1. Observation non-overwrite: adding evidence preserves asserted position.
2. Scenario isolation: counterfactual movement preserves the source world.
3. CRS safety: mixed-CRS predicates fail explicitly.
4. Topological determinism: fixed geometry and rule order yield one result.
5. State-domain preservation: rules only assign declared state values.
6. Diagnostic locality: malformed source reports its source line and column.

## Research questions

- RQ1: Can one typed model preserve the four spatial modes without conflation?
- RQ2: Do derived topological events reproduce a reference geometry engine?
- RQ3: Can standard projections retain the intended spatial role of each mode?
- RQ4: Does the language reduce modeling errors relative to a composed
  GeoSPARQL + SHACL + workflow implementation?

## Empirical status and evaluation direction

The first real-data experiment replays NOAA IBTrACS main tracks through one
frozen, experiment-defined polygon. The internal runtime and an independent
Shapely/GEOS path compare complete, ordered transition labels. The recorded
2026-07-19 run covered 223 tracks and 13,561 transitions with no label
mismatches. This establishes feasibility and Point/Polygon event-trace parity
for the tested workload, not full GeoSPARQL conformance or general validity.

The second experiment replays the same immutable snapshot through five
overlapping, experiment-defined regions and monitors 6, 12, and 24-hour
qualifications. It compares membership at every transition-region pair,
instantaneous crossings, and sustained-event timestamps with an independent
GEOS plus event-sweep implementation. The 2026-07-19 run covered 67,805
transition-region pairs and produced zero mismatches at all three layers.

The next experiment should introduce multiple overlapping geofences and a
chronological split. Freeze regions and event rules from the earlier segment,
then replay later trajectories without tuning routes or geofences. Compare with
an external GeoSPARQL service and a Moving Features/workflow baseline while
continuing to test observation non-overwrite, scenario isolation, CRS
rejection, and projection parsing independently.
