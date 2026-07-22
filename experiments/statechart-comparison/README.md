# RDF/SHACL + Sismic comparison

This experiment implements the cold-chain duration policy twice:

1. as one PULSE model; and
2. as the unchanged RDF/SHACL input from the composition experiment plus an
   executable Sismic 1.6.11 statechart.

The baseline compares exact final state, instantaneous crossings, and sustained
event timestamps. Six single-site integration faults then locate identifier,
effect-domain, sample/clock-order, scenario-isolation, evidence-role, and
monitor-start-guard obligations across:

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

The six faults deliberately cover one case at each named contract site; they
were selected by the sole author and are not an empirical fault taxonomy. The
statechart, reference workflow, and adapters were also authored by the sole
author; separation means distinct code and execution paths, not independent
specification by another researcher.

The experiment compares enforcement location on one matched task. It does not
measure usability, engineering effort, fault prevalence, or general language
superiority.
