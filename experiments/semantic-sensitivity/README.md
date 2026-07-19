# Semantic policy sensitivity protocol

This experiment asks whether PULSE's declared modal, boundary, sampling, and
clock policies have observable consequences. It executes six constructed
counterexamples and compares the declared behavior with one explicit semantic
alternative per case:

1. boundary-inclusive `coveredBy` versus strict `within`;
2. observation non-overwrite versus implicit assertion replacement;
3. cloned scenarios versus shared-state scenarios;
4. inverse-event cancellation versus retaining stale monitors;
5. timer-before-move versus move-before-timer at one timestamp; and
6. sample-and-hold versus linearly interpolated segment contacts.

Run the frozen checks with:

```powershell
python -m pulse_spatial.experiments.semantic_sensitivity `
  --output-json experiments/semantic-sensitivity/results/semantic-sensitivity-2026-07-19.json `
  --output-markdown experiments/semantic-sensitivity/results/semantic-sensitivity-2026-07-19.md `
  --require-all-distinguished
```

All six alternatives change a modal state or event trace. This is a semantic
mutation-adequacy check: it shows that the contracts are testable and
consequential, not that the selected policy is universally preferable.
