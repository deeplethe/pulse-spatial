# Cross-view reference validation

PULSE-S has two independently exercised paths for normative geofences:

```text
typed world -> internal Point/Polygon predicates -> violations
typed world -> RDF + SHACL-SPARQL -> pySHACL + GEOS -> validation results
```

`validate_projection_parity` runs both paths and compares their conformance
flags and violation counts. A match is evidence that the projection preserves
the tested constraint behavior; it is not a proof of general semantic
equivalence.

## Reference backend

The optional `validation` dependency group contains pySHACL and Shapely. During
validation, PULSE-S temporarily registers two RDFLib SPARQL extension
functions:

| Function | GEOS-backed operation |
|---|---|
| `geof:sfWithin(a, b)` | `within(a, b)` |
| `geof:sfIntersects(a, b)` | `intersects(a, b)` |

The adapter accepts GeoSPARQL WKT literals, defaults omitted CRS identifiers to
CRS84, and rejects comparisons whose explicit CRS identifiers differ. Existing
RDFLib registrations for either function are preserved.

## Executable cases

The automated protocol currently checks:

| Case | Internal expectation | Projected expectation |
|---|---|---|
| Asserted point inside, observation outside | conform | conform |
| Asserted point outside | one violation | one result |
| Point on boundary with `inside` | violation | result |
| Point on boundary with `coveredBy` | conform | conform |
| Outside point while state guard is inactive | conform | conform |

The first case is particularly important: SOSA observation geometry must not be
selected as the authoritative GeoSPARQL geometry of the feature.

## Reproduction

```powershell
python -m pip install -e .[validation]
pulse-spatial examples\cold_chain_geofence.pulse --validate-projections
```

The JSON result reports `matches`, both conformance flags, internal violations,
the SHACL result count, and the textual validation report.

## Limits

- This adapter implements two functions, not the GeoSPARQL conformance classes.
- Shapely/GEOS evaluates planar coordinates and does not transform CRSs.
- RDFLib function registration is process-global, so the context is not meant
  for concurrent registration in multiple threads.
- Passing this protocol does not establish round-trip completeness, inference
  equivalence, temporal equivalence, or external server interoperability.
