# Real-track four-mode end-to-end protocol

This integration experiment uses the frozen NOAA IBTrACS snapshot and storm
track `2023251N16334` (MARGOT). It exercises one chain rather than separate
language slices:

1. each of 91 samples is recorded as source-qualified evidence;
2. recording alone is checked not to mutate the asserted position;
3. the runner explicitly accepts the sample through `move_at`;
4. sampled entry/exit and a six-hour departure monitor execute;
5. a guarded normative containment constraint is evaluated;
6. a hypothetical move executes on a clone; and
7. the final asserted/evidence graph and SHACL shape are parsed and validated
   with RDFLib, pySHACL, and the GEOS function adapter.

Run the frozen case with:

```powershell
python -m pulse_spatial.experiments.end_to_end `
  --output-json experiments/end-to-end/results/ibtracs-four-mode-2026-07-19.json `
  --output-markdown experiments/end-to-end/results/ibtracs-four-mode-2026-07-19.md `
  --require-all-checks
```

The executed trace contains 90 accepted moves, 91 evidence records, three
sampled entry/exit events, one duration-qualified event, one state transition,
two normative violations before guard deactivation, an isolated scenario, and
exact internal/SHACL agreement over 926 data triples and 6 shape triples. This
is an integration case, not a productivity or industrial-deployment study.
