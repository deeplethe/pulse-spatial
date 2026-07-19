# External Apache Jena GeoSPARQL agreement

This experiment evaluates a PULSE-projected CRS84 Point/Polygon graph with the
unmodified Apache Jena GeoSPARQL 6.1.0 query engine.  The containerized Java
harness is in `external/jena-geosparql` and imports no PULSE geometry code.

Protocol:

1. Select the 86 checked-in CRS84 topology cases.
2. Materialize every case point as an instance and every case polygon as a
   region in one GeoSPARQL graph.
3. Query the full 86 x 86 cross product with `geof:sfWithin`,
   `geof:sfIntersects`, `geof:sfDisjoint`, and `geof:sfTouches`.
4. Compare all 7,396 returned rows with PULSE strict-inside,
   boundary-inclusive membership, disjointness, and boundary results.
5. Report projection, container, RDF load, and query-materialization timings
   separately.

Run from the repository root:

```powershell
docker build --quiet -t pulse-jena-geosparql:6.1.0 external/jena-geosparql
python -m pulse_spatial.experiments.geosparql_external `
  --require-parity `
  --output-json experiments/geosparql-external/results/jena-topology.json `
  --output-markdown experiments/geosparql-external/results/jena-topology.md
```

This is a focused external-system agreement test, not an OGC conformance suite
and not a like-for-like throughput comparison between a native event runtime
and a triplestore.
