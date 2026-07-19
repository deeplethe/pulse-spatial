# Apache Jena GeoSPARQL external baseline

This directory builds a pinned, separately implemented external comparison
using Apache Jena GeoSPARQL 6.1.0.  The Java harness contains no PULSE geometry
implementation.  It loads a PULSE-projected Turtle graph and evaluates
`geof:sfWithin` and `geof:sfIntersects`, returning SPARQL Results JSON.  For
the current Point/Polygon fragment, `sfIntersects` is the standards-level
realization of boundary-inclusive point membership.  The Egenhofer
`ehCoveredBy` relation is not equivalent for a strictly interior point.

Build the container:

```powershell
docker build -t pulse-jena-geosparql:6.1.0 external/jena-geosparql
```

Run it against a projection (replace the host path as needed):

```powershell
docker run --rm `
  -v "${PWD}/build:/data:ro" `
  pulse-jena-geosparql:6.1.0 /data/pulse-data.ttl
```

The Python experiment driver builds the image on request, creates an immutable
evaluation graph, invokes the container, parses its standards-format response,
and compares every returned Boolean with the PULSE kernel.  Container startup,
RDF load, and query timings are recorded separately from native execution.

The comparison establishes agreement for the tested Point/Polygon/CRS84
fragment.  It is neither a full GeoSPARQL conformance claim nor an assertion
that a native event runtime and a triplestore perform identical tasks.
