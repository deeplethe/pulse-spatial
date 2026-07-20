# PostGIS production-oriented concurrency benchmark

- Devices: 50,000
- Warm-up / measurement per level: 15 s / 60 s
- Crash recovery verified: **True**
- Acceptance passes: **True**

| Clients | Rep | TPS | p50 ms | p95 ms | p99 ms | failures |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 1902.20 | 0.335 | 1.377 | 1.733 | 0 |
| 1 | 2 | 1213.43 | 0.340 | 2.828 | 3.267 | 0 |
| 1 | 3 | 1494.42 | 0.335 | 2.651 | 3.080 | 0 |
| 4 | 1 | 4548.89 | 0.412 | 3.969 | 4.935 | 0 |
| 4 | 2 | 4883.35 | 0.414 | 3.395 | 4.846 | 0 |
| 4 | 3 | 4428.98 | 0.419 | 4.041 | 5.018 | 0 |
| 8 | 1 | 8308.86 | 0.471 | 3.856 | 5.052 | 0 |
| 8 | 2 | 6674.02 | 0.446 | 4.763 | 5.474 | 0 |
| 8 | 3 | 7568.95 | 0.467 | 4.445 | 5.277 | 0 |
| 16 | 1 | 11790.40 | 0.497 | 5.333 | 6.102 | 0 |
| 16 | 2 | 14287.78 | 0.534 | 4.208 | 5.502 | 0 |
| 16 | 3 | 12160.73 | 0.483 | 5.172 | 5.907 | 0 |
| 32 | 1 | 23167.65 | 0.671 | 4.567 | 6.196 | 0 |
| 32 | 2 | 19813.65 | 0.586 | 6.204 | 7.071 | 0 |
| 32 | 3 | 19877.66 | 0.593 | 6.170 | 7.085 | 0 |

## Three-run summary

| Clients | mean TPS | TPS CV | mean p99 ms | p99 range ms |
|---:|---:|---:|---:|---:|
| 1 | 1536.68 | 0.184 | 2.693 | 1.733--3.267 |
| 4 | 4620.40 | 0.042 | 4.933 | 4.846--5.018 |
| 8 | 7517.28 | 0.089 | 5.268 | 5.052--5.474 |
| 16 | 12746.31 | 0.086 | 5.837 | 5.502--6.102 |
| 32 | 20952.99 | 0.075 | 6.784 | 6.196--7.085 |

## Claim boundary

Durable single-node PostgreSQL/PostGIS mixed spatial workload using pgbench prepared statements, weighted reads/writes, per-transaction latency logs, GiST plan checks, and SIGKILL recovery. This is production-oriented evidence, not a claim of multi-node high availability, cloud SLA, or universal capacity independent of the reported host.
