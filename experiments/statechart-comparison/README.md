# RDF/SHACL + Sismic comparison

This experiment implements the cold-chain duration policy twice:

1. as one PULSE model; and
2. as the unchanged RDF/SHACL input from the composition experiment plus an
   executable Sismic 1.6.11 statechart.

The baseline compares exact final state, instantaneous crossings, and sustained
event timestamps. Four single-site integration faults then locate identifier,
effect-domain, sample/clock-order, and scenario-isolation obligations across:

- PULSE's compiler/runtime;
- an unprofiled RDF + SHACL + statechart composition; and
- the same composition with an explicit binding check, state invariant, and
  adapter preconditions.

Run from the repository root after installing the `test` or `statechart` extra:

```console
python -m pulse_spatial.experiments.statechart_comparison \
  --require-complete \
  --output-json experiments/statechart-comparison/results/statechart-fault-location-2026-07-21.json \
  --output-markdown experiments/statechart-comparison/results/statechart-fault-location-2026-07-21.md
```

The experiment compares enforcement location on one matched task. It does not
measure usability, engineering effort, fault prevalence, or general language
superiority.
