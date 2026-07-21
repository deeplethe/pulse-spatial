# Lean 4 mechanization

This directory contains proof-checked, reduced abstractions of selected PULSE
mechanisms. The transition Core, monitor lifecycle, and compiler modules are
not yet composed into a refinement of the complete Python runtime. They make
the following mechanisms explicit:

- authoritative positions versus append-only observations;
- logical-clock validation and atomic error outcomes;
- boundary-policy-parametric sampled entry/exit events;
- finite pending-monitor discharge;
- duration-qualified rule matching, opposite-crossing cancellation, and
  source-state-guarded monitor creation with exact deadlines;
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
The geometry predicate is an environment-supplied total Boolean function. The
mechanization therefore verifies properties of the reduced models, not
floating-point geometry, full surface parsing, ordered state updates, or the
composition of monitor reconciliation with Core moves. The compiler theorems
apply to the mechanized subset. Cross-implementation correspondence is
currently a byte-identical canonical-IR check for the executable paper model,
not a theorem about every Python compiler path.

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
