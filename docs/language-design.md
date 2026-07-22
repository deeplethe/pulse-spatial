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
sample is retained until the next move. Equal-time moves are accepted in caller
order and may create crossings or reconcile monitors without advancing time. An
inverse crossing before the deadline cancels a pending qualification. Timers
due at the same time as a move fire first; equal deadlines are ordered by the
compiler-assigned grounded declaration rank. `started_at` records the crossing, `effective_at` the duration deadline,
and `emitted_at` the runtime clock advance that exposed the event. A guarded
duration rule starts only when its source state matches at the crossing; its
state transition is guarded again at emission. A scenario over an active
runtime clones its asserted state, evidence, object states, clock, and pending
monitors, then begins no earlier than that clock, the latest observation, or an
explicit start. Without an active runtime it clones the compiled base world
with no pending monitors and defaults to the latest timestamp (Unix epoch if none),
applies untimed assumptions at that instant in declaration order, and advances
its isolated clock by the declared `run` duration. This remains discrete
sample-and-hold execution, not continuous simulation.

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

The scale real-data experiment replays the official NOAA IBTrACS `since1980`
main tracks through frozen experiment-defined polygons. It covers 4,775 tracks,
300,033 points, and 295,258 transitions. The single-zone trace has 571 event
transitions; the five-zone duration protocol evaluates 1,476,290
transition-region pairs, 4,800 instantaneous events, and 12,831 sustained
events. PULSE and the separately implemented GEOS/event-sweep path have zero
differences at membership, instantaneous-event, and timestamp layers.

The projection experiment now includes unmodified Apache Jena GeoSPARQL 6.1.0.
Fourteen CRS84 topology points and regions create a 196-pair query cross
product; `sfWithin` and `sfIntersects` agree with PULSE on every row, including
the intended boundary cases. This externally exposed that `ehCoveredBy` was
not the correct realization of the language's Point/Polygon boundary-inclusive
membership, so the generated projection was corrected.

General safety proofs are supported by 3,534 bounded exhaustive checks, and a
synthetic scale ladder separates move execution, evidence ingestion, and RDF
materialization through 100,000 items. Remaining evaluation priorities are a
persistent indexed spatial store, explicit antimeridian and CRS-transformation
policies, a proof-assistant model, and a preregistered modeling study.
