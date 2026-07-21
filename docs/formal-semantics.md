# PULSE core calculus

Status: normative draft for the executable PULSE spatial-temporal kernel.

This document fixes the semantic contract against which the reference
implementation and experiments are tested.  It is deliberately a calculus of
the executable kernel, not of parsing, diagnostics, storage, or every future
surface-language construct.  A well-typed surface model is first resolved and
desugared to this core.

## 1. Static environment and domains

Let `I`, `R`, `K`, and `S_i` be finite sets of instance identifiers, region
identifiers, rule identifiers, and states declared for instance `i`.  Let
`G_c` be the domain of finite, valid geometries in coordinate reference system
`c`.  The supported executable geometry fragment is Point/Polygon.

The immutable environment is

```text
Γ = <crs, region, stateDomain, rule, sustained, constraint>
```

where:

- `crs(i)` and `crs(r)` give the declared CRS of an instance position and a
  region;
- `region(r) ∈ G_crs(r)` is a closed polygon;
- `stateDomain(i) = S_i` is non-empty;
- `rule` is a declaration-ordered finite sequence of guarded state rules;
- `sustained` is a finite map from unique names to positive-duration event
  specifications; and
- `constraint` is a finite sequence of normative predicates.

Primitive values are strings, booleans, finite integers/decimals, states, and
geometries.  The relevant judgments are:

```text
Γ ⊢ g : Geometry[c]
Γ ⊢ o : Observation[i, position]
Γ ⊢ a : Action
Γ ⊢ X ok
```

Spatial predicates are partial across CRSs.  No implicit transformation is
part of the core:

```text
Γ ⊢ point(i) : Point[c]    Γ ⊢ region(r) : Polygon[c]
-----------------------------------------------------  T-SPATIAL
Γ ⊢ coveredBy(point(i), region(r)) : Boolean
```

There is no corresponding rule when the two CRS indices differ.

## 2. Configurations, actions, and outcomes

A runtime configuration is

```text
X = <A, O, q, Q, t>
```

where `A : I ⇀ G` is authoritative asserted position, `O` is an append-only
sequence of observations, `q(i) ∈ S_i` is current state, `Q` is a finite map of
pending sustained-event monitors keyed by specification name, and `t` is an
offset-aware logical time.  A pending monitor is

```text
<name, event, subject, region, started, duration, rule?>
```

with `duration > 0` and deadline `started + duration`.

Core actions are:

```text
a ::= record(o)
    | move(i, g, t')
    | advance(t')
```

An outcome is either `ok(X', trace)` or `error(code, X)`.  Error outcomes
retain the input configuration; validation is therefore atomic.  Traces are
finite ordered sequences of instantaneous or sustained events.

Well-formedness `Γ ⊢ X ok` requires that all identifiers resolve, geometries
have their declared CRS, every `q(i)` belongs to `S_i`, observations are typed
and offset-aware, monitor names are unique, monitor subjects and regions
resolve, monitor durations are positive, and `t` is offset-aware.

## 3. Deterministic helper functions

The calculus uses total deterministic helpers on well-formed inputs:

- `due(Q,t')` returns monitors whose deadline is at most `t'`, sorted by the
  total key `(deadline,name)`; uniqueness of the name-keyed map makes ties
  unambiguous;
- `emit(X,due,t')` removes each due monitor, emits it with its semantic
  deadline and current emission time `t'`, and applies its attached rule only
  if the source state still matches;
- `membership(g,r)` is boundary-inclusive Point/Polygon membership;
- `cross(A,i,g)` enumerates regions in declaration order and returns `enters`
  or `leaves` when old and new sampled membership differ;
- `cancelStart(q,Q,events,t')` first cancels inverse monitors and then starts
  matching positive-duration monitors whose source-state guards hold in `q`, in
  declaration order; and
- `applyRules(q,events)` applies immediate rules in declaration order.  A
  later rule observes earlier state changes, and a source-state mismatch skips
  the rule.

The semantics is sample-and-hold.  It does not interpolate a segment between
accepted positions.  Consequently an outside-to-outside segment intersecting
a polygon emits no sampled crossing event.

## 4. Dynamic semantics

The main evaluation judgment is:

```text
Γ ⊢ <X,a> ⇓ outcome
```

Observation recording changes only the evidence component:

```text
Γ ⊢ o : Observation
---------------------------------------------------------------- RECORD
Γ ⊢ <<A,O,q,Q,t>, record(o)> ⇓ ok(<A,O·o,q,Q,t>, ε)
```

Time advance rejects backward time.  Otherwise it emits due monitors and then
sets the clock:

```text
t' ≥ t    D = due(Q,t')    emit(<A,O,q,Q,t>,D,t') = <A,O,q',Q',T>
---------------------------------------------------------------- ADVANCE
Γ ⊢ <<A,O,q,Q,t>, advance(t')> ⇓ ok(<A,O,q',Q',t'>, T)
```

A move performs every precondition check before mutation.  It then advances
time, derives crossings from the old and new accepted samples, commits the new
position, cancels/starts monitors, and applies immediate rules:

```text
t' ≥ t    Γ ⊢ g : Point[crs(i)]
Γ ⊢ <X,advance(t')> ⇓ ok(X0,Td)
E = cross(A0,i,g)
A1 = A0[i ↦ g]
Q1 = cancelStart(q0,Q0,E,t')
q1 = applyRules(q0,E)
---------------------------------------------------------------- MOVE
Γ ⊢ <X,move(i,g,t')> ⇓ ok(<A1,O0,q1,Q1,t'>, Td·E)
```

If no old position exists, `cross` returns the empty trace and the accepted
sample initializes `A(i)`.  When `t'=t`, `cross` still compares the previous
accepted sample with the new sample, so an equal-time move may emit a crossing
and cancel or start monitors even though no time elapses.  Timers already due
at `t` are emitted before the first equal-time move; multiple equal-time input
moves then follow caller order.

For any failed premise that is classified as a runtime validation error:

```text
validateΓ(X,a) = error(code)
---------------------------------------------------------------- ERROR
Γ ⊢ <X,a> ⇓ error(code,X)
```

## 5. Scenarios and the four modes

The authoritative mode is `A`; observed evidence is `O`; normative constraints
are immutable declarations in `Γ`; a hypothetical scenario is evaluated on a
deep clone.  Given a finite sequence of desugared assumption moves `as`:

```text
clone(X) = Xs    Γ ⊢ <Xs,as> ⇓* ok(Xs',T)
--------------------------------------------------------------- SCENARIO
Γ ⊢ scenario(X,as) ⇓ <Xs',T>       and the source X is unchanged
```

For an untimestamped surface scenario, `t0` is explicit when supplied and
otherwise is the latest observation timestamp (or the Unix epoch when there is
no observation). Assumption moves execute at `t0` in declaration order; `run d`
then executes `advance(t0+d)` before questions are answered. This advances the
discrete sample-and-hold clock and exposes due monitors; it does not introduce
continuous interpolation.

## 6. Projection relation

`πdata(X)` maps authoritative geometries to GeoSPARQL Feature/Geometry/WKT
resources, states to `pulse:state`, and each element of `O` to a distinct SOSA
Observation and Result.  `πshape(Γ)` maps supported normative predicates to
SHACL-SPARQL constraints using GeoSPARQL functions.  Hypothetical state is not
published unless explicitly requested.

Projection does not define execution.  For the supported CRS84 Point/Polygon
fragment, boundary-inclusive `coveredBy` is compared with GeoSPARQL Simple
Features `sfIntersects`, while strict `inside` is compared with `sfWithin`.
This mapping is deliberately fragment-specific: it relies on a Point subject
and Polygon region.  Boundary cases must be reported separately because the
relations intentionally differ.

## 7. Metatheory

The following statements are proof obligations for the long-paper version.
The implementation also exercises them through unit tests and bounded
exhaustive exploration; bounded exploration is supporting evidence, not a
general proof.

### Lemma 1 — helper functionality

For well-formed finite arguments, `due`, `emit`, `cross`, `cancelStart`, and
`applyRules` each return exactly one finite result.

*Proof sketch.* Each helper is a composition of finite map lookup, finite
declaration-order traversal, stable sorting by a total tuple key, and functional
replacement.  No helper contains a nondeterministic choice.

### Theorem 1 — preservation

If `Γ ⊢ X ok`, `Γ ⊢ a : Action`, and
`Γ ⊢ <X,a> ⇓ ok(X',T)`, then `Γ ⊢ X' ok`.

*Proof sketch.* By cases on `a`.  `record` appends an already typed
observation.  `advance` removes well-formed monitors and assigns only declared
rule targets.  `move` validates identifiers, time and CRS before assigning a
typed point; started monitors are drawn from `Γ`, inverse cancellation only
removes entries, and immediate rules assign declared targets.  All unchanged
components inherit their invariant from `X`.

### Theorem 2 — determinism

If `Γ ⊢ <X,a> ⇓ u1` and `Γ ⊢ <X,a> ⇓ u2`, then `u1 = u2`.

*Proof sketch.* Validation is functional.  In the successful cases, Lemma 1
fixes every intermediate result and all order-sensitive operations use explicit
orders.  The error rule preserves `X` and returns the unique validation code.

### Theorem 3 — observation non-interference

If `Γ ⊢ <X,record(o)> ⇓ ok(X',ε)`, then
`X'.A=X.A`, `X'.q=X.q`, `X'.Q=X.Q`, and `X'.t=X.t`.

*Proof.* Immediate from RECORD.

### Theorem 4 — scenario isolation

If `Γ ⊢ scenario(X,as) ⇓ <Xs',T>`, every component of source `X` is unchanged.

*Proof sketch.* SCENARIO evaluates only from `clone(X)`.  Core steps replace
or mutate containers reachable from the clone; the clone operation shares no
mutable container with `X`.

### Theorem 5 — finite time advance

For well-formed finite `Q` and `t' ≥ t`, `advance(t')` terminates and emits at
most `|Q|` sustained events.

*Proof.* `due(Q,t')` is finite.  `emit` removes exactly one distinct keyed
monitor per iteration and starts no monitor.

### Theorem 6 — atomic failure

If `Γ ⊢ <X,a> ⇓ error(code,Xe)`, then `Xe=X`.

*Proof.* Immediate from ERROR and the requirement that validation precedes
mutation.

### Conditional theorem 7 — projection adequacy

Assume a GeoSPARQL processor implements the standard interpretation of CRS84
WKT Point/Polygon literals and the selected relation.  For every supported
authoritative pair `(i,r)`, evaluating that relation over `πdata(X)` returns the
same Boolean as the corresponding PULSE predicate.

This theorem is conditional on the external processor and geometry model.  The
Apache Jena experiment tests the premise and conclusion over topology cases and
real trajectories; it does not turn implementation agreement into a proof of
GeoSPARQL conformance.

## 8. Mechanized safety kernel

`formal/lean` contains a Lean 4.30.0 model of the pure transition-safety
kernel. It represents authoritative positions, append-only observations,
logical time, sampled crossings, finite pending monitors, atomic outcomes, and
scenario execution. The following declarations are accepted by `lake build`
without `sorry` placeholders:

- `preservation`;
- `determinism`;
- `observation_noninterference`;
- `scenario_isolation`;
- `finite_advance`; and
- `atomic_failure`.

`PulseFormal.Monitors` additionally models duration-qualified rules over the
crossing events produced by the core. It proof-checks:

- `cancelled_not_in_cancelMatching` and
  `cancelMatching_member_not_cancelled`;
- `startFor_guard_holds`, `startFor_deadline_exact`, and `startFor_future`;
- `reconcile_future` and `reconcileAll_future`; and
- `reconcile_length_le` and `reconcileAll_length_le`.

Together these establish that an opposite crossing removes a matching pending
monitor, a matching trigger creates a monitor only when its source-state guard
holds, the monitor has the rule-defined deadline, positive durations keep
reconciled deadlines in the future, and a finite event batch can add no more
than `events.length * rules.length` monitors.

`PulseFormal.Compiler` adds a post-parse surface language and a deterministic
Core IR. It performs identifier resolution, duration-unit normalization, and
scenario desugaring. The checked declarations include:

- `compileRule_preserves_fields` and `compileRule_preserves_guard`;
- `compileRule_preserves_wellTyped` and `compileRule_deadline_exact`;
- `compileScenario_preserves_horizon` and
  `compileScenario_preserves_wellTyped`; and
- `compileScenario_simulates_execution`.

The last theorem relates surface scenario semantics to `Core.run` over the
generated move/advance action sequence. A Lean executable emits canonical IR
for Listing 1.1; a Python regression test compiles the actual `.pulse` file and
requires byte-identical IR. Thus the general preservation result is for the
mechanized subset, while the cross-implementation result currently covers the
paper model rather than every accepted Python program.

The mechanization is intentionally narrower than this normative draft. It
abstracts geometry as an environment-supplied total Boolean membership
function and does not yet encode the text parser, declaration-ordered state
updates, RDF projection, or a general refinement relation to every Python
compiler/runtime path. Consequently it checks the transition, monitor, and
paper-subset compilation disciplines; it is not a mechanized proof of the
floating-point geometry kernel or full-language refinement.

## 9. Claims intentionally excluded

The core does not claim continuous trajectory intersection, automatic CRS
transformation, probabilistic observation fusion, rule confluence, full
GeoSPARQL conformance, or equivalence between operational traces and arbitrary
RDF entailment regimes.  Declaration order is semantic, so confluence is not a
goal.
