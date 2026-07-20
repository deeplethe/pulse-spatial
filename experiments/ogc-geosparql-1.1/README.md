# GeoSPARQL 1.1 Annex A identifier and custom-probe coverage

This directory pins a researcher-authored transcription of the normative
Abstract Test Suite (ATS) inventory from Annex A of OGC GeoSPARQL 1.1 (OGC
22-047r1): seven conformance-class groups and 55 abstract-test identifiers.
`ats-manifest.json` is a coverage manifest, not an independently extracted
inventory or an OGC certification.

The OGC standard defines conformance per class and requires correct results for
the applicable abstract tests. The official
`opengeospatial/ets-geosparql11` repository is tracked separately because the
pinned audit found a development template rather than a complete executable
realization of all 55 abstract tests. PULSE therefore reports:

1. inventory completeness against the normative Annex A identifiers;
2. concrete executable probes for every abstract test;
3. pass, fail, error, manual-review, and not-claimed states without silently
   treating unsupported serializations or DGGS as successes; and
4. descriptive class-group completeness only when all mapped custom probes
   pass. This does not assert conformance of the class.

The official `opengeospatial/ogc-geosparql` tag `1.1.0-ghpages` is also pinned
at commit `cd53678be2e9775066d63791c84c3fa010fc29ff`. Its two auxiliary RDF
registers are integrity-checked and parsed by
`pulse-spatial-ogc-source-audit`. They are deliberately not presented as an
executable ETS or as interchangeable with Annex A: the requirements register
contains 58 `spec:ConformanceTest` resources, while its service description
lists 52 `sd:feature` resources. The local manifest transcribes 55 Annex A
identifiers across seven groups. The audit corroborates all 55 manifest names
against the register and preserves exact cross-source deltas; it does not parse
the specification HTML independently.

The existing 7,396-row Jena comparison remains a differential topology
experiment. It is complementary to this class-level conformance audit.

The checked-in 2026-07-20 matrix covers all 55 identifiers with 185 executable
component probes. The Query Rewrite tests check all 24 named relations in all
four normative feature/geometry rule shapes, for 96 rule-shape assertions.

The unmodified Apache Jena GeoSPARQL 6.1.0 baseline passes 112/185 custom probes.
Five of seven Annex A class groups have every mapped probe pass; this grouping
is diagnostic and is not a conformance-class claim.

The isolated PULSE profiles add GeoSPARQL 1.1 non-DGGS functions and true
spatial aggregates, plus an H3 4.4.0 DGGS literal/function profile. With the
PULSE WKT query-rewrite adapter enabled, the combined profile passes 185/185
researcher-authored probes. All seven Annex A class groups are probe-complete,
but this does not establish that the normative abstract test purposes return
correct results and is not an OGC-issued certificate. In particular, the H3
profile has declared finite-resolution coverage semantics and locally
approximated metric operations; see `docs/geosparql-profile.md`.

```bash
docker build --tag pulse-jena-geosparql:6.1.0 external/jena-geosparql
pulse-spatial-ogc-source-audit --require-audit-pass
pulse-spatial-ogc-conformance --require-complete-coverage
pulse-spatial-ogc-conformance \
  --query-rewrite --geometry-profile --dggs-profile \
  --require-probe-complete-class /conf/geometry-extension \
  --require-probe-complete-class /conf/geometry-extension-dggs \
  --require-probe-complete-class /conf/query-rewrite-extension
```
