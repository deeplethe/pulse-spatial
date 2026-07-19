# Apache Jena GeoSPARQL external agreement

## Summary

- External system: Apache Jena GeoSPARQL 6.1.0
- Points: 14
- Regions: 14
- Cross-product pairs: 196
- Returned rows: 196
- Boundary-focused intended pairs: 8
- Mismatches: **0**
- All checks pass: **True**

## Timing (seconds)

- PULSE projection: 0.000381
- Container process: 1.644546
- Jena initialization: 0.588836
- Jena RDF load: 0.144846
- Jena query materialization: 0.273854

## Claim boundary

Agreement with unmodified Apache Jena GeoSPARQL 6.1.0 for the checked-in CRS84 Point/Polygon graph using sfWithin and sfIntersects. This is not a complete GeoSPARQL conformance test, continuous-trajectory comparison, or like-for-like performance contest between a native event runtime and a triplestore.
