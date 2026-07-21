# Contract fault-localization probe

- PULSE contracts held: **4/4**
- Workflow mutants escaping unchanged RDF/SHACL validation: **4/4**
- Workflow mutants caught by external postcondition oracles: **4/4**

| Obligation | PULSE boundary | RDF/SHACL sees code mutant | External oracle |
|---|---|---:|---:|
| observationNonInterference | observation-recording boundary | False | True |
| scenarioIsolation | isolated scenario runtime | False | True |
| timerBeforeMoveAtTie | temporal step ordering | False | True |
| guardPreservation | transition guard at monitor start | False | True |

## Claim boundary

A mutation-based localization probe over four selected contract obligations. It shows which checked boundary owns each obligation; it does not establish defect prevalence, standards incapability, usability, productivity, or complete mutation coverage.
