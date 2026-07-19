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
Duration-qualified process guards are parsed but rejected by the compiler until
their clock and sampling semantics are defined. A scenario `run` duration is
retained as a horizon annotation; it does not imply continuous simulation.

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
RDFLib. This establishes syntactic validity, not SHACL or GeoSPARQL entailment.
Constraint execution requires an engine that implements both SHACL-SPARQL and
the referenced GeoSPARQL functions.

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

## Evaluation direction

Use a real moving-object dataset with a chronological split. Freeze regions and
event rules from the earlier segment, then replay later trajectories without
adding routes or geofences. Compare event traces against a reference spatial
engine and test observation non-overwrite, scenario isolation, CRS rejection,
and projection parsing independently.
