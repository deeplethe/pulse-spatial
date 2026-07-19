# Snapshot provenance

## Source

- Dataset: NOAA International Best Track Archive for Climate Stewardship
  (IBTrACS), Version 4r01
- File: `ibtracs.last3years.list.v04r01.csv`
- Source URL: <https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.last3years.list.v04r01.csv>
- DOI: <https://doi.org/10.25921/82ty-9e16>
- Source directory last-modified date observed: 2026-07-16
- Accessed: 2026-07-19
- Raw size: 9,468,292 bytes
- Raw SHA-256: `95199b7ef1e92e7e32f1681c27d197f8bed86afcaa0dc55adc3b2ea273037dce`

## Deterministic normalization

The `pulse-spatial-ibtracs` loader selected rows whose `TRACK_TYPE` is `main`,
discarded the IBTrACS units row, rejected invalid coordinates or timestamps,
normalized longitude to `[-180, 180]`, removed exact duplicate points, and
sorted tracks by `SID` and points by timestamp/coordinate. It retained only:

`SID, SEASON, BASIN, NAME, ISO_TIME, LAT, LON, TRACK_TYPE`

The resulting snapshot is
`ibtracs-last3years-main-2026-07-16.csv`:

- Rows excluding header: 13,784
- Size: 891,190 bytes
- SHA-256: `6ee7ad5684598d250de0ecd099972ccd249d1e1a285920ba359aea6fb2d22b6c`

The experimental study polygon is not part of NOAA IBTrACS and is not an
official NOAA geographic boundary. NOAA does not endorse PULSE-S. Users of the
snapshot should cite the IBTrACS dataset and consult NOAA's current dataset
documentation and terms.
