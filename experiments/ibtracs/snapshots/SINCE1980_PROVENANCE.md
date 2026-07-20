# Pinned since-1980 source provenance

## Source bytes used by the reported experiment

- Dataset: NOAA International Best Track Archive for Climate Stewardship
  (IBTrACS), Version 4r01
- File: `ibtracs.since1980.list.v04r01.csv`
- Source URL: <https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.since1980.list.v04r01.csv>
- DOI: <https://doi.org/10.25921/82ty-9e16>
- Accessed: 2026-07-19
- Size: 142,982,689 bytes
- SHA-256: `9f3db13f92bdc47d49edcdec677e64bafe9f20c67529552a65a10882205bb7fe`

The upstream URL is a dataset-service location rather than an immutable
content-addressed object. Reproduction must therefore verify both byte size and
SHA-256 before accepting a download. `pulse-spatial-ibtracs
--expect-sha256 ...` fails closed when the current upstream bytes differ.

The repository does not redistribute the 143 MB source file. The
machine-readable result preserves its URL, DOI, byte size, digest, row filters,
time range, basin set, and replay counts. A future archival release should
attach the exact source bytes, subject to NOAA's distribution terms, under the
digest above.

## Count conventions

- 4,775 tracks are loaded after filtering to valid main-track rows.
- 4,768 tracks contain at least two accepted points and therefore contribute
  one or more replay transitions.
- Seven tracks contain one accepted point; they contribute to the 300,033 point
  total but cannot contribute a transition.
- The five-zone workload evaluates all 4,775 loaded tracks because its count is
  a dataset inventory; its 1,476,290 transition-zone pairs are
  `295,258 transitions x 5 zones`.
