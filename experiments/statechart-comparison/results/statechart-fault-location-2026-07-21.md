# RDF/SHACL + Sismic comparison

- Exact baseline outcome match: **True**
- PULSE prevented/detected: **4/4**
- Unprofiled composition detected only by outcome oracle: **4/4**
- Profiled composition prevented/detected: **4/4**

| Fault | PULSE | RDF+Sismic | Profiled RDF+Sismic |
|---|---|---|---|
| F-IDENTIFIER-DRIFT | compile | outcome-oracle | load-binding |
| F-EFFECT-DOMAIN | compile | outcome-oracle | statechart-invariant |
| F-SAMPLE-BEFORE-CLOCK | prevented-by-runtime-api | outcome-oracle | adapter-precondition |
| F-SCENARIO-ALIAS | prevented-by-scenario-runtime | source-state-oracle | prevented-by-clone-adapter |

## Claim boundary

One matched task and four deliberately injected integration faults. The result locates enforcement and shows that an explicit statechart profile can recover the checked obligations with extra binding, invariant, and adapter contracts. It is not a usability, maintenance, fault-prevalence, or language-superiority study.
