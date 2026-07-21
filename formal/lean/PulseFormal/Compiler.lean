/-
Copyright 2026 PULSE contributors.
Licensed under the Apache License, Version 2.0.

Verified compilation boundary for the executable paper subset.  The surface
records below start after parsing but before name resolution and desugaring.
Compilation resolves identifiers, normalizes durations to seconds, and lowers
scenario assumptions plus a horizon to Core actions.
-/

import PulseFormal.Monitors

namespace PulseFormal
namespace Compiler

inductive DurationUnit where
  | seconds
  | minutes
  | hours
  deriving DecidableEq, Repr

structure SurfaceDuration where
  value : Nat
  unit : DurationUnit
  deriving DecidableEq, Repr

def durationSeconds : SurfaceDuration → Time
  | ⟨value, .seconds⟩ => value
  | ⟨value, .minutes⟩ => value * 60
  | ⟨value, .hours⟩ => value * 3600

inductive SurfaceTrigger where
  | enters
  | leaves
  deriving DecidableEq, Repr

def SurfaceTrigger.toEventKind : SurfaceTrigger → EventKind
  | .enters => .enters
  | .leaves => .leaves

structure SurfacePosition where
  xMicrodegrees : Int
  yMicrodegrees : Int
  crs : String
  deriving DecidableEq, Repr

structure SurfaceRule where
  name : String
  trigger : SurfaceTrigger
  subject : String
  region : String
  fromState : String
  toState : String
  duration : SurfaceDuration
  deriving DecidableEq, Repr

structure SurfaceImmediateRule where
  name : String
  trigger : SurfaceTrigger
  subject : String
  region : String
  fromState : String
  toState : String
  deriving DecidableEq, Repr

structure SurfaceMove where
  subject : String
  position : SurfacePosition
  deriving DecidableEq, Repr

structure SurfaceScenario where
  name : String
  assumptions : List SurfaceMove
  horizon : Option SurfaceDuration
  deriving DecidableEq, Repr

structure SurfaceProgram where
  symbols : List String
  rules : List SurfaceRule
  immediateRules : List SurfaceImmediateRule
  scenarios : List SurfaceScenario
  deriving DecidableEq, Repr

private def resolveFrom : List String → String → Nat → Option Id
  | [], _, _ => none
  | candidate :: rest, name, next =>
      if candidate = name then some next
      else resolveFrom rest name (next + 1)

def resolveName (symbols : List String) (name : String) : Option Id :=
  resolveFrom symbols name 0

structure ResolvedRuleNames where
  name : Id
  subject : Id
  region : Id
  fromState : Id
  toState : Id
  deriving DecidableEq, Repr

def resolveRuleNames
    (symbols : List String) (rule : SurfaceRule) : Option ResolvedRuleNames :=
  match resolveName symbols rule.name with
  | none => none
  | some name =>
      match resolveName symbols rule.subject with
      | none => none
      | some subject =>
          match resolveName symbols rule.region with
          | none => none
          | some region =>
              match resolveName symbols rule.fromState with
              | none => none
              | some fromState =>
                  match resolveName symbols rule.toState with
                  | none => none
                  | some toState =>
                      some { name, subject, region, fromState, toState }

def resolveImmediateRuleNames
    (symbols : List String) (rule : SurfaceImmediateRule) :
    Option ResolvedRuleNames :=
  resolveRuleNames symbols
    { name := rule.name
      trigger := rule.trigger
      subject := rule.subject
      region := rule.region
      fromState := rule.fromState
      toState := rule.toState
      duration := { value := 1, unit := .seconds } }

theorem resolveRuleNames_preserves_fromState
    {symbols : List String} {rule : SurfaceRule} {names : ResolvedRuleNames}
    (resolved : resolveRuleNames symbols rule = some names) :
    resolveName symbols rule.fromState = some names.fromState := by
  unfold resolveRuleNames at resolved
  split at resolved <;> try simp_all
  split at resolved <;> try simp_all
  split at resolved <;> try simp_all
  split at resolved <;> try simp_all
  split at resolved <;> try simp_all
  cases resolved
  rfl

structure CompiledRule where
  name : Id
  trigger : EventKind
  subject : Id
  region : Id
  fromState : Id
  toState : Id
  duration : Time
  deriving DecidableEq, Repr

structure CompiledImmediateRule where
  name : Id
  trigger : EventKind
  subject : Id
  region : Id
  fromState : Id
  toState : Id
  deriving DecidableEq, Repr

def CompiledRule.monitorRule (rule : CompiledRule) : DurationRule :=
  { name := rule.name
    trigger := rule.trigger
    subject := rule.subject
    region := rule.region
    fromState := rule.fromState
    toState := rule.toState
    duration := rule.duration }

def compileRule
    (symbols : List String) (rule : SurfaceRule) : Option CompiledRule :=
  (resolveRuleNames symbols rule).map fun names =>
    { name := names.name
      trigger := rule.trigger.toEventKind
      subject := names.subject
      region := names.region
      fromState := names.fromState
      toState := names.toState
      duration := durationSeconds rule.duration }

def compileImmediateRule
    (symbols : List String) (rule : SurfaceImmediateRule) :
    Option CompiledImmediateRule :=
  (resolveImmediateRuleNames symbols rule).map fun names =>
    { name := names.name
      trigger := rule.trigger.toEventKind
      subject := names.subject
      region := names.region
      fromState := names.fromState
      toState := names.toState }

def compilePosition
    (symbols : List String) (position : SurfacePosition) : Option Position :=
  (resolveName symbols position.crs).map fun crs =>
    { x := position.xMicrodegrees
      y := position.yMicrodegrees
      crs }

structure CompiledMove where
  subject : Id
  position : Position
  deriving DecidableEq, Repr

def compileMove
    (symbols : List String) (move : SurfaceMove) : Option CompiledMove := do
  let subject ← resolveName symbols move.subject
  let position ← compilePosition symbols move.position
  pure { subject, position }

structure ResolvedScenarioNames where
  name : Id
  moves : List CompiledMove
  deriving DecidableEq, Repr

def resolveScenarioNames
    (symbols : List String) (scenario : SurfaceScenario) :
    Option ResolvedScenarioNames := do
  let name ← resolveName symbols scenario.name
  let moves ← scenario.assumptions.mapM (compileMove symbols)
  pure { name, moves }

def actionsFor
    (moves : List CompiledMove) (horizonEnd : Option Time)
    (initialTime : Time) : List Action :=
  moves.map (fun move => .move move.subject move.position initialTime) ++
    match horizonEnd with
    | none => []
    | some target => [.advance target]

structure CompiledScenario where
  name : Id
  moves : List CompiledMove
  horizonEnd : Option Time
  deriving DecidableEq, Repr

def CompiledScenario.actions
    (scenario : CompiledScenario) (initialTime : Time) : List Action :=
  actionsFor scenario.moves scenario.horizonEnd initialTime

def compileScenario
    (symbols : List String) (initialTime : Time)
    (scenario : SurfaceScenario) : Option CompiledScenario :=
  (resolveScenarioNames symbols scenario).map fun names =>
    { name := names.name
      moves := names.moves
      horizonEnd := scenario.horizon.map fun duration =>
        initialTime + durationSeconds duration }

structure CoreProgram where
  symbols : List String
  rules : List CompiledRule
  immediateRules : List CompiledImmediateRule
  scenarios : List CompiledScenario
  deriving DecidableEq, Repr

def compileProgram
    (program : SurfaceProgram) (initialTime : Time) : Option CoreProgram := do
  let rules ← program.rules.mapM (compileRule program.symbols)
  let immediateRules ← program.immediateRules.mapM
    (compileImmediateRule program.symbols)
  let scenarios ← program.scenarios.mapM
    (compileScenario program.symbols initialTime)
  pure { symbols := program.symbols, rules, immediateRules, scenarios }

def SurfaceRule.WellTyped (symbols : List String) (rule : SurfaceRule) : Prop :=
  (resolveRuleNames symbols rule).isSome ∧ 0 < durationSeconds rule.duration

def CompiledRule.WellFormed (rule : CompiledRule) : Prop :=
  0 < rule.duration

def SurfaceImmediateRule.WellTyped
    (symbols : List String) (rule : SurfaceImmediateRule) : Prop :=
  (resolveImmediateRuleNames symbols rule).isSome

def CompiledImmediateRule.WellFormed
    (rule : CompiledImmediateRule) : Prop :=
  rule.fromState ≠ rule.toState

def SurfaceScenario.WellTyped
    (symbols : List String) (scenario : SurfaceScenario) : Prop :=
  (resolveScenarioNames symbols scenario).isSome ∧
    ∀ duration ∈ scenario.horizon, 0 < durationSeconds duration

def CompiledScenario.WellFormed
    (initialTime : Time) (scenario : CompiledScenario) : Prop :=
  ∀ horizonEnd ∈ scenario.horizonEnd, initialTime < horizonEnd

theorem compileRule_preserves_fields
    {symbols : List String} {surface : SurfaceRule} {core : CompiledRule}
    (compiled : compileRule symbols surface = some core) :
    core.trigger = surface.trigger.toEventKind ∧
    core.duration = durationSeconds surface.duration := by
  unfold compileRule at compiled
  cases resolved : resolveRuleNames symbols surface with
  | none => simp [resolved] at compiled
  | some names =>
      simp [resolved] at compiled
      subst core
      simp

theorem compileRule_preserves_guard
    {symbols : List String} {surface : SurfaceRule} {core : CompiledRule}
    (compiled : compileRule symbols surface = some core) :
    resolveName symbols surface.fromState = some core.fromState := by
  unfold compileRule at compiled
  cases resolved : resolveRuleNames symbols surface with
  | none => simp [resolved] at compiled
  | some names =>
      simp [resolved] at compiled
      subst core
      exact resolveRuleNames_preserves_fromState resolved

theorem compileRule_preserves_wellTyped
    {symbols : List String} {surface : SurfaceRule} {core : CompiledRule}
    (typed : surface.WellTyped symbols)
    (compiled : compileRule symbols surface = some core) :
    core.WellFormed := by
  have duration := (compileRule_preserves_fields compiled).2
  unfold SurfaceRule.WellTyped at typed
  unfold CompiledRule.WellFormed
  simpa [duration] using typed.2

theorem compileRule_deadline_exact
    {symbols : List String} {surface : SurfaceRule} {core : CompiledRule}
    (compiled : compileRule symbols surface = some core) (time : Time) :
    (monitorOf core.monitorRule time).deadline =
      time + durationSeconds surface.duration := by
  simp only [monitorOf, CompiledRule.monitorRule]
  exact congrArg (time + ·) (compileRule_preserves_fields compiled).2

theorem compileImmediateRule_preserves_fields
    {symbols : List String} {surface : SurfaceImmediateRule}
    {core : CompiledImmediateRule}
    (compiled : compileImmediateRule symbols surface = some core) :
    core.trigger = surface.trigger.toEventKind ∧
    resolveName symbols surface.fromState = some core.fromState ∧
    resolveName symbols surface.toState = some core.toState := by
  unfold compileImmediateRule at compiled
  unfold resolveImmediateRuleNames at compiled
  cases resolved : resolveRuleNames symbols
      { name := surface.name
        trigger := surface.trigger
        subject := surface.subject
        region := surface.region
        fromState := surface.fromState
        toState := surface.toState
        duration := { value := 1, unit := .seconds } } with
  | none => simp [resolved] at compiled
  | some names =>
      simp [resolved] at compiled
      subst core
      constructor
      · rfl
      · constructor
        · exact resolveRuleNames_preserves_fromState resolved
        · unfold resolveRuleNames at resolved
          split at resolved <;> try simp_all
          split at resolved <;> try simp_all
          split at resolved <;> try simp_all
          split at resolved <;> try simp_all
          split at resolved <;> try simp_all
          cases resolved
          rfl

theorem compileScenario_preserves_horizon
    {symbols : List String} {initialTime : Time}
    {surface : SurfaceScenario} {core : CompiledScenario}
    (compiled : compileScenario symbols initialTime surface = some core) :
    core.horizonEnd = surface.horizon.map fun duration =>
      initialTime + durationSeconds duration := by
  unfold compileScenario at compiled
  cases resolved : resolveScenarioNames symbols surface with
  | none => simp [resolved] at compiled
  | some names =>
      simp [resolved] at compiled
      subst core
      rfl

theorem compileScenario_preserves_wellTyped
    {symbols : List String} {initialTime : Time}
    {surface : SurfaceScenario} {core : CompiledScenario}
    (typed : surface.WellTyped symbols)
    (compiled : compileScenario symbols initialTime surface = some core) :
    core.WellFormed initialTime := by
  intro target present
  rw [compileScenario_preserves_horizon compiled] at present
  cases horizon : surface.horizon with
  | none => simp [horizon] at present
  | some duration =>
      simp [horizon] at present
      subst target
      exact Nat.lt_add_of_pos_right (typed.2 duration (by simp [horizon]))

def surfaceScenarioSemantics
    (env : Env) (source : Config) (symbols : List String)
    (initialTime : Time) (scenario : SurfaceScenario) : Option Outcome :=
  (resolveScenarioNames symbols scenario).map fun names =>
    run env source
      (actionsFor names.moves
        (scenario.horizon.map fun duration =>
          initialTime + durationSeconds duration)
        initialTime)

theorem compileScenario_simulates_execution
    {env : Env} {source : Config} {symbols : List String}
    {initialTime : Time} {surface : SurfaceScenario} {core : CompiledScenario}
    (compiled : compileScenario symbols initialTime surface = some core) :
    surfaceScenarioSemantics env source symbols initialTime surface =
      some (run env source (core.actions initialTime)) := by
  unfold compileScenario at compiled
  unfold surfaceScenarioSemantics
  cases resolved : resolveScenarioNames symbols surface with
  | none => simp [resolved] at compiled
  | some names =>
      simp [resolved] at compiled
      subst core
      rfl

def paperSymbols : List String :=
  [ "AtRisk"
  , "Reroute"
  , "Safe"
  , "SustainedDeparture@batch"
  , "Z"
  , "batch"
  , "http://www.opengis.net/def/crs/OGC/1.3/CRS84" ]

def paperSurface : SurfaceProgram :=
  { symbols := paperSymbols
    rules :=
      [ { name := "SustainedDeparture@batch"
          trigger := .leaves
          subject := "batch"
          region := "Z"
          fromState := "Safe"
          toState := "AtRisk"
          duration := ⟨10, .minutes⟩ } ]
    immediateRules := []
    scenarios :=
      [ { name := "Reroute"
          assumptions :=
            [ { subject := "batch"
                position :=
                  { xMicrodegrees := 121515000
                    yMicrodegrees := 31205000
                    crs := "http://www.opengis.net/def/crs/OGC/1.3/CRS84" } } ]
          horizon := some ⟨20, .minutes⟩ } ] }

theorem paper_compiles : (compileProgram paperSurface 0).isSome := by
  decide

private def quote (value : String) : String :=
  "\"" ++ value ++ "\""

private def renderList (values : List String) : String :=
  "[" ++ String.intercalate "," values ++ "]"

private def renderSymbol (name : String) : String := quote name

private def renderTrigger : EventKind → String
  | .enters => quote "enters"
  | .leaves => quote "leaves"
  | .sustained => quote "sustained"

private def renderRule (rule : CompiledRule) : String :=
  "{\"name\":" ++ toString rule.name ++
  ",\"trigger\":" ++ renderTrigger rule.trigger ++
  ",\"subject\":" ++ toString rule.subject ++
  ",\"region\":" ++ toString rule.region ++
  ",\"fromState\":" ++ toString rule.fromState ++
  ",\"toState\":" ++ toString rule.toState ++
  ",\"durationSeconds\":" ++ toString rule.duration ++ "}"

private def renderImmediateRule (rule : CompiledImmediateRule) : String :=
  "{\"name\":" ++ toString rule.name ++
  ",\"trigger\":" ++ renderTrigger rule.trigger ++
  ",\"subject\":" ++ toString rule.subject ++
  ",\"region\":" ++ toString rule.region ++
  ",\"fromState\":" ++ toString rule.fromState ++
  ",\"toState\":" ++ toString rule.toState ++ "}"

private def renderPosition (position : Position) : String :=
  "{\"xMicrodegrees\":" ++ toString position.x ++
  ",\"yMicrodegrees\":" ++ toString position.y ++
  ",\"crs\":" ++ toString position.crs ++ "}"

private def renderAction : Action → String
  | .record observation =>
      "{\"kind\":\"record\",\"subject\":" ++
      toString observation.subject ++
      ",\"time\":" ++ toString observation.observedAt ++ "}"
  | .move subject position time =>
      "{\"kind\":\"move\",\"subject\":" ++ toString subject ++
      ",\"position\":" ++ renderPosition position ++
      ",\"time\":" ++ toString time ++ "}"
  | .advance time =>
      "{\"kind\":\"advance\",\"time\":" ++ toString time ++ "}"

private def renderScenario (initialTime : Time) (scenario : CompiledScenario) : String :=
  "{\"name\":" ++ toString scenario.name ++ ",\"actions\":" ++
  renderList ((scenario.actions initialTime).map renderAction) ++ "}"

def renderCanonical (initialTime : Time) (program : CoreProgram) : String :=
  "{\"schemaVersion\":1,\"symbols\":" ++
  renderList (program.symbols.map renderSymbol) ++
  ",\"durationRules\":" ++ renderList (program.rules.map renderRule) ++
  ",\"immediateRules\":" ++
  renderList (program.immediateRules.map renderImmediateRule) ++
  ",\"scenarios\":" ++
  renderList (program.scenarios.map (renderScenario initialTime)) ++ "}\n"

def paperCanonical : String :=
  match compileProgram paperSurface 0 with
  | none => "compile-error\n"
  | some program => renderCanonical 0 program

end Compiler
end PulseFormal
