# Point/Polygon boundary differential corpus

## Summary

- Topology cases: 17
- Topology mismatches: 0
- Rejection cases: 9
- Rejection mismatches: 0
- All checks pass: **True**

## Topology cases

| Case | Feature | Within | Boundary | Covered by | Match |
|---|---|---:|---:|---:|---:|
| square-interior | interior | True | False | True | True |
| square-exterior | exterior | False | False | False | True |
| horizontal-edge | boundary edge | False | True | True | True |
| vertical-edge | boundary edge | False | True | True | True |
| square-vertex | boundary vertex | False | True | True | True |
| near-boundary-inside | 1e-13 inside boundary | True | False | True | True |
| near-boundary-outside | 1e-13 outside boundary | False | False | False | True |
| concave-interior | concave interior | True | False | True | True |
| concave-notch | concave exterior | False | False | False | True |
| concave-horizontal-edge | concave boundary edge | False | True | True | True |
| concave-reflex-vertex | concave boundary vertex | False | True | True | True |
| reversed-ring | clockwise orientation | True | False | True | True |
| slanted-edge | non-axis-aligned boundary | False | True | True | True |
| tiny-polygon | 1e-9-scale interior | True | False | True | True |
| large-offset-grid | 1e9-offset local grid | True | False | True | True |
| thin-polygon | 1e-12-height interior | True | False | True | True |
| negative-coordinates | negative-coordinate interior | True | False | True | True |

## Explicit rejection cases

| Case | Rejected as expected | Error |
|---|---:|---|
| too-few-coordinates | True | Polygon shell requires at least four coordinates |
| open-shell | True | Polygon shell must be closed |
| mixed-shell-crs | True | Polygon coordinates must share one CRS |
| non-finite-coordinate | True | Point coordinates must be finite |
| missing-crs | True | Point CRS must be explicit |
| collinear-shell | True | Polygon shell cannot be collinear |
| self-intersecting-shell | True | Polygon shell must be simple |
| zero-length-edge | True | Polygon shell cannot contain zero-length edges |
| query-crs-mismatch | True | CRS mismatch: 'urn:pulse:test:grid' != 'http://www.opengis.net/def/crs/OGC/1.3/CRS84' |

## Claim boundary

Differential agreement with Shapely/GEOS for the checked-in, two-dimensional Point/simple-Polygon cases and explicit rejection contracts. This is not an OGC or GeoSPARQL conformance suite and does not cover holes, multipolygons, coordinate transformation, geodesic predicates, or antimeridian semantics.
