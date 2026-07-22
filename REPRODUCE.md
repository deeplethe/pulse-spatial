# Paper reproduction manifest

This file maps the paper's executable evidence to commands and checked-in
outputs. Run commands from the repository root at the frozen paper commit.
The paper's comparison and load results are evidence only within the claim
boundaries in the linked protocols.

## Common environment

- Python: CPython 3.11 and 3.12 are tested; the primary CI job uses 3.12.
  Install exact direct and transitive versions with
  `python -m pip install -r requirements-lock.txt`, followed by
  `python -m pip install --no-deps -e .`.
- Lightweight Python checks require less than 1 GiB RAM and no external
  service. Docker experiments require Docker Desktop or an equivalent engine.
- Lean is pinned by `formal/lean/lean-toolchain`; external container images are
  pinned in their protocol or Docker files. Dataset provenance and hashes are
  under `experiments/ibtracs/snapshots/`.

Recorded JSON and Markdown files are committed so results can be audited
without rerunning Docker or the large NOAA workload. Wall times are
host-dependent; these commands impose no portable performance expectation.

## Paper evidence map

| Paper evidence | Command | Expected result/output | Inputs and practical requirements |
|---|---|---|---|
| Table 4, core regression suite | `python -m unittest discover -s tests -v` | 88 tests pass | Local Python; under 1 GiB; normally seconds |
| Table 4, bounded core checks | `python -m pulse_spatial.experiments.formal_properties --max-depth 4 --output-json experiments/formal-properties/results/bounded-depth4.json --output-markdown experiments/formal-properties/results/bounded-depth4.md` | 340 bounded move traces and 3,534 checks, no failures | Local Python; under 1 GiB; normally seconds |
| Table 4, Lean kernel | `docker build --tag pulse-lean:4.30.0 formal/lean`, then `docker run --rm pulse-lean:4.30.0` | Lean build succeeds without `sorry` or `admit` | Docker; allow several minutes and image-build disk |
| Table 4, Lean/Python bridge | From `formal/lean`, run `lake exe pulse_traces > generated-integrated-traces.json`; then run `pulse-spatial-lean-trace-bridge --require-exact` at the root | 32/32 aligned finite cases | Lean toolchain plus local Python |
| Table 4, temporal trace/mutant study | `pulse-spatial-contract-faults --require-complete --output-json experiments/composition/results/temporal-contract-mutation-sensitivity-2026-07-21.json --output-markdown experiments/composition/results/temporal-contract-mutation-sensitivity-2026-07-21.md` | 37,440/37,440 reference matches; 10/10 mutants killed | Local Python; CPU-bound finite enumeration |
| Table 4, topology corpus | `pulse-spatial-topology-corpus --require-parity --output-json experiments/topology/results/topology-corpus-expanded-2026-07-20.json --output-markdown experiments/topology/results/topology-corpus-expanded-2026-07-20.md` | 89 valid cases and 9 rejection cases; zero GEOS differences | Python test extras including Shapely/GEOS |
| Table 4, external Jena rows | Run `docker build --quiet -t pulse-jena-geosparql:6.1.0 external/jena-geosparql`, then `python -m pulse_spatial.experiments.geosparql_external --require-parity --output-json experiments/geosparql-external/results/jena-topology.json --output-markdown experiments/geosparql-external/results/jena-topology.md` | 7,396 rows; zero differences | Docker/Java image; see `experiments/geosparql-external/README.md` |
| Table 4, custom GeoSPARQL probe inventory | After building the Jena image, run `pulse-spatial-ogc-source-audit --require-audit-pass`, `pulse-spatial-ogc-conformance --require-complete-coverage`, then `pulse-spatial-ogc-conformance --query-rewrite --geometry-profile --dggs-profile --require-probe-complete-class /conf/geometry-extension --require-probe-complete-class /conf/geometry-extension-dggs --require-probe-complete-class /conf/query-rewrite-extension` | 55/55 identifier map; 112/185 native and 185/185 profile probes | Docker/Jena; researcher-authored probes, not an OGC ETS |
| Table 4, four-role case | `python -m pulse_spatial.experiments.end_to_end --output-json experiments/end-to-end/results/ibtracs-four-mode-2026-07-19.json --output-markdown experiments/end-to-end/results/ibtracs-four-mode-2026-07-19.md --require-all-checks` | Frozen 91-point checks pass | Checked-in track; Python validation extras |
| Table 4, composition equivalence | `pulse-spatial-composition --repetitions 5 --require-equivalence` | Three frozen paths reproduce the expected trace | Local Python; microbenchmark values are host-specific |
| Table 5, RDF/Sismic fault location | `python -m pulse_spatial.experiments.statechart_comparison --require-complete --output-json experiments/statechart-comparison/results/statechart-fault-location-2026-07-21.json --output-markdown experiments/statechart-comparison/results/statechart-fault-location-2026-07-21.md` | All four declared faults are located as reported | Researcher-authored Sismic model and adapters |
| Table 4, full IBTrACS replay | `pulse-spatial-spatiotemporal --data PATH_TO_SINCE1980.csv --repetitions 5 --require-parity` | 4,775 valid tracks, 1,476,290 transition-zone pairs, zero differences | 143 MiB NOAA input verified against `experiments/ibtracs/snapshots/SINCE1980_PROVENANCE.md`; CPU-bound |
| Table 4, PostGIS parity/persistence | `pulse-spatial-postgis --data PATH_TO_SINCE1980.csv --require-parity` | Stored memberships and events agree and survive container replacement | Docker, PostgreSQL 18/PostGIS 3.6; database volume and 143 MiB input |
| Table 4, PostGIS concurrency/recovery | Commands in `experiments/postgis/CONCURRENCY.md` | Checked-in reports contain resource, WAL, latency, skip, and restart evidence | Docker; reported host used 24 logical CPUs and 16.3 GiB assigned RAM; long-running |

## Static tables and views

Paper Tables 1--3 describe contract placement, event rules, and projection
fidelity. They are specifications rather than benchmark outputs. Projection
regressions are exercised by `python -m unittest discover -s tests -v`; `docs/projections.md`
defines what each RDF/SHACL view preserves, approximates, or omits. No reverse
round trip from the generated views to the authoritative PULSE model is claimed.

## Raw results and failures

Each experiment directory contains its protocol and machine-readable result.
A reproduction fails if a command with a `--require-*` flag exits nonzero or if
its reported counts differ from the frozen result for a non-performance field.
Throughput and latency are machine observations and should not be expected to
match across hosts.
