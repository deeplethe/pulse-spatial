# PostGIS shared topology external agreement

## Summary

- External system: PostgreSQL/PostGIS
- Points: 86
- Regions: 86
- Shared cross-product pairs: 7396
- Returned rows: 7396
- Boundary self-pairs: 38
- Mismatches: **0**
- All checks pass: **True**

## Timing (seconds)

- imagePull: cached
- inputSerialization: 0.008336300030350685
- databaseStartup: 5.788337599951774
- databaseLoadAndIndex: 0.342875299975276
- crossProductQuery: 0.6580430999747477

## Claim boundary

Agreement with PostgreSQL/PostGIS ST_Within, ST_CoveredBy, ST_Disjoint, and ST_Touches on the exact 7,396 CRS84 Point/Polygon pairs used by the Apache Jena baseline. This is a shared semantic workload, not an OGC conformance certificate, geodesic test, or performance contest.
