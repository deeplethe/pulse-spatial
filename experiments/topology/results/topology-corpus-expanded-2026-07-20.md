# Point/Polygon boundary differential corpus

## Summary

- Topology cases: 89
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
| profile-rectangle-west-small-interior | rectangle; interior; scale 0.5 | True | False | True | True |
| profile-rectangle-west-small-exterior | rectangle; exterior; scale 0.5 | False | False | False | True |
| profile-rectangle-west-small-edge | rectangle; boundary edge; scale 0.5 | False | True | True | True |
| profile-rectangle-west-small-vertex | rectangle; boundary vertex; scale 0.5 | False | True | True | True |
| profile-rectangle-west-small-near-in | rectangle; near-boundary interior; scale 0.5 | True | False | True | True |
| profile-rectangle-west-small-near-out | rectangle; near-boundary exterior; scale 0.5 | False | False | False | True |
| profile-rectangle-west-interior | rectangle; interior; scale 1 | True | False | True | True |
| profile-rectangle-west-exterior | rectangle; exterior; scale 1 | False | False | False | True |
| profile-rectangle-west-edge | rectangle; boundary edge; scale 1 | False | True | True | True |
| profile-rectangle-west-vertex | rectangle; boundary vertex; scale 1 | False | True | True | True |
| profile-rectangle-west-near-in | rectangle; near-boundary interior; scale 1 | True | False | True | True |
| profile-rectangle-west-near-out | rectangle; near-boundary exterior; scale 1 | False | False | False | True |
| profile-rectangle-east-large-interior | rectangle; interior; scale 2 | True | False | True | True |
| profile-rectangle-east-large-exterior | rectangle; exterior; scale 2 | False | False | False | True |
| profile-rectangle-east-large-edge | rectangle; boundary edge; scale 2 | False | True | True | True |
| profile-rectangle-east-large-vertex | rectangle; boundary vertex; scale 2 | False | True | True | True |
| profile-rectangle-east-large-near-in | rectangle; near-boundary interior; scale 2 | True | False | True | True |
| profile-rectangle-east-large-near-out | rectangle; near-boundary exterior; scale 2 | False | False | False | True |
| profile-rectangle-east-tiny-interior | rectangle; interior; scale 0.25 | True | False | True | True |
| profile-rectangle-east-tiny-exterior | rectangle; exterior; scale 0.25 | False | False | False | True |
| profile-rectangle-east-tiny-edge | rectangle; boundary edge; scale 0.25 | False | True | True | True |
| profile-rectangle-east-tiny-vertex | rectangle; boundary vertex; scale 0.25 | False | True | True | True |
| profile-rectangle-east-tiny-near-in | rectangle; near-boundary interior; scale 0.25 | True | False | True | True |
| profile-rectangle-east-tiny-near-out | rectangle; near-boundary exterior; scale 0.25 | False | False | False | True |
| profile-triangle-west-small-interior | triangle; interior; scale 0.5 | True | False | True | True |
| profile-triangle-west-small-exterior | triangle; exterior; scale 0.5 | False | False | False | True |
| profile-triangle-west-small-edge | triangle; boundary edge; scale 0.5 | False | True | True | True |
| profile-triangle-west-small-vertex | triangle; boundary vertex; scale 0.5 | False | True | True | True |
| profile-triangle-west-small-near-in | triangle; near-boundary interior; scale 0.5 | True | False | True | True |
| profile-triangle-west-small-near-out | triangle; near-boundary exterior; scale 0.5 | False | False | False | True |
| profile-triangle-west-interior | triangle; interior; scale 1 | True | False | True | True |
| profile-triangle-west-exterior | triangle; exterior; scale 1 | False | False | False | True |
| profile-triangle-west-edge | triangle; boundary edge; scale 1 | False | True | True | True |
| profile-triangle-west-vertex | triangle; boundary vertex; scale 1 | False | True | True | True |
| profile-triangle-west-near-in | triangle; near-boundary interior; scale 1 | True | False | True | True |
| profile-triangle-west-near-out | triangle; near-boundary exterior; scale 1 | False | False | False | True |
| profile-triangle-east-large-interior | triangle; interior; scale 2 | True | False | True | True |
| profile-triangle-east-large-exterior | triangle; exterior; scale 2 | False | False | False | True |
| profile-triangle-east-large-edge | triangle; boundary edge; scale 2 | False | True | True | True |
| profile-triangle-east-large-vertex | triangle; boundary vertex; scale 2 | False | True | True | True |
| profile-triangle-east-large-near-in | triangle; near-boundary interior; scale 2 | True | False | True | True |
| profile-triangle-east-large-near-out | triangle; near-boundary exterior; scale 2 | False | False | False | True |
| profile-triangle-east-tiny-interior | triangle; interior; scale 0.25 | True | False | True | True |
| profile-triangle-east-tiny-exterior | triangle; exterior; scale 0.25 | False | False | False | True |
| profile-triangle-east-tiny-edge | triangle; boundary edge; scale 0.25 | False | True | True | True |
| profile-triangle-east-tiny-vertex | triangle; boundary vertex; scale 0.25 | False | True | True | True |
| profile-triangle-east-tiny-near-in | triangle; near-boundary interior; scale 0.25 | True | False | True | True |
| profile-triangle-east-tiny-near-out | triangle; near-boundary exterior; scale 0.25 | False | False | False | True |
| profile-concave-west-small-interior | concave; concave interior; scale 0.5 | True | False | True | True |
| profile-concave-west-small-notch | concave; concave exterior; scale 0.5 | False | False | False | True |
| profile-concave-west-small-edge | concave; concave boundary edge; scale 0.5 | False | True | True | True |
| profile-concave-west-small-reflex | concave; concave boundary vertex; scale 0.5 | False | True | True | True |
| profile-concave-west-small-outer-edge | concave; outer boundary edge; scale 0.5 | False | True | True | True |
| profile-concave-west-small-outer-vertex | concave; outer boundary vertex; scale 0.5 | False | True | True | True |
| profile-concave-west-interior | concave; concave interior; scale 1 | True | False | True | True |
| profile-concave-west-notch | concave; concave exterior; scale 1 | False | False | False | True |
| profile-concave-west-edge | concave; concave boundary edge; scale 1 | False | True | True | True |
| profile-concave-west-reflex | concave; concave boundary vertex; scale 1 | False | True | True | True |
| profile-concave-west-outer-edge | concave; outer boundary edge; scale 1 | False | True | True | True |
| profile-concave-west-outer-vertex | concave; outer boundary vertex; scale 1 | False | True | True | True |
| profile-concave-east-large-interior | concave; concave interior; scale 2 | True | False | True | True |
| profile-concave-east-large-notch | concave; concave exterior; scale 2 | False | False | False | True |
| profile-concave-east-large-edge | concave; concave boundary edge; scale 2 | False | True | True | True |
| profile-concave-east-large-reflex | concave; concave boundary vertex; scale 2 | False | True | True | True |
| profile-concave-east-large-outer-edge | concave; outer boundary edge; scale 2 | False | True | True | True |
| profile-concave-east-large-outer-vertex | concave; outer boundary vertex; scale 2 | False | True | True | True |
| profile-concave-east-tiny-interior | concave; concave interior; scale 0.25 | True | False | True | True |
| profile-concave-east-tiny-notch | concave; concave exterior; scale 0.25 | False | False | False | True |
| profile-concave-east-tiny-edge | concave; concave boundary edge; scale 0.25 | False | True | True | True |
| profile-concave-east-tiny-reflex | concave; concave boundary vertex; scale 0.25 | False | True | True | True |
| profile-concave-east-tiny-outer-edge | concave; outer boundary edge; scale 0.25 | False | True | True | True |
| profile-concave-east-tiny-outer-vertex | concave; outer boundary vertex; scale 0.25 | False | True | True | True |

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
