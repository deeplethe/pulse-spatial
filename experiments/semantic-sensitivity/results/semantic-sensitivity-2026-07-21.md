# Semantic policy sensitivity

- Policies checked: 6
- Alternatives changing an observable outcome: 6

| Policy | PULSE | Alternative | Distinguishable |
|---|---|---|---:|
| boundary-inclusion | sampled events=0 | sampled leaves=1 | True |
| observation-non-overwrite | assertedInside=true | assertedInside=false | True |
| scenario-isolation | source=Safe,scenario=AtRisk | source=AtRisk | True |
| inverse-cancellation | sustained events=0 | sustained events=1 | True |
| deadline-ordering | sustained events=1 | sustained events=0 | True |
| sample-and-hold | sampled events=0 | boundary contacts=2 | True |

## Claim boundary

Constructed sensitivity cases show that six declared policies change observable traces or modal state. They are mutation-adequacy checks, not evidence that each PULSE policy is universally preferable.
