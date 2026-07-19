# PULSE spatiotemporal evaluation plan

The evaluation separates semantic correctness, empirical execution,
interoperability, modeling burden, and human usability. Passing one category
must not be reported as evidence for another.

## Research questions

- **RQ1 -- modal preservation:** Can asserted, observed, normative, and
  hypothetical spatiotemporal content coexist without silent overwrites?
- **RQ2 -- spatial correctness:** Do PULSE Point/Polygon membership and
  crossing traces agree with an independent geometry engine?
- **RQ3 -- temporal correctness:** Do duration-qualified events agree with an
  independent event-sweep implementation under a frozen clock policy?
- **RQ4 -- projection fidelity:** Do RDF, GeoSPARQL, SOSA, SHACL, and OWL-Time
  views preserve their declared subset of the authoritative model?
- **RQ5 -- composition burden:** For the same executable workload, which
  identifiers, files, adapters, and duplicated rules are required by PULSE and
  by a GeoSPARQL + SHACL + workflow composition?
- **RQ6 -- usability:** Do modelers complete equivalent tasks more accurately
  or quickly? This requires a preregistered user study and cannot be inferred
  from lines of code.

## Experiment matrix

| ID | Evidence | Baseline | Status | Permitted claim |
|---|---|---|---|---|
| E0 | 34 semantic and integration tests | Explicit expected contracts | Executed | Core invariants hold for tested cases |
| E1 | RDF/SHACL cross-view validation | pySHACL + GEOS functions | Executed | Tested projection outcomes agree |
| E2 | 223 IBTrACS tracks, one polygon | Shapely/GEOS `covers` | Executed | Single-zone event-label parity |
| E3 | Five zones; 6/12/24-hour events | GEOS + independent event sweep | Executed | Discrete multizone spatiotemporal parity |
| E4 | Boundary, holes, invalid geometry corpus | OGC/GeoSPARQL reference cases | Planned | Predicate-subset conformance |
| E5 | Frozen cold-chain implementation | GeoSPARQL + SHACL + workflow glue | Planned | Descriptive composition burden only |
| E6 | Chronological frozen-rule holdout | Moving Features/workflow baseline | Planned | Limited temporal transfer |
| E7 | Counterbalanced modeling tasks | Qualified participants | Planned | Usability differences with uncertainty |

## Current E3 protocol

The authoritative clock is discrete event time. Positions use sample-and-hold
between ordered observations. At a timestamp shared by a timer deadline and a
new move, the timer fires first. A crossing starts one monitor for each duration;
an inverse crossing cancels monitors that have not reached their deadline.

The comparison evaluates:

1. the Boolean membership label for every transition-zone pair;
2. every instantaneous `enters` or `leaves` label;
3. every sustained label including start, effective, and emission timestamps.

The report additionally summarizes emission lag and identifies monitors that
remain un-emitted by track end or an inverse crossing. It does not infer the
unobserved continuous path between samples.

All five polygons are experiment-defined, may overlap, and are not official
NOAA boundaries. The independent path uses Shapely/GEOS for membership and a
separately implemented event-sweep algorithm for duration deadlines.

## Reporting rules

- Always publish source/snapshot hashes, environment versions, and raw JSON.
- Treat timing as a local microbenchmark unless a database benchmark is run.
- Report exact mismatch counts and samples, not only aggregate event counts.
- Do not call E2 or E3 GeoSPARQL conformance tests.
- Do not infer usability from syntax length or artifact count.
- Do not extrapolate sample-and-hold results to continuous trajectories.
