# Hypothesis Tree

All considered approaches with predicted outcomes, confidence, and evidence. This is an MCTS-like branching structure: each branch is a candidate path, and branches are expanded, evaluated, or pruned based on research and execution results.

## Branch statuses

- `active` — under consideration or being researched
- `selected` — chosen as the current primary path; execution is proceeding on this branch
- `deferred` — promising but deprioritized due to resources or dependencies
- `eliminated` — pruned based on evidence, failed probe, or failed execution
- `completed` — reached the goal and archived

## Entry format

```
### B<id>: <branch name>
- **Status:** active | selected | deferred | eliminated | completed
- **Parent:** B<id> or `root`
- **Predicted outcome:** what the branch is expected to achieve (e.g., score, Elo, metric)
- **Confidence:** LOW | MEDIUM | HIGH (with justification). Optional numeric score: 0.0–0.3 = LOW, 0.3–0.6 = MEDIUM, 0.6–1.0 = HIGH. The numeric score is an aid; the qualitative label is the source of truth.
- **Process reward proxy:** the measurable signal used to score this branch
- **Proxy ID:** PX<id> linking to `proxy-log.md`
- **Proxy status:** candidate | validated | degraded | rejected | retired
- **Proxy value:** current value of the proxy
- **Evidence:** list of sources, unknowns, and probe results supporting or undermining this branch
- **Blocked by:** P0/P1 unknowns that must be resolved before this branch can proceed
- **Next step:** the one concrete step to take next on this branch
- **Estimated cost:** time/compute/resources needed for the next step
- **Children:** B<id>, B<id> (sub-variants or follow-up branches)
```

## Active / selected branches

<!-- Add branches here. Keep selected branches at the top. -->

### B1: [placeholder — replace with first real branch]
- **Status:** active
- **Parent:** root
- **Predicted outcome:** TBD
- **Confidence:** LOW
- **Process reward proxy:** TBD
- **Proxy value:** TBD
- **Evidence:** none
- **Blocked by:** U1
- **Next step:** TBD
- **Estimated cost:** TBD
- **Children:** none

---

## Eliminated branches

<!-- Move eliminated branches here with a one-line reason. Full traces go to `archive.md`. -->

---

## Completed branches

<!-- Move completed branches here. -->
