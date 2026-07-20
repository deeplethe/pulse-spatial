# PULSE GeoSPARQL 1.1 geometry profile

The PULSE non-DGGS geometry profile supports WKT, GML, GeoJSON, and KML
geometry literals in the scope exercised by the repository's GeoSPARQL 1.1
conformance matrix. The implementation is an adapter over Apache Jena
GeoSPARQL 6.1.0 and JTS 1.20.0. The PULSE functions are registered separately
and are enabled only by the `--geometry-profile` harness option.

## GML profile

The documented GML profile is **GML 3.2.1**. `geof:asGML` accepts the profile
string `GML 3.2.1` and emits geometry elements in the
`http://www.opengis.net/gml/3.2` namespace with an explicit `srsName`.

## Declared numerical choices

- `geof:concaveHull` uses JTS maximum-edge-length-ratio concave hulls with a
  default ratio of 0.5. `geof:aggConcaveHull` uses its supplied ratio.
- `geof:boundingCircle` and `geof:aggBoundingCircle` use the JTS minimum
  bounding circle algorithm and return its polygonal approximation.
- Metric buffers over geographic coordinates use a centroid-anchored local
  equirectangular conversion: 111,320 metres per longitude degree adjusted by
  cosine latitude, and 110,574 metres per latitude degree. This is a local
  approximation, not a geodesic buffer, and must not be used for large extents
  or polar geometries.
- Spatial aggregates transform input geometries to the SRS of the first bound
  input and return WKT in that SRS.

This document is implementation evidence for GeoSPARQL 1.1 Requirement 22. It
does not constitute an OGC-issued certificate.

## H3 DGGS profile

The optional DGGS profile identifies H3 with `https://h3geo.org/` and uses
valid H3 4.4.0 indexes at a common resolution. Its lexical forms are:

```text
<https://h3geo.org/> CELL (8928308280fffff)
<https://h3geo.org/> CELLS (8928308280fffff 8928308280bffff)
```

An empty string denotes an empty geometry as required by GeoSPARQL 1.1. The
spatial meaning of a non-empty literal is the polygonal union of its addressed
H3 cells. Geometry-valued functions cover the result with H3 cells at the
input resolution using H3 centre containment; points and lines map to their
containing/touched cells. Operations reject mixed-resolution operands and
aggregates. `geof:asDGGS` uses resolution 9 unless the input is already an H3
literal, and `geof:transform` supports the identity H3 target.

H3 is two-dimensional, so `minZ` and `maxZ` return the profile's declared
surface value `0`. Metric operations use a local equirectangular frame centred
on the operand and are therefore bounded approximations rather than ellipsoidal
geodesics. The executable ATS refinements test this declared finite-resolution
semantics; they are not an OGC certification.
