# PostGIS production-oriented concurrency benchmark

- Devices: 50,000
- Warm-up / measurement per level: 5 s / 30 s
- Crash recovery verified: **True**
- Acceptance passes: **True**

| Clients | Rep | TPS | p50 ms | p95 ms | p99 ms | failures |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 16548.33 | 0.974 | 6.490 | 8.086 | 0 |
| 64 | 1 | 22159.08 | 1.645 | 8.439 | 11.986 | 0 |
| 96 | 1 | 24683.86 | 2.152 | 11.686 | 17.402 | 0 |

## Cross-repetition summary

| Clients | mean TPS | TPS CV | mean p99 ms | p99 range ms |
|---:|---:|---:|---:|---:|
| 32 | 16548.33 | 0.000 | 8.086 | 8.086--8.086 |
| 64 | 22159.08 | 0.000 | 11.986 | 11.986--11.986 |
| 96 | 24683.86 | 0.000 | 17.402 | 17.402--17.402 |

## Separated-container resources

| Clients | DB CPU mean/max | generator CPU mean/max | DB memory max MiB | WAL MiB | block hit ratio |
|---:|---:|---:|---:|---:|---:|
| 32 | 909.8% / 1031.0% | 458.5% / 498.7% | 276.4 | 114.20 | 0.99919 |
| 64 | 1236.4% / 1334.1% | 484.5% / 508.0% | 413.7 | 92.77 | 1.00000 |
| 96 | 1371.0% / 1487.6% | 478.6% / 516.9% | 527.4 | 91.71 | 1.00000 |

## Claim boundary

Durable single-node PostgreSQL/PostGIS mixed spatial workload using pgbench prepared statements, weighted reads/writes, a separate load-generator container, per-transaction latency logs, PostgreSQL/WAL and container-resource telemetry, GiST plan checks, identical checkpointed state per measured run, and SIGKILL recovery. This is production-oriented evidence, not a claim of multi-node high availability, cloud SLA, or universal capacity independent of the reported host.
