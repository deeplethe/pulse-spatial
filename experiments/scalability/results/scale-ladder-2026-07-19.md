# PULSE deterministic scale ladder

| Size | Moves/s | Ingest obs/s | Projection obs/s | RDF bytes | Peak allocated bytes |
|---:|---:|---:|---:|---:|---:|
| 1,000 | 105,238 | 150,734 | 23,847 | 799,961 | 1,806,846 |
| 10,000 | 127,570 | 158,694 | 24,545 | 7,995,464 | 18,014,547 |
| 100,000 | 101,849 | 104,941 | 17,342 | 80,220,467 | 180,448,825 |

## Claim boundary

Single-process deterministic scale ladder for one Point/Polygon geofence and append-only evidence projection. Tracemalloc reports Python-managed allocations, not total process RSS. Results are not a concurrency, distributed deployment, database, or industrial service-level benchmark.
