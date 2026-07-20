# GeoSPARQL 1.1 researcher-authored probe coverage

- Annex A class groups represented: 7
- Normative abstract tests: 55
- Executable/manual component probes: 185
- Query-rewrite rule-shape assertions: 96
- Inventory coverage complete: **True**
- Query-rewrite profile: PULSE WKT rule materialization; Jena native rules bypassed
- Geometry profile: PULSE GeoSPARQL 1.1 non-DGGS profile
- DGGS profile: PULSE H3 profile (H3 Java 4.4.0)
- Probe-complete class groups: /conf/core, /conf/topology-vocab-extension, /conf/geometry-extension, /conf/geometry-extension-dggs, /conf/geometry-topology-extension, /conf/rdfs-entailment-extension, /conf/query-rewrite-extension

| Annex A class group | Probe status | All mapped probes pass |
|---|---:|---:|
| `/conf/core` | pass | True |
| `/conf/topology-vocab-extension` | pass | True |
| `/conf/geometry-extension` | pass | True |
| `/conf/geometry-extension-dggs` | pass | True |
| `/conf/geometry-topology-extension` | pass | True |
| `/conf/rdfs-entailment-extension` | pass | True |
| `/conf/query-rewrite-extension` | pass | True |

## Claim boundary

Complete coverage of all 55 normative GeoSPARQL 1.1 abstract-test identifiers with researcher-authored executable refinements. The Query Rewrite Extension is evaluated with a PULSE-authored WKT rule-materialization adapter; all other classes use Apache Jena inferencing. Jena native rule inferencing is bypassed for the adapter probes. The Geometry Extension is evaluated with the PULSE GeoSPARQL 1.1 geometry profile. The DGGS Geometry Extension is evaluated with the PULSE H3 finite-resolution profile. Class groupings report only whether every mapped custom probe passed. They are descriptive coverage groups, not GeoSPARQL conformance-class claims or an OGC-issued certificate. Manual requirements remain manual rather than being silently counted as passes.
