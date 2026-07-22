# Standards projection contract

PULSE-S keeps its typed runtime model authoritative and emits standards-oriented
views for interchange and validation. The projections are deterministic views;
they are not claimed to be a lossless round trip or a replacement execution
semantics.

## Output bundle

`project_standards` and the `--emit-projections` CLI option produce two graphs:

| File | Contents |
|---|---|
| `*-data.ttl` | Asserted GeoSPARQL features, runtime state, and SOSA observations |
| `*-shapes.ttl` | Normative geofences represented as SHACL-SPARQL node shapes |

The default resource IRI root is
`https://w3id.org/pulse-spatial/resource`. The vocabulary IRI
`https://w3id.org/pulse-spatial/vocab#` is provisional during pre-alpha
development and must not yet be treated as a stable published ontology.
The provisional names `pulse:modality` and `pulse:Modality` are legacy RDF
labels for PULSE's operational role partition; they do not denote modal-logic
or deontic operators.

## Data graph mapping

| PULSE-S construct | RDF view |
|---|---|
| Region or asserted position | `geo:Feature`, `geo:hasGeometry`, `geo:asWKT` |
| Asserted geometry role | `pulse:modality pulse:Asserted` |
| Location observation | `sosa:Observation` |
| Observed entity | `sosa:hasFeatureOfInterest` |
| Spatial property | `sosa:Property` and `sosa:observedProperty` |
| Observation source | `sosa:madeBySensor` and `sosa:Sensor` |
| Observation time | `sosa:resultTime` with `xsd:dateTime` |
| Observed geometry | `sosa:hasResult` to a GeoSPARQL geometry |
| Evidence role | `pulse:modality pulse:Observed` |
| Confidence and accuracy | `pulse:confidence`, `pulse:accuracyMetres` |
| Runtime state | `pulse:state` |

The custom PULSE-S annotations are deliberate: a bare GeoSPARQL geometry does
not say whether it is an authoritative assertion or an observation, and SOSA
does not prescribe the application's confidence and metric-accuracy model.
The alpha language's single observation `at` field maps to `sosa:resultTime`;
it does not yet distinguish execution completion from `sosa:phenomenonTime`.

## Shapes graph mapping

Each geofence constraint becomes a `sh:NodeShape` targeting the constrained
instance. The SPARQL body reads the instance and region WKT literals and uses:

| PULSE-S predicate | GeoSPARQL function |
|---|---|
| `inside` | `geof:sfWithin` |
| `coveredBy` (Point/Polygon only) | `geof:sfIntersects` |

A `while` state guard becomes a `pulse:state` graph pattern, matching the
runtime rule that the constraint is inactive when the guarded state is absent
or different.

## Portability boundary

The generated shapes require SHACL-SPARQL plus GeoSPARQL query functions. A
SHACL Core processor without those functions cannot evaluate the spatial
filter. RDFLib tests verify the Turtle and SPARQL syntax. The optional reference
validator additionally executes the shapes using pySHACL and Shapely/GEOS
implementations of the two projected functions. This establishes a reproducible
cross-view parity check, not conformance of the adapter or language to the full
GeoSPARQL standard. See `reference-validation.md`.
