# Multizone duration-qualified trajectory experiment

This experiment extends the single-geofence IBTrACS replay in two directions:
five overlapping regions are evaluated on every transition, and every crossing
starts 6, 12, and 24-hour sustained-event monitors.

## Semantics

PULSE uses ordered event timestamps and sample-and-hold positions. A `leaves`
monitor means that the object remains outside after the crossing; an `enters`
monitor means that it remains inside. An inverse crossing before the deadline
cancels the pending monitor. A deadline coincident with a new observation fires
before that observation changes membership.

Each sustained event records:

- `started_at`: the boundary-crossing time;
- `effective_at`: the exact duration deadline;
- `emitted_at`: the sample or clock advance that exposed the due timer.

This distinction prevents sparse observations from being reported as exact
continuous detection times.

## Independent comparison

The PULSE path executes `TemporalSpatialRuntime`. The reference path separately
uses Shapely/GEOS `covers` for membership and an event-sweep implementation for
timer scheduling and cancellation. The experiment compares complete sorted
labels at three levels:

1. membership for every transition-zone pair;
2. instantaneous `enters` and `leaves` events;
3. sustained events including all three timestamps.

The five study polygons are frozen in the experiment source. They are
experiment-defined and are not official NOAA basin or warning boundaries.

## Recorded 2026-07-19 result

- 223 tracks and 13,784 points
- 13,561 transitions
- 67,805 transition-zone pairs
- 175 event and 67,630 non-event transition-zone pairs
- 96 tracks with at least one instantaneous event
- 525 sustained-monitor starts
- 475 sustained events
- 50 monitors not emitted because of an inverse crossing or track end
- 0 membership mismatches
- 0 instantaneous-event mismatches
- 0 sustained-event mismatches

The report disaggregates all membership, entry, exit, and sustained-event
counts by zone. Event pairs range from 7 in `SouthIndianStudyZone` to 78 in
`NorthernTropics`; sustained events range from 20 to 217. Thus the zero-error
total can be audited per zone rather than being inferred from an aggregate
dominated by non-events.

The result also reports the lag from `effective_at` to `emitted_at`. This is a
property of observation spacing, not geometry-engine performance, and makes
the uncertainty introduced by discrete sampling visible. Of the 475 emitted
events, 472 were exposed exactly at their deadline; the other three had a
maximum emission lag of one hour.

The recorded run uses the immutable IBTrACS snapshot documented in
[`../ibtracs/snapshots/PROVENANCE.md`](../ibtracs/snapshots/PROVENANCE.md).
Machine-readable and Markdown reports are in [`results/`](results/).

## Reproduce

```powershell
python -m pip install -e .[test]
pulse-spatial-spatiotemporal `
  --data experiments/ibtracs/snapshots/ibtracs-last3years-main-2026-07-16.csv `
  --repetitions 5 `
  --require-parity
```

## Claim boundary

The result supports exact parity for the declared discrete Point/Polygon,
sample-and-hold workload. It does not establish continuous-trajectory,
geodesic, coordinate-transformation, database-performance, or full GeoSPARQL
conformance claims.
