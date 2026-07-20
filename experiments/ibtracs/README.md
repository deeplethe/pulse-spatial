# IBTrACS real-trajectory experiment

This experiment replays real tropical-cyclone tracks through the PULSE-S
Point/Polygon geofence runtime and compares every derived `enters` or `leaves`
label with an independent Shapely/GEOS `covers` implementation.

The primary evidence is the full-data run recorded in
[`results/ibtracs-last3years-2026-07-19.json`](results/ibtracs-last3years-2026-07-19.json).
The small `synthetic-format-fixture.csv` exists only for focused unit tests; it
is not the source of the reported empirical result. CI also replays the full
checked-in normalized snapshot on Python 3.11 and 3.12.

## Dataset and citation

The source is NOAA's International Best Track Archive for Climate Stewardship
(IBTrACS), version 4r01, `ibtracs.last3years.list.v04r01.csv`, accessed on
2026-07-19. The rolling source can change after each NOAA update, so the exact
input is identified by byte count and SHA-256 in the result file. A normalized
snapshot of the selected main-track fields is checked in for exact replay.

Please cite the dataset as:

> Gahtan, J., Knapp, K., Schreck, C., Diamond, H., Kossin, J., & Kruk, M.
> (2024). International Best Track Archive for Climate Stewardship (IBTrACS)
> Project, Version 4r01. NOAA National Centers for Environmental Information.
> https://doi.org/10.25921/82ty-9e16

See [`snapshots/PROVENANCE.md`](snapshots/PROVENANCE.md) for the exact
transformation and checksums. The checked-in study polygon is
experiment-defined and is not an official NOAA basin or warning boundary.

## Protocol

1. Read valid rows whose `TRACK_TYPE` is `main`.
2. Sort each storm by time and replay every consecutive position transition.
3. Derive `enters` and `leaves` with the PULSE-S runtime using CRS84 and
   boundary-inclusive `coveredBy` semantics.
4. Independently derive the same labels with Shapely/GEOS `covers`.
5. Compare the complete ordered transition-label trace, not only event counts.
6. Report median execution time across five repetitions as a local
   microbenchmark; it is not a database or industrial-performance benchmark.

The experiment-defined `NorthAtlanticStudyZone` polygon is frozen in
`src/pulse_spatial/experiments/ibtracs.py`. This version tests one polygon to
isolate topological event derivation; it does not test geodesic distance,
coordinate transformation, multiple simultaneous geofences, or full
GeoSPARQL conformance.

## Recorded result

The 2026-07-19 run loaded 223 tracks and 13,784 points from the 2023--2025
seasons, producing 13,561 transitions. Thirty-eight transitions carried an
event label (3 `enters`, 35 `leaves`). PULSE-S and GEOS agreed on every label:
0 mismatches and 100% exact transition agreement.

On the recorded Windows/Python 3.12 environment, the median runtime over five
repetitions was 0.093984 s for PULSE-S and 0.082853 s for the GEOS reference.
These timings establish that the experiment is executable; the scientific
claim is event-label parity for this Point/Polygon workload.

The larger `since1980` run is recorded separately in
`results/ibtracs-since1980-2026-07-19.*`. It covers 4,775 tracks, 300,033
loaded tracks and 295,258 transitions from 1980--2025 across seven basins.
Of those tracks, 4,768 contain at least two accepted points and are replayable;
the remaining seven single-point tracks contribute points but no transition.
All 571
event-bearing transitions match the GEOS path. The 143 MB official input is
identified by URL, DOI, and SHA-256 in the report and remains under ignored
`.data/`; it is not duplicated in the repository.

The pinned-byte run can be fetched only if the downloaded file still matches
the recorded digest:

```powershell
pulse-spatial-ibtracs `
  --data .data/ibtracs.since1980.list.v04r01.csv `
  --url https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.since1980.list.v04r01.csv `
  --download `
  --expect-sha256 9f3db13f92bdc47d49edcdec677e64bafe9f20c67529552a65a10882205bb7fe `
  --require-parity
```

Full byte-level provenance is recorded in
[`snapshots/SINCE1980_PROVENANCE.md`](snapshots/SINCE1980_PROVENANCE.md).

## Reproduce from the immutable snapshot

```powershell
python -m pip install -e .[test]
pulse-spatial-ibtracs `
  --data experiments/ibtracs/snapshots/ibtracs-last3years-main-2026-07-16.csv `
  --repetitions 5 `
  --require-parity
```

## Refresh from NOAA

This command downloads the current rolling file into the ignored `.data`
directory and writes new reports. Do not overwrite the recorded result unless
the new dataset hash and access date are also documented.

```powershell
pulse-spatial-ibtracs `
  --download `
  --repetitions 5 `
  --output-snapshot experiments/ibtracs/snapshots/ibtracs-main-current.csv `
  --output-json experiments/ibtracs/results/ibtracs-current.json `
  --output-markdown experiments/ibtracs/results/ibtracs-current.md `
  --require-parity
```
