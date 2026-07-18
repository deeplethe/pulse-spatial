# Standards map

PULSE-S reuses standards at projection and adapter boundaries. It does not
claim equivalence to or conformance with them in the pre-alpha kernel.

| Standard | Reused concern | PULSE-S-specific concern |
|---|---|---|
| GeoSPARQL 1.1 | Geometry literals, CRS identifiers, topological vocabulary | Modal status and transition execution |
| OWL-Time | Instants, intervals, temporal ordering | Runtime duration and step semantics |
| SOSA/SSN | Observation, feature of interest, result quality | Evidence does not overwrite assertions |
| OGC Moving Features | Time-varying geometry and trajectory exchange | Counterfactual trajectories and process effects |
| SensorThings API | Thing, Location, HistoricalLocation, Observation | Authoritative-model and scenario separation |
| IndoorGML | Navigable cells and adjacency | Process-aware indoor state changes |
| SHACL | RDF graph validation | Internal normative execution contract |

Authoritative references:

- https://www.ogc.org/standards/geosparql/
- https://www.w3.org/TR/owl-time/
- https://www.w3.org/TR/vocab-ssn-2023/
- https://docs.ogc.org/is/22-003r3/22-003r3.pdf
- https://docs.ogc.org/is/15-078r6/15-078r6.html
- https://www.ogc.org/standards/indoorgml/
