import PulseFormal.Integrated

open PulseFormal

structure TraceCaseSpec where
  initialInside : Bool
  firstInside : Bool
  secondInside : Bool
  immediate : Bool
  dualRule : Bool

private def booleans : List Bool := [false, true]

private def traceCases : List TraceCaseSpec :=
  booleans.flatMap fun initialInside =>
    booleans.flatMap fun firstInside =>
      booleans.flatMap fun secondInside =>
        booleans.flatMap fun immediate =>
          booleans.map fun dualRule =>
            { initialInside, firstInside, secondInside, immediate, dualRule }

private def position (inside : Bool) : Position :=
  { x := if inside then 1 else -1
    y := 0
    crs := 0 }

private def coreEnv : Env :=
  { crs := fun _ => 0
    regions := [9]
    membership := fun candidate region =>
      region == 9 && decide (0 <= candidate.x) }

private def durationRule : DurationRule :=
  { name := 1
    trigger := .leaves
    subject := 0
    region := 9
    fromState := 0
    toState := 2
    duration := 2 }

private def immediateRule : ImmediateRule :=
  { name := 2
    trigger := .leaves
    subject := 0
    region := 9
    fromState := 0
    toState := 1 }

private def secondDurationRule : DurationRule :=
  { name := 0
    trigger := .leaves
    subject := 1
    region := 9
    fromState := 0
    toState := 2
    duration := 2 }

private def traceEnv (withImmediate dualRule : Bool) : IntegratedEnv :=
  { core := coreEnv
    durationRules :=
      if dualRule then [durationRule, secondDurationRule] else [durationRule]
    immediateRules := if withImmediate then [immediateRule] else [] }

private def initialConfig (inside : Bool) : IntegratedConfig :=
  { core :=
      { asserted := fun subject =>
          if subject = 0 then some (position inside)
          else if subject = 1 then some (position true)
          else none
        observations := []
        pending := []
        clock := 0 }
    states := fun _ => 0 }

private def actions (spec : TraceCaseSpec) : List Action :=
  [ .move 0 (position spec.firstInside) 1 ] ++
  (if spec.dualRule then [.move 1 (position false) 1] else []) ++
  [ .move 0 (position spec.secondInside) 2, .advance 4 ]

private def boolText (value : Bool) : String :=
  if value then "true" else "false"

private def renderKind : EventKind -> String
  | .enters => "\"enters\""
  | .leaves => "\"leaves\""
  | .sustained => "\"sustained\""

private def renderEvent (event : Event) : String :=
  "{\"kind\":" ++ renderKind event.kind ++
  ",\"subject\":" ++ toString event.subject ++
  ",\"region\":" ++ toString event.region ++
  ",\"effectiveAt\":" ++ toString event.effectiveAt ++
  ",\"emittedAt\":" ++ toString event.emittedAt ++ "}"

private def renderEvents (events : List Event) : String :=
  "[" ++ String.intercalate "," (events.map renderEvent) ++ "]"

private def renderCase (spec : TraceCaseSpec) : String :=
  let header :=
    "{\"initialInside\":" ++ boolText spec.initialInside ++
    ",\"firstInside\":" ++ boolText spec.firstInside ++
    ",\"secondInside\":" ++ boolText spec.secondInside ++
    ",\"immediate\":" ++ boolText spec.immediate ++
    ",\"dualRule\":" ++ boolText spec.dualRule
  match integratedRun (traceEnv spec.immediate spec.dualRule)
      (initialConfig spec.initialInside) (actions spec) with
  | .error _ source =>
      header ++ ",\"status\":\"error\",\"finalState\":" ++
        toString (source.states 0) ++
        ",\"secondaryState\":" ++ toString (source.states 1) ++
        ",\"pending\":" ++ toString source.core.pending.length ++
        ",\"trace\":[]}"
  | .ok final trace =>
      header ++ ",\"status\":\"ok\",\"finalState\":" ++
        toString (final.states 0) ++
        ",\"secondaryState\":" ++ toString (final.states 1) ++
        ",\"pending\":" ++ toString final.core.pending.length ++
        ",\"trace\":" ++ renderEvents trace ++ "}"

def main : IO Unit :=
  IO.print <| "{\"schemaVersion\":1,\"caseCount\":" ++
    toString traceCases.length ++ ",\"cases\":[" ++
    String.intercalate "," (traceCases.map renderCase) ++ "]}\n"
