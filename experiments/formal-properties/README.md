# Bounded checks for the PULSE core metatheory

The general proofs are stated in `docs/formal-semantics.md`.  This experiment
adds executable support by exhaustively exploring every action sequence over a
finite abstraction with four point positions (outside west, boundary, inside,
outside east), one region, three states, immediate and sustained rules.

At depth four the experiment explores all 340 sequences twice and checks:

- deterministic outcomes;
- state, CRS, and monitor preservation;
- finite time advance;
- atomic failure for backward time and mixed CRS;
- observation non-interference; and
- scenario isolation.

Run:

```powershell
python -m pulse_spatial.experiments.formal_properties `
  --max-depth 4 `
  --output-json experiments/formal-properties/results/bounded-depth4.json `
  --output-markdown experiments/formal-properties/results/bounded-depth4.md
```

This is bounded exhaustive checking, not a substitute for the general proofs.
