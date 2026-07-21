/-
Copyright 2026 PULSE contributors.
Licensed under the Apache License, Version 2.0.

Integrated executable kernel for the paper subset.  This module composes the
Core clock and crossing semantics with duration-monitor reconciliation,
deadline-guarded state transitions, and declaration-ordered immediate rules.
In particular, a move fires due timers first, reconciles monitors against the
pre-immediate state, and only then applies same-event immediate rules.
-/

import PulseFormal.Compiler

namespace PulseFormal

structure ImmediateRule where
  name : Id
  trigger : EventKind
  subject : Id
  region : Id
  fromState : Id
  toState : Id
  deriving DecidableEq, Repr

structure IntegratedEnv where
  core : Env
  durationRules : List DurationRule
  immediateRules : List ImmediateRule

def IntegratedEnv.WellFormed (env : IntegratedEnv) : Prop :=
  (∀ rule ∈ env.durationRules,
    0 < rule.duration ∧ rule.fromState ≠ rule.toState) ∧
  (∀ rule ∈ env.immediateRules, rule.fromState ≠ rule.toState) ∧
  (env.durationRules.map (·.name) ++
    env.immediateRules.map (·.name)).Nodup

structure IntegratedConfig where
  core : Config
  states : RuleState

def IntegratedConfig.WellFormed
    (env : IntegratedEnv) (x : IntegratedConfig) : Prop :=
  ∀ monitor ∈ x.core.pending,
    ∃ rule ∈ env.durationRules,
      rule.name = monitor.name ∧ rule.subject = monitor.subject ∧
      rule.region = monitor.region ∧ x.core.clock < monitor.deadline

inductive IntegratedOutcome where
  | ok (config : IntegratedConfig) (trace : List Event)
  | error (code : Error) (source : IntegratedConfig)

def updateRuleState
    (state : RuleState) (subject value : Id) : RuleState :=
  fun candidate => if candidate = subject then value else state candidate

def durationRuleFor : List DurationRule -> Id -> Option DurationRule
  | [], _ => none
  | rule :: rest, name =>
      if rule.name = name then some rule else durationRuleFor rest name

def applyDueMonitor
    (state : RuleState) (rules : List DurationRule) (monitor : Monitor) :
    RuleState :=
  match durationRuleFor rules monitor.name with
  | none => state
  | some rule =>
      if state rule.subject = rule.fromState then
        updateRuleState state rule.subject rule.toState
      else
        state

def applyDueMonitors
    (state : RuleState) (rules : List DurationRule)
    (monitors : List Monitor) : RuleState :=
  monitors.foldl (fun current monitor => applyDueMonitor current rules monitor) state

def immediateMatches (rule : ImmediateRule) (event : Event) : Bool :=
  event.kind == rule.trigger &&
  event.subject == rule.subject &&
  event.region == rule.region

def applyImmediateRule
    (state : RuleState) (events : List Event) (rule : ImmediateRule) :
    RuleState :=
  if state rule.subject = rule.fromState then
    if events.any (immediateMatches rule) then
      updateRuleState state rule.subject rule.toState
    else
      state
  else
    state

def applyImmediateRules
    (state : RuleState) (rules : List ImmediateRule) (events : List Event) :
    RuleState :=
  rules.foldl (fun current rule => applyImmediateRule current events rule) state

def stateAfterDue
    (state : RuleState) (rules : List DurationRule)
    (pending : List Monitor) (time : Time) : RuleState :=
  applyDueMonitors state rules (due pending time)

def crossingsAt
    (env : IntegratedEnv) (x : IntegratedConfig) (subject : Id)
    (position : Position) (time : Time) : List Event :=
  crossingEvents env.core x.core.asserted subject position time

def pendingAfterMove
    (env : IntegratedEnv) (x : IntegratedConfig) (subject : Id)
    (position : Position) (time : Time) : List Monitor :=
  let preImmediate :=
    stateAfterDue x.states env.durationRules x.core.pending time
  reconcileAll
    (remaining x.core.pending time)
    env.durationRules
    preImmediate
    (crossingsAt env x subject position time)
    time

def statesAfterMove
    (env : IntegratedEnv) (x : IntegratedConfig) (subject : Id)
    (position : Position) (time : Time) : RuleState :=
  let preImmediate :=
    stateAfterDue x.states env.durationRules x.core.pending time
  applyImmediateRules
    preImmediate env.immediateRules (crossingsAt env x subject position time)

def integratedAdvance
    (env : IntegratedEnv) (x : IntegratedConfig) (time : Time) :
    IntegratedOutcome :=
  if time < x.core.clock then
    .error .backwardsTime x
  else
    .ok
      { core :=
          { x.core with
            pending := remaining x.core.pending time
            clock := time }
        states := stateAfterDue x.states env.durationRules x.core.pending time }
      (dueEvents x.core.pending time)

def integratedRecord
    (env : IntegratedEnv) (x : IntegratedConfig) (observation : Observation) :
    IntegratedOutcome :=
  match record env.core x.core observation with
  | .error code _ => .error code x
  | .ok next trace => .ok { core := next, states := x.states } trace

def integratedMove
    (env : IntegratedEnv) (x : IntegratedConfig) (subject : Id)
    (position : Position) (time : Time) : IntegratedOutcome :=
  if time < x.core.clock then
    .error .backwardsTime x
  else if position.crs != env.core.crs subject then
    .error .crsMismatch x
  else
    let crossings := crossingsAt env x subject position time
    .ok
      { core :=
          { x.core with
            asserted := updatePosition x.core.asserted subject position
            pending := pendingAfterMove env x subject position time
            clock := time }
        states := statesAfterMove env x subject position time }
      (dueEvents x.core.pending time ++ crossings)

def integratedExecute
    (env : IntegratedEnv) (x : IntegratedConfig) : Action -> IntegratedOutcome
  | .record observation => integratedRecord env x observation
  | .move subject position time => integratedMove env x subject position time
  | .advance time => integratedAdvance env x time

def integratedRun
    (env : IntegratedEnv) : IntegratedConfig -> List Action -> IntegratedOutcome
  | x, [] => .ok x []
  | x, action :: rest =>
      match integratedExecute env x action with
      | .error code source => .error code source
      | .ok next firstTrace =>
          match integratedRun env next rest with
          | .error code source => .error code source
          | .ok final restTrace => .ok final (firstTrace ++ restTrace)

def Compiler.CoreProgram.integratedEnv
    (program : Compiler.CoreProgram) (core : Env) : IntegratedEnv :=
  { core
    durationRules := program.rules.map Compiler.CompiledRule.monitorRule
    immediateRules := program.immediateRules.map fun rule =>
      { name := rule.name
        trigger := rule.trigger
        subject := rule.subject
        region := rule.region
        fromState := rule.fromState
        toState := rule.toState } }

def Compiler.compileIntegratedEnv
    (core : Env) (program : Compiler.SurfaceProgram) (initialTime : Time) :
    Option IntegratedEnv :=
  (Compiler.compileProgram program initialTime).map fun compiled =>
    compiled.integratedEnv core

theorem Compiler.compileIntegratedEnv_isSome
    (core : Env) (program : Compiler.SurfaceProgram) (initialTime : Time) :
    (Compiler.compileIntegratedEnv core program initialTime).isSome =
      (Compiler.compileProgram program initialTime).isSome := by
  unfold Compiler.compileIntegratedEnv
  cases Compiler.compileProgram program initialTime <;> rfl

theorem integratedMove_backwards_atomic
    (env : IntegratedEnv) (x : IntegratedConfig) (subject : Id)
    (position : Position) (time : Time) (backwards : time < x.core.clock) :
    integratedMove env x subject position time =
      .error .backwardsTime x := by
  simp [integratedMove, backwards]

theorem integratedMove_crs_atomic
    (env : IntegratedEnv) (x : IntegratedConfig) (subject : Id)
    (position : Position) (time : Time)
    (forward : ¬ time < x.core.clock)
    (mismatch : position.crs ≠ env.core.crs subject) :
    integratedMove env x subject position time =
      .error .crsMismatch x := by
  simp [integratedMove, forward, mismatch]

theorem integratedMove_trace_order
    {env : IntegratedEnv} {x next : IntegratedConfig} {subject : Id}
    {position : Position} {time : Time} {trace : List Event}
    (evaluates : integratedMove env x subject position time = .ok next trace) :
    trace = dueEvents x.core.pending time ++
      crossingEvents env.core x.core.asserted subject position time := by
  unfold integratedMove at evaluates
  split at evaluates <;> try simp at evaluates
  split at evaluates <;> try simp at evaluates
  simp only [crossingsAt] at evaluates
  exact evaluates.2.symm

theorem integratedMove_monitor_uses_preImmediate_state
    {env : IntegratedEnv} {x next : IntegratedConfig} {subject : Id}
    {position : Position} {time : Time} {trace : List Event}
    (evaluates : integratedMove env x subject position time = .ok next trace) :
    next.core.pending =
      reconcileAll
        (remaining x.core.pending time)
        env.durationRules
        (stateAfterDue x.states env.durationRules x.core.pending time)
        (crossingEvents env.core x.core.asserted subject position time)
        time := by
  unfold integratedMove at evaluates
  split at evaluates <;> try simp at evaluates
  split at evaluates <;> try simp at evaluates
  simp only [pendingAfterMove, crossingsAt] at evaluates
  rcases evaluates with ⟨rfl, rfl⟩
  rfl

theorem integratedAdvance_finite
    {env : IntegratedEnv} {x next : IntegratedConfig} {time : Time}
    {trace : List Event}
    (evaluates : integratedAdvance env x time = .ok next trace) :
    trace.length <= x.core.pending.length := by
  unfold integratedAdvance at evaluates
  split at evaluates
  · simp at evaluates
  · simp at evaluates
    rcases evaluates with ⟨rfl, rfl⟩
    simpa [dueEvents] using due_length_le x.core.pending time

private def regressionState : RuleState := fun _ => 0

private def regressionDuration : DurationRule :=
  { name := 7
    trigger := .leaves
    subject := 1
    region := 2
    fromState := 0
    toState := 2
    duration := 10 }

private def regressionImmediate : ImmediateRule :=
  { name := 8
    trigger := .leaves
    subject := 1
    region := 2
    fromState := 0
    toState := 1 }

private def regressionLeave : Event :=
  { kind := .leaves
    subject := 1
    region := 2
    effectiveAt := 5
    emittedAt := 5 }

theorem same_event_monitor_precedes_immediate_regression :
    (reconcileAll [] [regressionDuration] regressionState [regressionLeave] 5).length = 1 /\
    (applyImmediateRules regressionState [regressionImmediate] [regressionLeave]) 1 = 1 := by
  decide

private def tieMonitorLaterName : Monitor :=
  { name := 9, subject := 1, region := 2, deadline := 10 }

private def tieMonitorEarlierName : Monitor :=
  { name := 3, subject := 4, region := 5, deadline := 10 }

theorem equal_deadline_monitors_are_name_ordered_regression :
    due [tieMonitorLaterName, tieMonitorEarlierName] 10 =
      [tieMonitorEarlierName, tieMonitorLaterName] := by
  decide

theorem paper_integrated_environment_exists (core : Env) :
    (Compiler.compileIntegratedEnv core Compiler.paperSurface 0).isSome := by
  rw [Compiler.compileIntegratedEnv_isSome]
  exact Compiler.paper_compiles

private def paperIntegratedDurationRule : DurationRule :=
  { name := 3
    trigger := .leaves
    subject := 5
    region := 4
    fromState := 2
    toState := 0
    duration := 600 }

private def paperIntegratedEnv (core : Env) : IntegratedEnv :=
  { core
    durationRules := [paperIntegratedDurationRule]
    immediateRules := [] }

theorem paper_compileIntegratedEnv_exact (core : Env) :
    Compiler.compileIntegratedEnv core Compiler.paperSurface 0 =
      some (paperIntegratedEnv core) := by
  rfl

theorem paper_integrated_environment_wellFormed (core : Env) :
    ∀ env, Compiler.compileIntegratedEnv core Compiler.paperSurface 0 = some env →
      env.WellFormed := by
  intro env compiled
  rw [paper_compileIntegratedEnv_exact] at compiled
  cases compiled
  simp [IntegratedEnv.WellFormed, paperIntegratedEnv,
    paperIntegratedDurationRule]

end PulseFormal
