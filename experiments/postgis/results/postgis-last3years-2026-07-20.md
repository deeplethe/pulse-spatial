# Persistent PostGIS/GiST baseline

- Tracks / points: 223 / 13,784
- Transition-zone pairs: 67,805
- Positive membership rows: 17,017
- Query plan uses samples GiST: **True**
- Persistent restart verified: **True**
- Membership mismatches: 0
- Instantaneous-event mismatches: 0
- Sustained-event mismatches: 0
- All layers match: **True**
- Indexed membership query: 0.185511 s

## Claim boundary

Persistent PostgreSQL/PostGIS geometry baseline using an on-disk Docker volume, GiST indexes, and ST_Covers for the five experiment-defined Polygon zones. Event and duration labels are derived from returned sampled memberships. This is not a concurrent service benchmark, continuous-trajectory evaluation, or comparison with an RDF triplestore.
