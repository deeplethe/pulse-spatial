# OGC GeoSPARQL 1.1 complete ATS coverage

- Conformance classes: 7
- Normative abstract tests: 55
- Executable/manual component probes: 185
- Query-rewrite rule-shape assertions: 96
- Inventory coverage complete: **True**
- Query-rewrite profile: Apache Jena native GeoSPARQL inferencing
- Geometry profile: disabled
- DGGS profile: disabled
- Claimable classes: /conf/core, /conf/topology-vocab-extension, /conf/geometry-topology-extension, /conf/rdfs-entailment-extension, /conf/query-rewrite-extension

| Conformance class | Status | Claimable |
|---|---:|---:|
| `/conf/core` | pass | True |
| `/conf/topology-vocab-extension` | pass | True |
| `/conf/geometry-extension` | fail | False |
| `/conf/geometry-extension-dggs` | fail | False |
| `/conf/geometry-topology-extension` | pass | True |
| `/conf/rdfs-entailment-extension` | pass | True |
| `/conf/query-rewrite-extension` | pass | True |

## Claim boundary

Complete coverage of all 55 normative GeoSPARQL 1.1 abstract-test identifiers with researcher-authored executable refinements. No PULSE query-rewrite adapter is enabled; Apache Jena native GeoSPARQL inferencing remains active. No PULSE geometry-function profile is enabled. No PULSE DGGS profile is enabled. A class is claimable only when all its abstract tests pass. This is not an OGC-issued certificate, and manual requirements remain manual rather than being silently counted as passes.
