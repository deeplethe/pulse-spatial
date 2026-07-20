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

## Shared topology cross-engine experiment

The command below loads the exact 86-point by 86-region CRS84 graph used by the
Apache Jena experiment and evaluates 7,396 pairs with `ST_Within`,
`ST_CoveredBy`, `ST_Disjoint`, and `ST_Touches`:

```text
pulse-spatial-postgis-topology --require-parity
```

The checked-in run returns all 7,396 rows with zero differences from the PULSE
kernel. Because Jena independently returns the same shared graph without
differences, this is a three-system semantic triangulation on one workload.
It is not a GeoSPARQL conformance certificate or a performance comparison.
