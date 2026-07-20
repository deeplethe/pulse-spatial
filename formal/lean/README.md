# Lean 4 mechanization

This directory contains a proof-checked abstraction of the executable PULSE
kernel.  It makes the following mechanisms explicit:

- authoritative positions versus append-only observations;
- logical-clock validation and atomic error outcomes;
- boundary-policy-parametric sampled entry/exit events;
- finite pending-monitor discharge;
- duration-qualified rule matching, opposite-crossing cancellation, and
  monitor creation with exact deadlines;
- pure scenario execution; and
- the `record`, `move`, and `advance` core actions.

Lean checks preservation, deterministic evaluation, observation
non-interference, scenario isolation, finite time advance, and atomic failure.
For duration-qualified rules it additionally checks that cancelled monitors are
removed, retained monitors preserve future deadlines, newly started monitors
have the exact rule-defined deadline, positive durations keep all deadlines in
the future, and a batch of crossing events can grow the pending set by at most
`events.length * rules.length`.
The geometry predicate is an environment-supplied total Boolean function.  The
mechanization therefore verifies the transition discipline, not floating-point
computational geometry or full surface-language parsing.

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
