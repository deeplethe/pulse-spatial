/-
Copyright 2026 PULSE contributors.
Licensed under the Apache License, Version 2.0.

Proof-checked lifecycle kernel for duration-qualified spatial rules.  A sampled
crossing cancels monitors for the opposite crossing and starts monitors for
matching rules.  This module is intentionally independent of geometry: it
consumes the crossing events produced by Core.crossingEvents.
-/

import PulseFormal.Core

namespace PulseFormal

structure DurationRule where
  name : Id
  trigger : EventKind
  subject : Id
  region : Id
  fromState : Id
  duration : Time
  deriving DecidableEq, Repr

abbrev RuleState := Id → Id

def opposite : EventKind → EventKind
  | .enters => .leaves
  | .leaves => .enters
  | .sustained => .sustained

def EnabledBy (state : RuleState) (rule : DurationRule) : Prop :=
  state rule.subject = rule.fromState

def TriggeredBy (state : RuleState) (rule : DurationRule) (event : Event) : Prop :=
  EnabledBy state rule ∧
  event.kind = rule.trigger ∧
  event.subject = rule.subject ∧
  event.region = rule.region

def CancelledBy
    (rules : List DurationRule) (event : Event) (monitor : Monitor) : Prop :=
  rules.any (fun rule =>
    rule.name == monitor.name &&
    event.kind == opposite rule.trigger &&
    event.subject == rule.subject &&
    event.region == rule.region) = true

instance
    (state : RuleState) (rule : DurationRule) (event : Event) :
    Decidable (TriggeredBy state rule event) :=
  by
    unfold TriggeredBy EnabledBy
    infer_instance

instance
    (rules : List DurationRule) (event : Event) (monitor : Monitor) :
    Decidable (CancelledBy rules event monitor) :=
  by
    unfold CancelledBy
    infer_instance

def monitorOf (rule : DurationRule) (time : Time) : Monitor :=
  { name := rule.name
    subject := rule.subject
    region := rule.region
    deadline := time + rule.duration }

def cancelMatching
    (pending : List Monitor) (rules : List DurationRule) (event : Event) :
    List Monitor :=
  pending.filter fun monitor => decide (¬ CancelledBy rules event monitor)

def startFor : RuleState → List DurationRule → Event → Time → List Monitor
  | _, [], _, _ => []
  | state, rule :: rest, event, time =>
      if TriggeredBy state rule event then
        monitorOf rule time :: startFor state rest event time
      else
        startFor state rest event time

def reconcile
    (pending : List Monitor) (rules : List DurationRule) (state : RuleState)
    (event : Event)
    (time : Time) : List Monitor :=
  cancelMatching pending rules event ++ startFor state rules event time

def reconcileAll
    (pending : List Monitor) (rules : List DurationRule) (state : RuleState) :
    List Event → Time → List Monitor
  | [], _ => pending
  | event :: rest, time =>
      reconcileAll (reconcile pending rules state event time) rules state rest time

def PositiveDurations (rules : List DurationRule) : Prop :=
  ∀ rule ∈ rules, 0 < rule.duration

def FutureDeadlines (pending : List Monitor) (time : Time) : Prop :=
  ∀ monitor ∈ pending, time < monitor.deadline

theorem cancelMatching_member_not_cancelled
    {pending : List Monitor} {rules : List DurationRule} {event : Event}
    {monitor : Monitor}
    (present : monitor ∈ cancelMatching pending rules event) :
    ¬ CancelledBy rules event monitor := by
  have retained := (List.mem_filter.mp present).2
  exact of_decide_eq_true retained

theorem cancelled_not_in_cancelMatching
    {pending : List Monitor} {rules : List DurationRule} {event : Event}
    {monitor : Monitor}
    (cancelled : CancelledBy rules event monitor) :
    monitor ∉ cancelMatching pending rules event := by
  intro present
  exact (cancelMatching_member_not_cancelled present) cancelled

theorem cancelMatching_member_was_pending
    {pending : List Monitor} {rules : List DurationRule} {event : Event}
    {monitor : Monitor}
    (present : monitor ∈ cancelMatching pending rules event) :
    monitor ∈ pending := by
  exact (List.mem_filter.mp present).1

theorem startFor_characterization
    {state : RuleState} {rules : List DurationRule} {event : Event} {time : Time}
    {monitor : Monitor}
    (present : monitor ∈ startFor state rules event time) :
    ∃ rule ∈ rules, TriggeredBy state rule event ∧
      monitor = monitorOf rule time := by
  induction rules with
  | nil => simp [startFor] at present
  | cons rule rest inductionHypothesis =>
      by_cases triggered : TriggeredBy state rule event
      · simp only [startFor, if_pos triggered, List.mem_cons] at present
        rcases present with rfl | present
        · exact ⟨rule, by simp, triggered, rfl⟩
        · obtain ⟨candidate, member, applies, same⟩ :=
            inductionHypothesis present
          exact ⟨candidate, by simp [member], applies, same⟩
      · simp only [startFor, if_neg triggered] at present
        obtain ⟨candidate, member, applies, same⟩ :=
          inductionHypothesis present
        exact ⟨candidate, by simp [member], applies, same⟩

theorem startFor_deadline_exact
    {state : RuleState} {rules : List DurationRule} {event : Event} {time : Time}
    {monitor : Monitor}
    (present : monitor ∈ startFor state rules event time) :
    ∃ rule ∈ rules,
      TriggeredBy state rule event ∧
      monitor.name = rule.name ∧
      monitor.subject = rule.subject ∧
      monitor.region = rule.region ∧
      monitor.deadline = time + rule.duration := by
  obtain ⟨rule, member, applies, rfl⟩ := startFor_characterization present
  exact ⟨rule, member, applies, rfl, rfl, rfl, rfl⟩

theorem startFor_guard_holds
    {state : RuleState} {rules : List DurationRule} {event : Event} {time : Time}
    {monitor : Monitor}
    (present : monitor ∈ startFor state rules event time) :
    ∃ rule ∈ rules,
      EnabledBy state rule ∧ monitor = monitorOf rule time := by
  obtain ⟨rule, member, triggered, same⟩ := startFor_characterization present
  exact ⟨rule, member, triggered.1, same⟩

theorem startFor_future
    {state : RuleState} {rules : List DurationRule} {event : Event} {time : Time}
    (positive : PositiveDurations rules) :
    FutureDeadlines (startFor state rules event time) time := by
  intro monitor present
  obtain ⟨rule, member, _, rfl⟩ := startFor_characterization present
  simp only [monitorOf]
  exact Nat.lt_add_of_pos_right (positive rule member)

theorem cancelMatching_future
    {pending : List Monitor} {rules : List DurationRule} {event : Event}
    {time : Time}
    (future : FutureDeadlines pending time) :
    FutureDeadlines (cancelMatching pending rules event) time := by
  intro monitor present
  exact future monitor (cancelMatching_member_was_pending present)

theorem reconcile_future
    {pending : List Monitor} {rules : List DurationRule} {event : Event}
    {state : RuleState} {time : Time}
    (future : FutureDeadlines pending time)
    (positive : PositiveDurations rules) :
    FutureDeadlines (reconcile pending rules state event time) time := by
  intro monitor present
  simp only [reconcile, List.mem_append] at present
  rcases present with retained | started
  · exact cancelMatching_future future monitor retained
  · exact startFor_future positive monitor started

theorem startFor_length_le
    (state : RuleState) (rules : List DurationRule) (event : Event) (time : Time) :
    (startFor state rules event time).length ≤ rules.length := by
  induction rules with
  | nil => simp [startFor]
  | cons rule rest inductionHypothesis =>
      by_cases triggered : TriggeredBy state rule event
      · simp [startFor, triggered, inductionHypothesis]
      · simp [startFor, triggered]
        exact Nat.le_trans inductionHypothesis (Nat.le_succ _)

theorem reconcile_length_le
    (pending : List Monitor) (rules : List DurationRule) (state : RuleState)
    (event : Event)
    (time : Time) :
    (reconcile pending rules state event time).length ≤
      pending.length + rules.length := by
  simp only [reconcile, List.length_append]
  exact Nat.add_le_add
    (List.length_filter_le _ _)
    (startFor_length_le state rules event time)

theorem reconcileAll_future
    {pending : List Monitor} {rules : List DurationRule} {events : List Event}
    {state : RuleState} {time : Time} :
    FutureDeadlines pending time →
    PositiveDurations rules →
    FutureDeadlines (reconcileAll pending rules state events time) time := by
  induction events generalizing pending with
  | nil =>
      intro future _
      exact future
  | cons event rest inductionHypothesis =>
      intro future positive
      simp only [reconcileAll]
      apply inductionHypothesis
      · exact reconcile_future future positive
      · exact positive

theorem reconcileAll_length_le
    (pending : List Monitor) (rules : List DurationRule) (state : RuleState)
    (events : List Event) (time : Time) :
    (reconcileAll pending rules state events time).length ≤
      pending.length + events.length * rules.length := by
  induction events generalizing pending with
  | nil => simp [reconcileAll]
  | cons event rest inductionHypothesis =>
      simp only [reconcileAll, List.length_cons]
      calc
        (reconcileAll (reconcile pending rules state event time) rules state rest time).length
            ≤ (reconcile pending rules state event time).length +
                rest.length * rules.length := inductionHypothesis _
        _ ≤ (pending.length + rules.length) +
                rest.length * rules.length :=
              Nat.add_le_add_right
                (reconcile_length_le pending rules state event time) _
        _ = pending.length + (rest.length + 1) * rules.length := by
              simp [Nat.add_mul, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]

end PulseFormal
