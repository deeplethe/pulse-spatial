# Generated Lean/Python observable-trace bridge

`TraceMain.lean` and the production Python runtime independently execute all 32
combinations of:

- initial sampled membership;
- membership at two successive moves; and
- presence or absence of a same-event immediate transition.
- presence or absence of a second subject/rule that creates an equal-deadline
  timer after the first rule, with a lexically earlier specification name.

Every case also includes a duration-qualified departure rule, same-time caller
ordering, and a final clock advance. The bridge compares both final states,
live-monitor count, ordered event subjects/kinds, effective times, and emission
times. Dual-rule cases force the runtime to reorder equal-deadline monitors by
unique specification name rather than insertion order.

Regenerate the Lean fixture from `formal/lean` with:

```console
lake exe pulse_traces > generated-integrated-traces.json
```

Then compare the production runtime from the repository root:

```console
pulse-spatial-lean-trace-bridge --require-exact
```

The result is exact correspondence over this declared finite Boolean grid. It
is not a general refinement theorem between the Lean and Python runtimes.
