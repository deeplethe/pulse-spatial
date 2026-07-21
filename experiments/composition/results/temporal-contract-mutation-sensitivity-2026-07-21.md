# Temporal contract mutation sensitivity

- PULSE matches exact oracle: **4/4**
- Reference workflow matches exact oracle: **4/4**
- Single-change mutants killed by the same oracle: **4/4**

| Obligation | Mutant | PULSE | Reference | Mutant killed | Changed fields |
|---|---|---:|---:|---:|---|
| inverseCancellation | M-CANCEL | True | True | True | finalState, sustainedTrace |
| timerBeforeMoveAtTie | M-ORDER | True | True | True | finalState, sustainedTrace |
| startGuard | M-START-GUARD | True | True | True | sustainedTrace |
| durationExactness | M-DURATION | True | True | True | finalState, sustainedTrace |

## Claim boundary

A mutation-sensitivity experiment over four selected temporal obligations. It establishes observable consequences and locates the corresponding PULSE runtime contracts. It does not compare usability, productivity, defect prevalence, or the expressive power of PULSE and standards-based workflows.
