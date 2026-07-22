# RDF/SHACL + Sismic comparison

- Exact baseline outcome match: **True**
- PULSE prevented/detected: **6/6**
- Unprofiled composition detected only by outcome oracle: **6/6**
- Profiled composition prevented/detected: **6/6**

| Fault | PULSE | RDF+Sismic | Profiled RDF+Sismic |
|---|---|---|---|
| F-IDENTIFIER-DRIFT | compile | outcome-oracle | load-binding |
| F-EFFECT-DOMAIN | compile | outcome-oracle | statechart-invariant |
| F-SAMPLE-BEFORE-CLOCK | prevented-by-runtime-api | outcome-oracle | adapter-precondition |
| F-SCENARIO-ALIAS | prevented-by-scenario-runtime | source-state-oracle | prevented-by-clone-adapter |
| F-OBSERVATION-OVERWRITE | record-api | source-state-oracle | role-adapter |
| F-MONITOR-START-GUARD | runtime-start-guard | outcome-oracle | adapter-precondition |

## Claim boundary

One matched task and six deliberately injected integration faults. The result locates enforcement and shows that an explicit statechart profile can recover the checked obligations with extra binding, invariant, and adapter contracts. It is not a usability, maintenance, fault-prevalence, or language-superiority study.
