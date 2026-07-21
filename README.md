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
a reached deadline records start, effective, and emission times separately. A
guarded duration rule starts a monitor only when its source state matches at the
crossing and rechecks that state before applying the deadline transition.

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

The exact paper listing is also executable. Its relative scenario clock starts
at the latest observation timestamp, applies assumptions in declaration order,
and advances the isolated branch through the declared horizon:

```powershell
.\.venv\Scripts\pulse-spatial examples\paper_cold_chain_st.pulse `
  --scenario Reroute
```

Projection export writes two UTF-8 Turtle files. The data graph combines
asserted GeoSPARQL geometry and SOSA observations while retaining PULSE-S modal
annotations. The shapes graph expresses normative geofences as SHACL-SPARQL.
Executing those shapes requires a SHACL engine with GeoSPARQL function support;
SHACL Core alone is insufficient.

The optional reference validator executes the generated shapes with pySHACL
and supplies `geof:sfWithin` and `geof:sfIntersects` through Shapely/GEOS. It
compares conformance and violation counts with the internal PULSE-S validator.
This is a cross-view parity backend, not a claim of full GeoSPARQL conformance.

No runtime dependency is required for the core topological kernel. The
`validation` extra adds pySHACL and Shapely/GEOS for independent projection
checks. A pinned Apache Jena GeoSPARQL 6.1.0 container provides a genuinely
external query-engine comparison without adding Java to the core runtime.
A Lean 4.30.0 project mechanically checks the transition-safety kernel and a
surface-to-Core compiler for the paper subset. The Python compiler exports the
same canonical IR for the executable paper listing. A pinned PostgreSQL
18/PostGIS 3.6 container supplies an on-disk GiST-indexed
database baseline.

## Executed real-trajectory experiment

The repository includes an executed NOAA IBTrACS experiment, not only toy
examples. It replays 223 tropical-cyclone tracks (13,784 points and 13,561
consecutive transitions) through an experiment-defined geofence and compares
the complete event-label trace with a Shapely/GEOS reference implementation.
The two paths produced 0 mismatches across all transitions, including 38
event-bearing transitions. See the
[`experiments/ibtracs` protocol and provenance](experiments/ibtracs/README.md)
and the
[`machine-readable result`](experiments/ibtracs/results/ibtracs-last3years-2026-07-19.json).

This result supports execution feasibility and event-label parity for the
tested Point/Polygon workload. It is not a claim of full GeoSPARQL conformance,
geodesic accuracy, prediction quality, or industrial performance.

The scale run uses the official `since1980` subset rather than the small
checked-in snapshot. It loads 4,775 tracks; 4,768 contain at least two accepted
points and therefore contribute replay transitions. The workload has 300,033
points and 295,258 transitions from 1980--2025 across seven basins. All 571 event-bearing
transitions agree with the GEOS path. The five-zone duration run evaluates
1,476,290 transition-zone pairs, including 4,832 instantaneous and 12,870
sustained events, with zero membership, event, or timestamp differences. The
143 MB source is downloaded by DOI/URL and verified by SHA-256; it is not
vendored into the repository.

A second executed experiment covers five overlapping study zones and
duration-qualified events. Across 67,805 transition-zone pairs, PULSE and a
separately implemented GEOS plus event-sweep baseline had zero membership,
instantaneous event, or sustained-event mismatches. The run produced 175 instantaneous and
475 sustained events at 6, 12, and 24-hour thresholds. See the
[`spatiotemporal experiment`](experiments/spatiotemporal/README.md).

A third experiment freezes one cold-chain trajectory and policy, then executes
it as PULSE, a GeoSPARQL/SOSA/OWL-Time + SHACL + workflow composition, and an
MF-JSON Prism + workflow composition. All three reproduce the same cancellation,
duration-qualified event, and final state. The checked-in artifact metrics are
descriptive rather than a usability claim; see the
[`composition comparison`](experiments/composition/README.md).

A companion fault-localization probe changes only RDF-workflow orchestration
code. Four seeded mutants escape unchanged RDF/SHACL artifact validation and
are caught by external postcondition oracles; the corresponding PULSE boundary
contracts all hold. This locates enforcement responsibility rather than
measuring usability or defect prevalence; see the same
[`composition protocol`](experiments/composition/README.md).

A fourth experiment probes the Point/simple-Polygon kernel with 89 valid
boundary, concavity, ring-orientation, and numeric-scale cases plus 9 explicit
rejection cases. Of the 89 valid cases, 86 use CRS84 and form the shared
Jena/PostGIS projection subset. The checked-in run has zero differences from
Shapely/GEOS and rejects all invalid inputs as declared. This is a differential
regression corpus, not an OGC or GeoSPARQL conformance suite; see the
[`topology corpus`](experiments/topology/README.md).

A fifth experiment replays one frozen 91-point IBTrACS track through the full
four-mode chain: evidence recording, explicit authoritative acceptance,
duration-qualified process execution, guarded normative validation, an
isolated scenario, and RDF/SHACL projection. All checks pass and internal
validation matches the projected result; see the
[`end-to-end protocol`](experiments/end-to-end/README.md).

A sixth experiment checks whether six declared semantic policies are
observable by executing a counterexample against one alternative per policy.
All six alternatives change a modal state or event trace; see the
[`semantic sensitivity protocol`](experiments/semantic-sensitivity/README.md).

A seventh experiment evaluates the generated graph with unmodified Apache Jena
GeoSPARQL 6.1.0. The expanded 86 x 86 topology cross product produces 7,396
query rows, including 56 intended boundary pairs, with zero differences for
`sfWithin`, `sfIntersects`, `sfDisjoint`, and `sfTouches`; see the
[`external GeoSPARQL protocol`](experiments/geosparql-external/README.md).
The identical 7,396-pair graph is now also executed independently by
PostgreSQL/PostGIS using `ST_Within`, `ST_CoveredBy`, `ST_Disjoint`, and
`ST_Touches`, again with zero mismatches. This supplies a shared-workload
PULSE/Jena/PostGIS triangulation rather than comparisons over unrelated data.

An eighth experiment supports the general proofs with bounded exhaustive
checking. Every sequence through a four-position abstraction up to depth four
is executed twice. The recorded run performs 3,534 determinism, preservation,
finite-advance, atomic-failure, observation, and scenario checks with no
failure; see the [`formal property protocol`](experiments/formal-properties/README.md).

A ninth evidence path mechanizes the transition-safety kernel in Lean 4.30.0.
Lean checks preservation, deterministic evaluation, observation
non-interference, scenario isolation, finite time advance, and atomic failure.
It also models duration-qualified rule matching, opposite-crossing monitor
cancellation, and state-guarded monitor creation, proving guard eligibility,
exact deadlines, future-deadline preservation, cancellation filtering, and a
finite batch-growth bound.
The `PulseFormal.Compiler` module additionally resolves names, normalizes
seconds/minutes/hours, lowers Point assumptions and scenario horizons to Core
actions, and proves preservation of rule triggers, source-state guards,
positive durations, exact deadlines, finite horizons, and scenario execution
under that desugaring. The Python compiler and Lean exporter produce the same
canonical IR for `examples/paper_cold_chain_st.pulse`; CI regenerates both
sides and rejects drift.
The proof model abstracts computational geometry behind a total membership
function, so it verifies execution discipline rather than floating-point
topology; see [`formal/lean`](formal/lean/README.md).

A tenth experiment loads the complete since-1980 workload into a persistent
PostgreSQL 18/PostGIS 3.6 database. A GiST-indexed `ST_Covers` query returns
371,340 positive membership rows over 300,033 stored points. Replacing the
container while retaining its volume preserves every point and the index; the
derived membership, 4,832 instantaneous-event, and 12,870 sustained-event
layers have zero differences from PULSE across 1,476,290 transition-zone
pairs. See the [`PostGIS baseline`](experiments/postgis/README.md).

An eleventh evidence path maps every identifier in the normative GeoSPARQL 1.1
Abstract Test Suite: all seven class groups and all 55 abstract-test identifiers
are represented by 185 researcher-authored probes, including 96 query-rewrite
rule-shape assertions. The pinned unmodified Jena 6.1.0 baseline passes 112/185
probes, while the isolated PULSE Geometry and H3 profiles pass 185/185. These are
custom probe-coverage results, not conformance-class claims or an OGC-issued
certification; the finite-resolution H3 and local metric approximation
boundaries are reported explicitly. See the
[`GeoSPARQL 1.1 probe matrix`](experiments/ogc-geosparql-1.1/README.md).
The official `opengeospatial/ogc-geosparql` RDF registers are separately pinned
by tag, commit, and SHA-256. A reproducible source audit compares the
researcher-transcribed 55-name Annex A manifest with 58 independently counted
requirements-register resources and 52 service-description features. The audit
does not independently parse the specification HTML and does not misrepresent
the auxiliary graphs as an executable OGC ETS.

A twelfth experiment exercises a durable mixed PostGIS component workload: 60% point
membership, 20% GiST window scans, and 20% synchronous position updates plus
event appends. The database and pgbench load generator run in separate
containers; every measured run starts from the same rebuilt, checkpointed
50,000-device state. It bypasses the PULSE parser, modal runtime, and projection
path, so its throughput is not end-to-end PULSE throughput. A 32/64/96-client closed-loop resource sweep reaches
24,683.86 TPS at 96 clients with 17.402 ms p99 and zero failures; the database
uses 13.71 CPU cores on average while the generator uses 4.79. SIGKILL recovery
takes 2.348 s and passes row, version, index, and post-recovery workload checks.
Open-loop Poisson tests use scheduled-start latency, so p99 includes queueing.
Across 18,864,158 completed transactions, the conservative three-repeat,
60-second lower bound is 10,000 TPS (13.044 ms worst p99, 0.0576% maximum skip),
and 12,000 TPS is the first failed target under the 20 ms p99 and 0.1% skip
budget. The 43,898.03 TPS exploratory completion peak is not SLO capacity. See the
[`production-oriented concurrency protocol`](experiments/postgis/CONCURRENCY.md).

## Repository map

- `docs/formal-semantics.md` — core calculus, judgments, theorems, and proofs
- `docs/language-design.md` — semantic scope and research plan
- `docs/projections.md` — RDF projection contract and portability boundary
- `docs/reference-validation.md` — cross-view parity protocol and limitations
- `docs/standards-map.md` — standards alignment and non-equivalence boundaries
- `docs/evaluation-plan.md` — research questions, experiment matrix, and claims
- `experiments/ibtracs/` — real-data protocol, snapshot, and scale results
- `experiments/spatiotemporal/` — multizone duration protocol and results
- `experiments/geosparql-external/` — Apache Jena external-system agreement
- `experiments/ogc-geosparql-1.1/` — complete ATS inventory and class audit
- `experiments/formal-properties/` — bounded exhaustive semantic checks
- `experiments/composition/` — three-path executable composition comparison
- `experiments/topology/` — Point/Polygon boundary differential corpus
- `experiments/end-to-end/` — real-track four-mode integration case
- `experiments/semantic-sensitivity/` — semantic policy mutation checks
- `experiments/postgis/` — persistence, concurrency, recovery, and SLO reports
- `external/jena-geosparql/` — pinned Java/Docker comparison harness
- `external/ogc-geosparql-1.1/` — integrity-pinned official auxiliary RDF registers
- `formal/lean/` — Lean 4 safety kernel and verified paper-subset compiler
- `grammar/pulse-s.ebnf` — proposed PULSE-S surface syntax
- `src/pulse_spatial/` — language, compiler, geometry, runtime, and projections
- `examples/` — executable language examples
- `tests/` — executable semantic contracts

## Near-term roadmap

1. Extend the one-model Python/Lean canonical-IR correspondence to a generated
   well-typed corpus and prove rule-aware, declaration-ordered runtime
   refinement beyond the current scenario-action desugaring theorem.
2. Add explicit accuracy regions and coordinate transformations.
3. Add polygon holes, multipolygons, and explicit antimeridian handling.
4. Project temporal events and intervals through an OWL-Time profile.
5. Submit the GeoSPARQL profiles to an independent implementation test and
   replace the local H3 metric approximation with geodesic operations.
6. Repeat the open-loop protocol on pinned bare-metal and cloud instances,
   then study connection pooling, partitioning, replicas, and failover.
7. Expand beyond the supported Point/simple-Polygon standards profile without
   weakening the explicit non-conformance boundary.

## License

Apache-2.0.
