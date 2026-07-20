# Production-oriented concurrency protocol

The concurrent baseline uses PostgreSQL's official `pgbench` client with
prepared statements and three weighted scripts: point membership (60%), GiST
window scan (20%), and durable position update plus event append (20%).  Each
client level has a distinct warm-up and measurement interval.  Per-transaction
logs yield p50, p95, p99, maximum latency, failures, retries, and per-script
breakdowns in addition to pgbench TPS.

The database retains `fsync`, `synchronous_commit`, and `full_page_writes` at
their durable defaults.  The acceptance protocol also verifies the GiST query
plan and sends `SIGKILL` during a concurrent write workload, restarts the same
volume, checks row and version monotonicity plus index validity, and executes a
post-recovery mixed probe.

Closed-loop scaling and recovery run:

```bash
pulse-spatial-postgis-concurrency \
  --data path/to/ibtracs.since1980.list.v04r01.csv \
  --clients 1,4,8,16,32 \
  --warmup-seconds 15 \
  --duration-seconds 60 \
  --repetitions 3 \
  --require-acceptance
```

The open-loop experiment uses pgbench's Poisson `--rate` scheduler. A target
passes only if every repeat has zero database transaction failures, completion
p99 at or below 20 ms, and skipped arrivals at or below 0.1%. Skipped arrivals
are admission/scheduling misses, not silently relabelled database failures.

```bash
pulse-spatial-postgis-slo \
  --data path/to/ibtracs.since1980.list.v04r01.csv \
  --rates 5000,7500,10000,15000,20000 \
  --clients 32 \
  --warmup-seconds 15 \
  --duration-seconds 60 \
  --repetitions 3 \
  --latency-limit-ms 20 \
  --maximum-skip-rate 0.001 \
  --require-valid
```

The checked-in evidence deliberately uses the contiguous passing prefix rather
than the highest isolated passing target. The combined report records a 5,000
TPS conservative lower bound, a first failed target of 5,500 TPS, 14,801,450
completed transactions in the repeated-window sweep, and separate five-minute
checks at 6,500 and 7,000 TPS. The exploratory run reaches 25,166.22 completed
TPS under a 30,000 TPS target, but that saturated point violates the declared
SLO and is not capacity. See
[`postgis-slo-evidence-since1980-2026-07-20.md`](results/postgis-slo-evidence-since1980-2026-07-20.md).

The closed-loop result reports zero failures/retries at every 1--32-client
level, 20,952.99 mean TPS and 6.784 ms mean p99 at 32 clients, and verified
SIGKILL recovery in 8.448 seconds. See
[`postgis-concurrency-since1980-2026-07-20.md`](results/postgis-concurrency-since1980-2026-07-20.md).

The protocol is production-oriented but remains a single-node local-container
experiment.  It is not a multi-node availability or cloud-SLA certification.
