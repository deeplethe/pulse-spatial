# GeoSPARQL 1.1 researcher-authored probe coverage

- Annex A class groups represented: 7
- Normative abstract tests: 55
- Executable/manual component probes: 185
- Query-rewrite rule-shape assertions: 96
- Inventory coverage complete: **True**
- Query-rewrite profile: Apache Jena native GeoSPARQL inferencing
- Geometry profile: disabled
- DGGS profile: disabled
- Probe-complete class groups: /conf/core, /conf/topology-vocab-extension, /conf/geometry-topology-extension, /conf/rdfs-entailment-extension, /conf/query-rewrite-extension

| Annex A class group | Probe status | All mapped probes pass |
|---|---:|---:|
| `/conf/core` | pass | True |
| `/conf/topology-vocab-extension` | pass | True |
| `/conf/geometry-extension` | fail | False |
| `/conf/geometry-extension-dggs` | fail | False |
| `/conf/geometry-topology-extension` | pass | True |
| `/conf/rdfs-entailment-extension` | pass | True |
| `/conf/query-rewrite-extension` | pass | True |

## Claim boundary

Complete coverage of all 55 normative GeoSPARQL 1.1 abstract-test identifiers with researcher-authored executable refinements. No PULSE query-rewrite adapter is enabled; Apache Jena native GeoSPARQL inferencing remains active. No PULSE geometry-function profile is enabled. No PULSE DGGS profile is enabled. Class groupings report only whether every mapped custom probe passed. They are descriptive coverage groups, not GeoSPARQL conformance-class claims or an OGC-issued certificate. Manual requirements remain manual rather than being silently counted as passes.
