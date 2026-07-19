# Standards map

PULSE-S reuses standards at projection and adapter boundaries. It does not
claim equivalence to or conformance with them in the pre-alpha kernel.

| Standard | Reused concern | PULSE-S-specific concern |
|---|---|---|
| GeoSPARQL 1.1 | Geometry literals, CRS identifiers, topological vocabulary | Modal status and transition execution |
| OWL-Time | Instants, intervals, temporal ordering | Discrete event timestamps, duration deadlines, and sample-and-hold execution |
| SOSA/SSN | Observation, feature of interest, result quality | Evidence does not overwrite assertions |
| OGC Moving Features | Time-varying geometry and trajectory exchange | Counterfactual trajectories and process effects |
| SensorThings API | Thing, Location, HistoricalLocation, Observation | Authoritative-model and scenario separation |
| IndoorGML | Navigable cells and adjacency | Process-aware indoor state changes |
| SHACL | RDF graph validation | Internal normative execution contract |

Current executable projections cover GeoSPARQL geometry, SOSA observation
records, and SHACL-SPARQL geofence constraints. PULSE-S-specific terms retain
modality, confidence, accuracy, and runtime state where the target standards do
not encode the language's distinction directly. See `projections.md` for the
precise mapping and execution boundary.

An optional reference adapter executes only `geof:sfWithin` and
`geof:ehCoveredBy` through GEOS and pySHACL. It is intentionally narrower than
a GeoSPARQL implementation and is used to detect cross-view semantic drift.

Authoritative references:

- https://www.ogc.org/standards/geosparql/
- https://www.w3.org/TR/owl-time/
- https://www.w3.org/TR/vocab-ssn-2023/
- https://docs.ogc.org/is/19-045r3/19-045r3.html
- https://docs.ogc.org/is/22-003r3/22-003r3.pdf
- https://docs.ogc.org/is/15-078r6/15-078r6.html
- https://www.ogc.org/standards/indoorgml/
