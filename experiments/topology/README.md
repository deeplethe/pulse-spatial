# Point/Polygon boundary differential corpus

This deterministic corpus probes the current dependency-free topology kernel
where implementation shortcuts most often change semantic outcomes: horizontal
and vertical edges, vertices, concave shells, clockwise rings, slanted edges,
points only `1e-13` from a boundary, `1e-9`-scale polygons, thin polygons, and
large-offset local grids. The expanded profile adds deterministic rectangle,
triangle, and concave-polygon cases under four CRS84 translations/scales,
bringing the valid corpus to 89 cases.

Each valid case evaluates three PULSE predicates (`within`, `onBoundary`, and
`coveredBy`) and compares the complete Boolean tuple with Shapely/GEOS. A
separate rejection set freezes diagnostics for open, collinear,
self-intersecting, zero-length, mixed-CRS, non-finite, and otherwise invalid
inputs. The corpus also guards the numeric policy: orientation uses a fast
binary64 determinant and exact-rational fallback near its rounding-error bound,
not a fixed coordinate-unit epsilon.

## Reproduce

```powershell
python -m pip install -e .[test]
pulse-spatial-topology-corpus `
  --require-parity `
  --output-json experiments/topology/results/topology-corpus-expanded-2026-07-20.json `
  --output-markdown experiments/topology/results/topology-corpus-expanded-2026-07-20.md
```

## Interpretation boundary

This is a project-defined differential regression corpus, not an OGC or
GeoSPARQL conformance suite. It covers two-dimensional Point/simple-Polygon
relations only. Polygon holes, multipolygons, coordinate transformations,
geodesic predicates, and antimeridian semantics remain outside the implemented
language slice.

The predicate names and boundary distinction align with the Simple Features
relation family reused by GeoSPARQL, but only an official test suite executed
against a complete implementation could support a standards-conformance claim:

- <https://docs.ogc.org/is/22-047r1/22-047r1.html>
- <https://www.ogc.org/standards/sfa/>

Machine-readable and rendered reports are checked into [`results/`](results/).
