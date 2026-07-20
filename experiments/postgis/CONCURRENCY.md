# Production-oriented concurrency protocol

The benchmark uses PostgreSQL's official `pgbench` client with prepared
statements and three weighted scripts: point membership (60%), GiST window scan
(20%), and durable position update plus event append (20%). PostgreSQL and
pgbench run in separate containers on one Docker network and physical host, so
their CPU and memory use are reported independently.

Every measured run rebuilds the same 50,000-device tables, recreates the GiST
and event indexes, analyzes them, and executes `CHECKPOINT` before warm-up. This
prevents event-table growth and fixed run order from confounding client/rate
comparisons. PostgreSQL retains `fsync`, `synchronous_commit`, and
`full_page_writes` at their durable defaults.

Each run records:

- complete per-transaction latency logs and per-script statistics;
- transaction failures, retries, skipped arrivals, and schedule lag;
- `pg_stat_database`, `pg_stat_wal`, `pg_stat_bgwriter`, and
  `pg_stat_checkpointer` counter deltas;
- separate database/load-generator CPU, memory, network, block I/O, and PID
  samples; and
- GiST plan use plus SIGKILL recovery checks.

## Closed-loop resource sweep

```bash
pulse-spatial-postgis-concurrency \
  --data path/to/ibtracs.since1980.list.v04r01.csv \
  --clients 32,64,96 \
  --warmup-seconds 5 \
  --duration-seconds 30 \
  --repetitions 1 \
  --require-acceptance
```

The reset-state run reaches 16,548.33, 22,159.08, and 24,683.86 TPS at 32,
64, and 96 clients, with p99 values of 8.086, 11.986, and 17.402 ms and no
transaction failures. At 96 clients the database consumes 13.71 CPU cores on
average, the separate generator consumes 4.79, and database memory peaks at
527.4 MiB. SIGKILL recovery takes 2.348 seconds and preserves rows, monotone
versions, valid indexes, GiST plan use, and a post-recovery mixed probe. See
[`postgis-resource-reset-sweep-since1980-2026-07-20.md`](results/postgis-resource-reset-sweep-since1980-2026-07-20.md).

## Open-loop SLO

The open-loop experiment uses pgbench's Poisson `--rate` scheduler. The
[PostgreSQL 18 pgbench documentation](https://www.postgresql.org/docs/18/pgbench.html)
states that throttled latency is measured from the scheduled start time and
therefore includes schedule lag. The benchmark enforces a 20 ms p99 on that
end-to-end value. `--latency-limit` is separately set to 100 ms: arrivals more
than 100 ms behind schedule are skipped rather than sent, and every repeat must
keep that skip rate at or below 0.1%. Every repeat must also have zero database
transaction failures.

```bash
pulse-spatial-postgis-slo \
  --data path/to/ibtracs.since1980.list.v04r01.csv \
  --rates 10000,12000,14000,16000,18000,19000,20000 \
  --clients 96 \
  --warmup-seconds 10 \
  --duration-seconds 60 \
  --repetitions 3 \
  --latency-limit-ms 20 \
  --admission-latency-limit-ms 100 \
  --maximum-skip-rate 0.001 \
  --require-valid
```

Across 18,864,158 completed transactions, 10,000 TPS is the conservative
contiguous repeated-window lower bound. Its three repeats have a worst p99 of
13.044 ms, maximum skip rate of 0.0576%, and zero database failures. 12,000 TPS
is the first failed target because two repeats slightly exceed the 0.1% skip
budget even though their p99 remains below 20 ms. Higher targets expose both
host variability and sustained schedule lag. See
[`postgis-slo-production-evidence-since1980-2026-07-20.md`](results/postgis-slo-production-evidence-since1980-2026-07-20.md).

The exploratory sweep observes up to 43,898.03 completed TPS, but it is not SLO
capacity. The earlier 20 ms admission experiment is retained as a different,
more aggressive load-shedding policy rather than overwritten.

## Claim boundary

These are durable, production-oriented, single-node measurements on Docker
Desktop/WSL2 with 24 logical CPUs and 16.3 GB assigned memory. They are not
multi-node high-availability evidence, a cloud SLA, or capacity portable to
other hosts. Resource sampling is out-of-band but not free; raw JSON records
the observed sampling interval as well as its target.
