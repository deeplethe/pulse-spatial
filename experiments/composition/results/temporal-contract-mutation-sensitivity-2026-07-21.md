# Generated temporal mutation matrix

- Generated traces: **37,440**
- PULSE/reference exact matches: **37,440/37,440**
- Single-field mutation operators killed: **10/10**

| Mutant | Single semantic field | Distinguished traces | Killed | First witness |
|---|---|---:|---:|---|
| M-CANCEL | cancel_inverse_crossing | 1,680 | True | T03145 |
| M-ORDER | timer_before_sample | 3,896 | True | T00393 |
| M-START-GUARD | require_start_guard | 8,304 | True | T00331 |
| M-DEADLINE-GUARD | require_deadline_guard | 3,832 | True | T00330 |
| M-STRICT-DEADLINE | inclusive_deadline | 3,424 | True | T00329 |
| M-DURATION-SHORT | duration_scale | 10,224 | True | T00325 |
| M-DURATION-LONG | duration_scale | 7,792 | True | T00329 |
| M-EMISSION-TIME | deadline_as_emission_time | 4,368 | True | T00333 |
| M-TRANSITION-ON-START | transition_on_start | 11,024 | True | T00033 |
| M-POSTSTATE-START | monitor_after_immediate_rule | 3,832 | True | T00330 |

## Claim boundary

Exhaustive mutation sensitivity only over the declared finite trace grid and ten single-field operators. It does not establish general correctness, real-world defect prevalence, usability, productivity, or expressive superiority over standards-based workflows.
