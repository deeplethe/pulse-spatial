# Apache Jena GeoSPARQL external agreement

## Summary

- External system: Apache Jena GeoSPARQL 6.1.0
- Points: 86
- Regions: 86
- Cross-product pairs: 7396
- Returned rows: 7396
- Boundary-focused intended pairs: 56
- Mismatches: **0**
- All checks pass: **True**

## Timing (seconds)

- PULSE projection: 0.001176
- Container process: 2.195471
- Jena initialization: 0.536272
- Jena RDF load: 0.165584
- Jena query materialization: 0.614241

## Claim boundary

Agreement with unmodified Apache Jena GeoSPARQL 6.1.0 for the checked-in CRS84 Point/Polygon graph using sfWithin, sfIntersects, sfDisjoint, and sfTouches. This is not a complete GeoSPARQL conformance test, continuous-trajectory comparison, or like-for-like performance contest between a native event runtime and a triplestore.
