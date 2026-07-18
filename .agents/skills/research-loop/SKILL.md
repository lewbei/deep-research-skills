---
name: research-loop
description: Iterative deep-research loop for competition and research-heavy tasks. Research → execute 1 bounded, falsifiable unit of work → research → execute... Reads the unknowns registry each round.
argument-hint: "[objective]"
triggers:
  - user
  - model
---

You are running an **interleaved research-and-execute loop**. The full process is in `.agents/skills/research-loop/docs/research-workflow.md` in the plugin directory — read it now if you haven't this session.
You MUST use the `./drs` CLI tool to initialize, track, and validate all workflow state transitions.

## Your job

1. **If this is the first invocation** (no `unknowns-registry.md` exists yet):
   - **Initialize the session using the CLI:**
     Run `./drs init --total-minutes <minutes> --kind <hard/soft>`
     This automatically instantiates the state directory and populates all compliant templates.
   - Run Phase 1 (extract goal & constraints; write to `unknowns-registry.md`, `time-budget.md`, etc.).
   - Advance phase via `./drs transition 1 2` to run Phase 2 (validate feasibility — bounded landscape scans).
   - Advance phase via `./drs transition 2 3` to run Phase 3 (broad research sweep — map the landscape).
   - Then enter the loop.

2. **If artifacts already exist** (loop is resuming):
   - Read `unknowns-registry.md`, `hypothesis-tree.md`, `decision-log.md`, `time-budget.md`, `proxy-log.md`, `human-escalation-policy.md`, `probe-registry.md`, `landscape-table.md`.
   - Run `./drs status` to confirm the active state.
   - Resume at Phase 3.5 (budget checkpoint) then Phase 4.

## The loop (Phases 3.5-9)

You must run `./drs transition <from> <to>` for all phase transitions. The state-machine enforces graph checks and restricts research phases depending on the budget mode.

Each iteration:

1. **Budget checkpoint (Phase 3.5):** Run `./drs budget` to calculate elapsed pacing and transition budget modes. If a threshold is crossed, follow `time-budget.md` rules and escalate if needed.
2. **Check `unknowns-registry.md` (Phase 4):** Transition via `./drs transition 3.5 4`. Pick the highest-priority open unknown that blocks a decision.
3. **Research it (Phase 5):** Transition via `./drs transition 4 5`. Use `@skills:landscape-scan` or `@skills:deep-dive`. Update the registry with findings.
4. **Hypothesis validation (Phase 6):** Transition via `./drs transition 5 6`. Update `hypothesis-tree.md` branches. Ensure P0/P1 branches have a `proxy-log.md` entry.
5. **Pick the next execution step (Phase 7):** Transition via `./drs transition 6 7` (or `./drs transition 4 7` if no new research was needed). Populate `mega-plan.md`.
6. **Execute 1 bounded unit of work (Phase 8):** Transition via `./drs transition 7 8`. Execute the probe/code, implement, test, and measure. Record results.
7. **Learn & Validate Proxies (Phase 9):** Transition via `./drs transition 8 9`. Run `./drs proxy <id> --add <val>:<true>` to calculate Spearman rank correlation and validate proxies.
8. **Loop back or Conclude:** Run `./drs transition 9 3.5` to start a new loop iteration, or `./drs transition 9 10` to complete the session. Run `./drs validate` to ensure 100% schema compliance.

## When to stop the loop

- **Goal reached** — the success criterion is met. Report and stop.
- **All approaches exhausted** — every branch was tried and killed. Report what was learned.
- **No blocking unknowns remain** and the current approach is working — stop researching, just execute the remaining plan.
- **Time budget exceeded** — follow `time-budget.md` `last-stand` or `halt` rules.
- **Human escalation triggered** — halt and wait for user input.

## Critical rules

- **You are the only writer.** Subagents (`landscape-scan`, `deep-dive`, `verify`) are read-only. Integrate their outputs into artifacts yourself.
- **Always update `unknowns-registry.md`** when a new unknown is discovered or an existing one is answered.
- **Execute only 1 bounded, falsifiable unit of work per loop iteration.** Do not batch unrelated experiments, but allow related tests/measurements to remain in one atomic experiment.
- **Use bounded subagents for research.** Pass explicit budget envelopes (wall time, max sources, max output words, max probes).
- **Record everything.** If an unknown is discovered during execution and not recorded, it will be lost.
- **Prefer primary sources.** Follow claims to the paper, code, or documentation that owns them.
- **Prune ruthlessly.** If an approach is killed, record why in `decision-log.md` and move on. No sunk-cost fallacy.
- **Validate proxies before committing.** A `candidate` proxy may not drive a P0/P1 decision.
- **Run probes before implementation.** Pending probes for P0/P1 unknowns must execute in Phase 8.
- **Escalate early.** Preventive triggers in `human-escalation-policy.md` fire before waste occurs.

## Output per iteration

After each loop iteration, report:
- Current budget mode and elapsed/remaining time.
- Which unknown was researched and what was found (including verifier verdict).
- Which step was executed and what the result was.
- Proxy status and any correlation update.
- What new unknowns surfaced.
- Any escalations triggered and user decisions.
- The next planned action.
