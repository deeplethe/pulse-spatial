# PULSE core bounded metatheory check

## Exploration

- Maximum depth: 4
- Move-only traces: 340
- Executed move steps: 2504

## Property checks

- determinism: 340
- preservation: 2504
- finiteAdvance: 680
- atomicFailure: 2
- observationNonInterference: 4
- scenarioIsolation: 4
- Total checks: **3534**
- Failures: **0**

## Claim boundary

Exhaustive exploration of every move-only trace through the finite four-position abstraction up to depth 4. Record, advance, scenario, and invalid-action properties are checked separately. The result supports testing of proof assumptions but is not a general, machine-checked proof of the unbounded calculus.
