# Deterministic execution and projection scale ladder

The real-data experiments provide external validity but do not isolate scale.
This deterministic synthetic ladder measures three distinct operations at
1,000, 10,000, and 100,000 items:

1. alternating geofence moves and derived events;
2. append-only observation ingestion; and
3. SOSA/GeoSPARQL Turtle materialization.

Each execution scale receives one untimed warm-up and repeated timed runs.
Observation ingestion and projection are measured once under `tracemalloc` so
the report includes Python-managed peak allocations. The projected graph is
checked to contain exactly one SOSA Observation resource per input record.

Run:

```powershell
python -m pulse_spatial.experiments.scalability `
  --sizes 1000,10000,100000 `
  --repetitions 3 `
  --output-json experiments/scalability/results/scale-ladder.json `
  --output-markdown experiments/scalability/results/scale-ladder.md
```

This is a single-process component benchmark, not a database, concurrent
service, distributed deployment, or industrial service-level claim.
