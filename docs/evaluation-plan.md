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
| E0 | 72 semantic and integration tests | Explicit expected contracts | Executed | Core invariants and the paper listing hold for tested cases |
| E1 | RDF/SHACL cross-view validation | pySHACL + GEOS functions | Executed | Tested projection outcomes agree |
| E2 | 223 IBTrACS tracks, one polygon | Shapely/GEOS `covers` | Executed | Single-zone event-label parity |
| E3 | Five zones; 6/12/24-hour events | GEOS + independent event sweep | Executed | Discrete multizone spatiotemporal parity |
| E4 | 89 boundary/numeric cases; 9 rejection cases; 86 CRS84 shared-workload cases | Shapely/GEOS | Executed | Differential parity for the frozen Point/simple-Polygon corpus |
| E5 | Frozen cold-chain implementation | GeoSPARQL/SHACL and MF-JSON Prism compositions | Executed | Outcome equivalence and descriptive composition only |
| E6 | Chronological frozen-rule holdout | Moving Features/workflow baseline | Planned | Limited temporal transfer |
| E7 | Counterbalanced modeling tasks | Qualified participants | Planned | Usability differences with uncertainty |
| E8 | 7,396 external query rows; four Simple Features relations | Apache Jena GeoSPARQL 6.1.0 | Executed | External-engine agreement for the supported profile |
| E9 | Transition kernel plus duration-monitor lifecycle | Lean 4.30.0 | Executed | Core safety plus cancellation, exact-deadline, future-deadline, and finite-growth properties are proof-checked |
| E10 | 300,033 persisted points; 1,476,290 transition-zone pairs | PostgreSQL 18/PostGIS 3.6 with GiST | Executed | Indexed membership and derived-event parity with restart persistence |
| E11 | 55/55 GeoSPARQL 1.1 Annex A identifiers; 185 custom probes; 96 query-rewrite rule shapes | Normative OGC 22-047r1 inventory + Jena 6.1.0 + H3 4.4.0 | Executed | Native baseline 112/185; isolated PULSE profiles 185/185 under a researcher-authored harness; no conformance-class claim |
| E12 | Separated-container concurrency, PostgreSQL/WAL/resource telemetry, SIGKILL recovery, open-loop SLO | PostgreSQL 18/PostGIS 3.6 + pgbench | Executed | Reset-state single-node scaling; 10k TPS host-scoped repeated-window lower bound; recovery evidence |
| E13 | Official RDF source integrity and inventory audit | OGC `ogc-geosparql` tag `1.1.0-ghpages` | Executed | 55 Annex allocations are source-corroborated; 55/58/52 inventory differences are explicit, not treated as an ETS |
| E14 | Same 7,396 Point/Polygon pairs and four predicates as E8 | PostgreSQL 18/PostGIS 3.6 | Executed | Zero-mismatch PULSE/Jena/PostGIS triangulation on one shared workload |

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

## E5 composition protocol

E5 freezes one trajectory, boundary policy, timer ordering, duration, and state
transition. PULSE, a Semantic Web composition, and an MF-JSON Prism composition
must reproduce the complete expected trace. MF-JSON Prism uses `Step`
interpolation; MF-JSON Trajectory's linear interpolation would be a different
task. Non-PULSE paths use explicit workflow code because representation,
query, and validation standards do not themselves execute the state change.

Artifact file count, substantive lines, declared components, and warm-process
timing are recorded as descriptive facts about the checked-in implementations.
They are not treated as proxies for usability, maintainability, or productivity.

## E4 topology-corpus protocol

E4 is deliberately a differential regression corpus rather than an official
standards-conformance suite. It compares the complete `within`, `onBoundary`,
and `coveredBy` result tuple for every valid case and checks explicit rejection
contracts for invalid geometry and CRS use. The cases cover boundary edges and
vertices, concavity, ring orientation, near-boundary coordinates, very small
and thin polygons, and large-offset local grids. Holes and antimeridian cases
are excluded because the current language slice cannot represent them.

## Reporting rules

- Always publish source/snapshot hashes, environment versions, and raw JSON.
- Treat timing as a local microbenchmark unless a database benchmark is run.
- Report exact mismatch counts and samples, not only aggregate event counts.
- Do not call E2 or E3 GeoSPARQL conformance tests.
- Do not call E4 an OGC or GeoSPARQL conformance suite.
- Do not describe E9 as a proof of floating-point geometry or the complete
  parser/compiler; geometry is abstracted by a total membership function and
  a Python refinement theorem remains future work.
- Keep E10's parity claim separate from E12's concurrency and SLO evidence.
- Report E12's 10,000 TPS value only with its scheduled-start 20 ms p99,
  100 ms pgbench admission threshold, 0.1% skip budget, three-repeat 60-second
  reset-state single-host protocol. Keep the 24,683.86 TPS closed-loop result
  and 43,898.03 TPS exploratory completion peak separate from SLO capacity.
- Describe E11 as 112/185 custom probes for the unmodified Jena baseline and
  185/185 for the isolated PULSE profiles, mapped to all 55 Annex A identifiers.
  Do not infer conformance-class passage from the researcher-authored probes.
  State the H3 finite-resolution and local metric approximation boundaries.
- Describe E13 as a provenance and cross-source consistency audit, never as
  execution of an official ETS. Annex A remains the normative authority.
- Describe E14 as shared-workload semantic agreement, not OGC certification or
  a like-for-like performance contest.
- Do not infer usability from syntax length or artifact count.
- Do not extrapolate sample-and-hold results to continuous trajectories.
