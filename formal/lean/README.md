# Lean 4 mechanization

This directory contains a proof-checked executable abstraction of the PULSE
paper subset. `PulseFormal.Integrated` now composes the transition Core,
monitor lifecycle, compiled duration rules, deadline-guarded state updates,
and declaration-ordered immediate rules in one `integratedRun`. The model makes
the following mechanisms explicit:

- authoritative positions versus append-only observations;
- logical-clock validation and atomic error outcomes;
- boundary-policy-parametric sampled entry/exit events;
- finite pending-monitor discharge;
- duration-qualified rule matching, opposite-crossing cancellation, and
  source-state-guarded monitor creation with exact deadlines;
- timer-before-move execution, deadline guard rechecking, monitor
  reconciliation against the pre-immediate state, and ordered immediate
  state updates;
- pure scenario execution; and
- the `record`, `move`, and `advance` core actions.

`PulseFormal.Compiler` lowers a post-parse surface subset to the reduced Core. It
resolves symbolic identifiers, converts seconds/minutes/hours to seconds,
compiles duration rules, and lowers Point-valued scenario assumptions plus a
horizon to `move`/`advance` actions. Lean proves trigger, guard, duration,
deadline, horizon, well-typedness, and scenario-desugaring preservation.

Lean checks preservation, deterministic evaluation, observation
non-interference, scenario isolation, finite time advance, and atomic failure.
For duration-qualified rules it additionally checks that cancelled monitors are
removed, retained monitors preserve future deadlines, every newly started
monitor has a satisfied source-state guard and the exact rule-defined deadline,
positive durations keep all deadlines in the future, and a batch of crossing
events can grow the pending set by at most `events.length * rules.length`.
The integrated module additionally checks atomic time/CRS failures, timer-event
trace order, finite advance, compilation into the integrated environment, and
a concrete same-event regression in which the duration monitor is created from
the pre-immediate state before an immediate transition changes that state.

The geometry predicate remains an environment-supplied total Boolean function,
and the mechanized compiler begins after parsing. The mechanization therefore
does not prove floating-point geometry, full surface parsing, the production
Python implementation, or a general refinement theorem between Lean and every
runtime path. Cross-implementation correspondence is a byte-identical
canonical-IR check for the executable paper model plus the generated mutation
corpus, not a universal compiler-correctness result.

The toolchain is pinned to Lean 4.30.0.  Build locally with an installed Lean
toolchain:

```text
lake build
```

or from this directory with Docker:

```text
docker build --tag pulse-lean:4.30.0 .
docker run --rm pulse-lean:4.30.0
```

Regenerate the canonical paper IR with:

```text
lake exe pulse_ir
```

CI compares that output with `paper-cold-chain-ir.json`; the Python suite
independently compiles `examples/paper_cold_chain_st.pulse` to the same bytes.
