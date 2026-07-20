# OGC GeoSPARQL 1.1 conformance coverage

This directory pins the complete normative Abstract Test Suite (ATS) inventory
from Annex A of OGC GeoSPARQL 1.1 (OGC 22-047r1): seven conformance classes and
55 abstract tests.  `ats-manifest.json` is a coverage oracle, not a fabricated
OGC certification.

The OGC standard defines conformance per class: an implementation may claim a
class only when every abstract test in that class passes.  The official
`opengeospatial/ets-geosparql11` repository is tracked separately because, as
of the pinned audit, it remains a development template rather than a complete
executable realization of all 55 abstract tests.  PULSE therefore reports:

1. inventory completeness against the normative Annex A identifiers;
2. concrete executable probes for every abstract test;
3. pass, fail, error, manual-review, and not-claimed states without silently
   treating unsupported serializations or DGGS as successes; and
4. conformance-class claims only when all tests in that class pass.

The existing 7,396-row Jena comparison remains a differential topology
experiment.  It is complementary to this class-level conformance audit.

The checked-in 2026-07-20 run covers all 55 identifiers with 124 probes and
claims four complete classes for the tested Jena configuration: Core,
Topology Vocabulary Extension, Geometry Topology Extension, and RDFS
Entailment Extension. Geometry Extension, Geometry Extension (DGGS), and Query
Rewrite Extension fail. “Complete” in this directory therefore means complete
normative inventory and traceable execution coverage, not 7/7 conformance.

```bash
docker build --tag pulse-jena-geosparql:6.1.0 external/jena-geosparql
pulse-spatial-ogc-conformance --require-complete-coverage
```
