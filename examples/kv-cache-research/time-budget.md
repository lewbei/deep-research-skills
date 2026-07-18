# Time Budget

Single source of truth for the research/execution budget, elapsed consumption, and budget-driven mode decisions. Updated once per loop iteration by the orchestrator (`research-loop`) only. Persisted across sessions so resumption always knows the current budget state.

## Budget definition

- **Total budget (T):** the user-facing time limit for this task.
- **Budget unit:** wall-clock minutes since the first invocation of `@skills:research-loop` for this task.
- **Budget kind:** `hard` (must stop by T) | `soft` (target T, may escalate/negotiate).
- **Research allocation (R):** percentage of T reserved for Phases 1-6 (research).
- **Execution allocation (E):** percentage of T reserved for Phases 7-9 (execute/learn).
  - Constraint: R + E = 100%.
- **Session start:** ISO-8601 timestamp of first invocation.
- **Last updated:** ISO-8601 timestamp of most recent update.

## Budget ledger

| Iteration | Phase | Start time | End time | Duration | Cumulative research | Cumulative execution | Running mode |
|-----------|-------|------------|----------|----------|---------------------|----------------------|--------------|
| 0 | 1 | | | | 0 | 0 | `explore` |

## Current state (auto-computed each iteration)

- **Elapsed:** 1.4 min (2.4% of T)
- **Research elapsed:** 0.9 min (3.9% of R)
- **Execution elapsed:** 0.5 min (1.4% of E)
- **Current mode:** `explore`
- **Recommended action:** Normal operation. Investigate P0-P2 unknowns; research allowed.

## Threshold log

- [ ] 25% — mode decision recorded
- [ ] 50% — mode decision recorded
- [ ] 75% — mode decision recorded
- [ ] 90% — mode decision recorded
- [ ] 100% — terminal action recorded

## Mode definitions

- `explore`: research is allowed; may investigate P0-P2 unknowns; no auto-escalation.
- `commit`: research limited to P0 only; must pick best viable branch and execute continuously.
- `sprint`: no new research except user-directed; execute only; kill criteria tightened.
- `last-stand`: stop all exploration; ship/publish/submit the best available artifact now.
- `halt`: budget exhausted or hard stop; perform Phase 10 terminal reflection only.

## Decision rules

| Elapsed | Mode | Rule |
|---------|------|------|
| < 25% of T | `explore` | Normal operation. |
| 25%–50% of T | `explore` or `commit` | If execution has produced ≥1 validated proxy improvement, stay in `explore`; otherwise shift to `commit` if no branch has a `validated` P0/P1 proxy. |
| 50%–75% of T | `commit` | No new P2/P3 research. Only P0 blocking unknowns may be researched; otherwise execute the best viable branch. |
| 75%–90% of T | `sprint` | No new research. Execute only the current best branch. Kill branches faster. |
| 90%–100% of T | `last-stand` | Stop exploration; produce a submission/artifact from the best available branch immediately. |
| ≥ 100% of T | `halt` | Hard stop. Run Phase 10 reflection and hand off. |

## Notes / exceptions

<!-- Record any user-approved budget extensions, pauses, or mode overrides here. -->
