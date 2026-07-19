/-
Copyright 2026 PULSE contributors.
Licensed under the Apache License, Version 2.0.

Mechanized safety kernel for PULSE.  Geometry membership is abstracted as a
total Boolean function, while mode separation, clock validation, sampled
crossings, pending timers, atomic errors, and scenario cloning are explicit.
-/

namespace PulseFormal

abbrev Id := Nat
abbrev Time := Nat

structure Position where
  x : Int
  y : Int
  crs : Nat
  deriving DecidableEq, Repr

structure Observation where
  subject : Id
  position : Position
  observedAt : Time
  source : Id
  deriving DecidableEq, Repr

inductive EventKind where
  | enters
  | leaves
  | sustained
  deriving DecidableEq, Repr

structure Event where
  kind : EventKind
  subject : Id
  region : Id
  effectiveAt : Time
  emittedAt : Time
  deriving DecidableEq, Repr

structure Monitor where
  name : Id
  subject : Id
  region : Id
  deadline : Time
  deriving DecidableEq, Repr

structure Env where
  crs : Id → Nat
  regions : List Id
  membership : Position → Id → Bool

structure Config where
  asserted : Id → Option Position
  observations : List Observation
  pending : List Monitor
  clock : Time

inductive Error where
  | backwardsTime
  | crsMismatch
  | invalidObservation
  deriving DecidableEq, Repr

inductive Action where
  | record (observation : Observation)
  | move (subject : Id) (position : Position) (time : Time)
  | advance (to : Time)

inductive Outcome where
  | ok (config : Config) (trace : List Event)
  | error (code : Error) (source : Config)

def ValidObservation (env : Env) (o : Observation) : Prop :=
  o.position.crs = env.crs o.subject

def WellFormed (env : Env) (x : Config) : Prop :=
  (∀ i p, x.asserted i = some p → p.crs = env.crs i) ∧
  (∀ o ∈ x.observations, ValidObservation env o) ∧
  (∀ m ∈ x.pending, x.clock < m.deadline)

def updatePosition
    (positions : Id → Option Position) (subject : Id) (p : Position) :
    Id → Option Position :=
  fun candidate => if candidate = subject then some p else positions candidate

def due (pending : List Monitor) (time : Time) : List Monitor :=
  pending.filter (fun monitor => decide (monitor.deadline ≤ time))

def remaining (pending : List Monitor) (time : Time) : List Monitor :=
  pending.filter (fun monitor => decide (time < monitor.deadline))

def dueEvents (pending : List Monitor) (time : Time) : List Event :=
  (due pending time).map fun monitor =>
    { kind := .sustained
      subject := monitor.subject
      region := monitor.region
      effectiveAt := monitor.deadline
      emittedAt := time }

def crossingEvents
    (env : Env) (positions : Id → Option Position) (subject : Id)
    (next : Position) (time : Time) : List Event :=
  match positions subject with
  | none => []
  | some previous =>
      env.regions.filterMap fun region =>
        let before := env.membership previous region
        let after := env.membership next region
        if before = after then none
        else some {
          kind := if after then .enters else .leaves
          subject := subject
          region := region
          effectiveAt := time
          emittedAt := time
        }

def advance (x : Config) (time : Time) : Outcome :=
  if time < x.clock then .error .backwardsTime x
  else
    .ok
      { x with pending := remaining x.pending time, clock := time }
      (dueEvents x.pending time)

def record (env : Env) (x : Config) (o : Observation) : Outcome :=
  if o.position.crs = env.crs o.subject then
    .ok { x with observations := x.observations ++ [o] } []
  else
    .error .invalidObservation x

def move
    (env : Env) (x : Config) (subject : Id) (position : Position)
    (time : Time) : Outcome :=
  if time < x.clock then .error .backwardsTime x
  else if position.crs ≠ env.crs subject then .error .crsMismatch x
  else
    .ok
      { x with
        asserted := updatePosition x.asserted subject position
        pending := remaining x.pending time
        clock := time }
      (dueEvents x.pending time ++
        crossingEvents env x.asserted subject position time)

def execute (env : Env) (x : Config) : Action → Outcome
  | .record o => record env x o
  | .move subject position time => move env x subject position time
  | .advance time => advance x time

def Exec (env : Env) (x : Config) (action : Action) (outcome : Outcome) : Prop :=
  execute env x action = outcome

def run (env : Env) : Config → List Action → Outcome
  | x, [] => .ok x []
  | x, action :: rest =>
      match execute env x action with
      | .error code source => .error code source
      | .ok next firstTrace =>
          match run env next rest with
          | .error code source => .error code source
          | .ok final restTrace => .ok final (firstTrace ++ restTrace)

structure ScenarioResult where
  source : Config
  branch : Outcome

def scenario (env : Env) (source : Config) (actions : List Action) :
    ScenarioResult :=
  { source := source, branch := run env source actions }

theorem updatePosition_eq
    (positions : Id → Option Position) (subject : Id) (p : Position) :
    updatePosition positions subject p subject = some p := by
  simp [updatePosition]

theorem updatePosition_ne
    (positions : Id → Option Position) (subject other : Id) (p : Position)
    (h : other ≠ subject) :
    updatePosition positions subject p other = positions other := by
  simp [updatePosition, h]

theorem remaining_future
    {pending : List Monitor} {time : Time} {monitor : Monitor}
    (h : monitor ∈ remaining pending time) : time < monitor.deadline := by
  simpa [remaining] using (List.mem_filter.mp h).2

theorem advance_preserves
    {env : Env} {x next : Config} {time : Time} {trace : List Event}
    (wf : WellFormed env x)
    (evaluates : advance x time = .ok next trace) :
    WellFormed env next := by
  unfold advance at evaluates
  split at evaluates
  · simp at evaluates
  · simp at evaluates
    rcases evaluates with ⟨rfl, rfl⟩
    rcases wf with ⟨positions, observations, monitors⟩
    refine ⟨positions, observations, ?_⟩
    intro monitor present
    exact remaining_future present

theorem record_preserves
    {env : Env} {x next : Config} {o : Observation} {trace : List Event}
    (wf : WellFormed env x)
    (evaluates : record env x o = .ok next trace) :
    WellFormed env next := by
  unfold record at evaluates
  split at evaluates
  · simp at evaluates
    rcases evaluates with ⟨rfl, rfl⟩
    rcases wf with ⟨positions, observations, monitors⟩
    refine ⟨positions, ?_, monitors⟩
    intro candidate present
    simp only [List.mem_append, List.mem_singleton] at present
    rcases present with present | rfl
    · exact observations candidate present
    · unfold ValidObservation
      assumption
  · simp at evaluates

theorem move_preserves
    {env : Env} {x next : Config} {subject : Id} {position : Position}
    {time : Time} {trace : List Event}
    (wf : WellFormed env x)
    (evaluates : move env x subject position time = .ok next trace) :
    WellFormed env next := by
  unfold move at evaluates
  split at evaluates
  · simp at evaluates
  · split at evaluates
    · simp at evaluates
    · simp at evaluates
      rcases evaluates with ⟨rfl, rfl⟩
      simp at ‹¬position.crs ≠ env.crs subject›
      rcases wf with ⟨positions, observations, monitors⟩
      refine ⟨?_, observations, ?_⟩
      · intro candidate p assigned
        change updatePosition x.asserted subject position candidate = some p at assigned
        by_cases same : candidate = subject
        · subst candidate
          simp [updatePosition] at assigned
          cases assigned
          exact ‹position.crs = env.crs subject›
        · rw [updatePosition_ne _ _ _ _ same] at assigned
          exact positions candidate p assigned
      · intro monitor present
        exact remaining_future present

theorem preservation
    {env : Env} {x next : Config} {action : Action} {trace : List Event}
    (wf : WellFormed env x)
    (evaluates : Exec env x action (.ok next trace)) :
    WellFormed env next := by
  cases action with
  | record o => exact record_preserves wf evaluates
  | move subject position time => exact move_preserves wf evaluates
  | advance time => exact advance_preserves wf evaluates

theorem determinism
    {env : Env} {x : Config} {action : Action} {first second : Outcome}
    (hFirst : Exec env x action first) (hSecond : Exec env x action second) :
    first = second := by
  exact hFirst.symm.trans hSecond

theorem observation_noninterference
    {env : Env} {x next : Config} {o : Observation} {trace : List Event}
    (evaluates : Exec env x (.record o) (.ok next trace)) :
    next.asserted = x.asserted ∧ next.pending = x.pending ∧ next.clock = x.clock := by
  change record env x o = .ok next trace at evaluates
  unfold record at evaluates
  split at evaluates
  · simp at evaluates
    rcases evaluates with ⟨rfl, rfl⟩
    simp
  · simp at evaluates

theorem scenario_isolation (env : Env) (x : Config) (actions : List Action) :
    (scenario env x actions).source = x := by
  rfl

theorem finite_advance
    {x next : Config} {time : Time} {trace : List Event}
    (evaluates : advance x time = .ok next trace) :
    trace.length ≤ x.pending.length := by
  unfold advance at evaluates
  split at evaluates
  · simp at evaluates
  · simp at evaluates
    rcases evaluates with ⟨rfl, rfl⟩
    simp [dueEvents, due]
    exact List.length_filter_le _ _

theorem atomic_failure
    {env : Env} {x failed : Config} {action : Action} {code : Error}
    (evaluates : Exec env x action (.error code failed)) :
    failed = x := by
  cases action with
  | record o =>
      change record env x o = .error code failed at evaluates
      unfold record at evaluates
      split at evaluates
      · simp at evaluates
      · simp at evaluates
        exact evaluates.2.symm
  | move subject position time =>
      change move env x subject position time = .error code failed at evaluates
      unfold move at evaluates
      split at evaluates
      · simp at evaluates
        exact evaluates.2.symm
      · split at evaluates
        · simp at evaluates
          exact evaluates.2.symm
        · simp at evaluates
  | advance time =>
      change advance x time = .error code failed at evaluates
      unfold advance at evaluates
      split at evaluates
      · simp at evaluates
        exact evaluates.2.symm
      · simp at evaluates

end PulseFormal
