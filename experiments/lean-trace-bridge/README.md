# Generated Lean/Python observable-trace bridge

`TraceMain.lean` and the production Python runtime independently execute all 16
combinations of:

- initial sampled membership;
- membership at two successive moves; and
- presence or absence of a same-event immediate transition.

Every case also includes a duration-qualified departure rule and a final clock
advance. The bridge compares final state, live-monitor count, ordered event
kinds, effective times, and emission times.

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
