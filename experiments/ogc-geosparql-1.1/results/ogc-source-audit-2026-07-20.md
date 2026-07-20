# OGC GeoSPARQL 1.1 official-source audit

## Audited inventory counts

- Researcher-transcribed Annex A manifest: 7 classes, 55 test allocations
- Official requirements register: 58 `spec:ConformanceTest` resources
- Official service description: 52 `sd:feature` resources
- Annex allocations corroborated by local-name crosswalk: 55/55
- Version-ambiguous inherited names: 4

## Cross-source divergences retained by the audit

- registerTestsNotSelectedByAnnexNameCrosswalk: 1
  - `http://www.opengis.net/spec/geosparql/1.1/conf/geometry-extension/query-functions-non-sf`
- serviceFeaturesNotTypedAsConformanceTests: 2
  - `http://www.opengis.net/spec/geosparql/1.1/conf/core/spatial-object-class`
  - `http://www.opengis.net/spec/geosparql/1.1/conf/geometry-extension/dggs-literal-srs`
- conformanceTestsNotListedAsServiceFeatures: 8
  - `http://www.opengis.net/spec/geosparql/1.0/conf/core/sparql-protocol`
  - `http://www.opengis.net/spec/geosparql/1.0/conf/rdfs-entailment-extension/bgp-rdfs-ent`
  - `http://www.opengis.net/spec/geosparql/1.0/conf/rdfs-entailment-extension/gml-geometry-types`
  - `http://www.opengis.net/spec/geosparql/1.0/conf/rdfs-entailment-extension/wkt-geometry-types`
  - `http://www.opengis.net/spec/geosparql/1.0/conf/topology-extension/eh-spatial-relations`
  - `http://www.opengis.net/spec/geosparql/1.0/conf/topology-extension/rcc8-spatial-relations`
  - `http://www.opengis.net/spec/geosparql/1.0/conf/topology-extension/sf-spatial-relations`
  - `http://www.opengis.net/spec/geosparql/1.1/conf/core/geometry-collection-class`

## Integrity checks

- PASS — pinnedFileHashesMatch
- PASS — manifestHasSevenClassesAnd55UniqueAllocations
- PASS — allAnnexAllocationsHaveRegisterCandidates
- PASS — registerShapeMatchesPinnedSource
- PASS — serviceDescriptionShapeMatchesPinnedSource

Overall audit: **PASS**

## Claim boundary

Passing this audit establishes integrity of the two pinned official RDF files and explicit accounting against a researcher-authored Annex A manifest transcription. It does not independently parse Annex A, execute an OGC ETS, or establish GeoSPARQL conformance.
