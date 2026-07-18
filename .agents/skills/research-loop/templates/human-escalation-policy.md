# Human Escalation Policy

A living policy that records every human escalation, the trigger that caused it, the decision made, and any follow-up conditions. The research loop must consult this file before committing to expensive or irreversible actions.

## When to escalate

Escalations are **preventive by default**. If a trigger matches, pause the loop and ask the user before continuing, unless the user has pre-approved the escalation condition in this file.

## Pre-approved conditions

If the user has explicitly pre-approved a condition, record it here so future loops can skip escalation for that condition.

```
- **Condition:** [e.g., "GPU spend up to $20 per run"]
- **Scope:** [which project/task/branch]
- **Approved by:** [user or date]
- **Expiry:** [date or "until revoked"]
```

## Preventive triggers (escalate *before* waste)

- **P1 — Budget threshold crossed:** estimated cumulative time to complete the current branch exceeds 50% of remaining time budget; compute/API cost threshold is crossed; or elapsed budget in Phase 2 exceeds 25% of total budget before completing the phase.
- **P2 — Major decision gate:** committing to an approach requiring >4 hours or significant compute; pruning the last viable alternative; switching branch families.
- **P3 — Plan divergence:** the next step no longer advances the Phase 1 goal.
- **P4 — Expensive compute:** single workload >$10 or 1 GPU-hour, or benchmark >30 min wall-clock.
- **P5 — Framework / dependency change:** adding a major dependency, language, cloud service, or paid API not in original constraints.
- **P6 — Goal re-validation:** feasibility verdict shifts from ACHIEVABLE to UNACHIEVABLE/UNKNOWN.
- **P7 — P0/P1 bypass:** unknown marked `provisional-high-risk` or `empirically-validated` via triangulation bypass.
- **P8 — User checkpoint:** original prompt contains "ask me before", "check with me", or "stop before".

## Reactive triggers (escalate *after* waste or failure)

- **R1 — Best branch killed and no fallback remains.**
- **R2 — Three consecutive steps with no measurable progress.**
- **R3 — P0 unknown cannot be empirically validated.**
- **R4 — New unknown invalidates current branch.**
- **R5 — Repeated probe failure on P0/P1 unknown.**
- **R6 — External dependency unavailable.**
- **R7 — Safety / ethics / rules boundary crossed.**
- **R8 — Exceptional success (already above target).**

## Escalation log

### E<id>: <short trigger summary>
- **Date:** YYYY-MM-DD
- **Phase:** 1–10 or "pre-loop"
- **Trigger:** which policy clause fired
- **Trigger type:** preventive | reactive
- **Situation:** what the agent was about to do or what just happened
- **Options presented:** the choices offered to the user
- **User decision:** what the user chose
- **Consequences:** what the agent is now allowed or forbidden to do
- **Follow-up condition:** when to re-escalate or auto-resolve
