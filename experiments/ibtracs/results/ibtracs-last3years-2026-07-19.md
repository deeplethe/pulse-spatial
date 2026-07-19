# IBTrACS geofence parity result

Generated: `2026-07-19T02:48:14.001576+00:00`

## Dataset

- Source: NOAA IBTrACS v04r01 last3years list CSV
- DOI: `10.25921/82ty-9e16`
- SHA-256: `95199b7ef1e92e7e32f1681c27d197f8bed86afcaa0dc55adc3b2ea273037dce`
- Valid main-track rows: 13,784
- Normalized snapshot: `experiments/ibtracs/snapshots/ibtracs-last3years-main-2026-07-16.csv`
- Snapshot SHA-256: `6ee7ad5684598d250de0ecd099972ccd249d1e1a285920ba359aea6fb2d22b6c`

## Workload

- Tracks replayed: 223
- Points: 13,784
- Transitions: 13,561
- Event-bearing transitions: 38

## Result

- Exact parity: **True**
- Transition mismatches: 0
- Transition agreement: 100.000000%
- Event agreement: 100.000000%
- Internal events: `{'enters': 3, 'leaves': 35}`
- Reference events: `{'enters': 3, 'leaves': 35}`

## Timing

- Internal median: 0.093984 s
- GEOS median: 0.082853 s

## Environment

- Python: `3.12.3`
- Shapely: `2.1.2`
- GEOS: `3.13.1`

## Claim boundary

Feasibility and event-label parity for Point/Polygon geofences; not GeoSPARQL conformance, geodesic accuracy, prediction, or industrial performance.
