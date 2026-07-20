# Persistent PostGIS/GiST baseline

This experiment loads the selected IBTrACS tracks and five checked-in study
zones into PostgreSQL 18 with PostGIS 3.6.  Samples and regions are stored in a
Docker volume, indexed with GiST, queried with
`ST_Covers(region.geom, sample.geom)`, and then reopened after the database
container is replaced.  The restart check verifies that rows, geometries, and
the index survive.

The positive membership rows are converted to sampled entry/exit and
6/12/24-hour duration labels without calling PULSE geometry code.  All three
layers are compared against the PULSE runtime.

Run the frozen snapshot:

```text
pulse-spatial-postgis \
  --data experiments/ibtracs/snapshots/ibtracs-last3years-main-2026-07-16.csv \
  --require-parity
```

The default image is pinned to `postgis/postgis:18-3.6`.  The experiment does
not expose a database port and removes its temporary volume unless
`--keep-volume` is supplied.

Concurrency, open-loop arrival-rate SLO, and SIGKILL recovery are evaluated by
the separate but schema-compatible
[`production-oriented concurrency protocol`](CONCURRENCY.md). Keeping the
parity and systems protocols distinct prevents a fast indexed query from being
misreported as concurrent service capacity.
