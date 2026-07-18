---
name: research-loop
description: Iterative deep-research loop for competition and research-heavy tasks. Research → execute 1 bounded, falsifiable unit of work → research → execute... Reads the unknowns registry each round.
argument-hint: "[objective]"
triggers:
  - user
  - model
---

You are running an **interleaved research-and-execute loop**. The full process is in `.agents/skills/research-loop/docs/research-workflow.md` in the plugin directory — read it now if you haven't this session.

## Your job

1. **If this is the first invocation** (no `unknowns-registry.md` exists yet):
   - **Create all core artifacts from templates first:**
     - `unknowns-registry.md` (from `.agents/skills/research-loop/templates/unknowns-registry.md`)
     - `landscape-table.md` (from `.agents/skills/research-loop/templates/landscape-table.md`)
     - `hypothesis-tree.md` (from `.agents/skills/research-loop/templates/hypothesis-tree.md`)
     - `decision-log.md` (from `.agents/skills/research-loop/templates/decision-log.md`)
     - `archive.md` (from `.agents/skills/research-loop/templates/archive.md`)
     - `probe-registry.md` (from `.agents/skills/research-loop/templates/probe-registry.md`)
     - `time-budget.md` (from `.agents/skills/research-loop/templates/time-budget.md`)
     - `proxy-log.md` (from `.agents/skills/research-loop/templates/proxy-log.md`)
     - `human-escalation-policy.md` (from `.agents/skills/research-loop/templates/human-escalation-policy.md`)
     - `.deep-research/session-state.json` (from `.agents/skills/research-loop/templates/session-state.json`)
     - `mega-plan.md` (empty, from `.agents/skills/research-loop/templates/mega-plan.md`; populated in Phase 7)
   - Run Phase 1 (extract goal & constraints; write to `unknowns-registry.md`, `time-budget.md`, etc.).
   - Run Phase 2 (validate feasibility — bounded landscape scans).
   - Run Phase 3 (broad research sweep — map the landscape).
   - Then enter the loop.

2. **If artifacts already exist** (loop is resuming):
   - Read `unknowns-registry.md`, `hypothesis-tree.md`, `decision-log.md`, `time-budget.md`, `proxy-log.md`, `human-escalation-policy.md`, `probe-registry.md`, `landscape-table.md`.
   - Resume at Phase 3.5 (budget checkpoint) then Phase 4.

## The loop (Phases 3.5-9)

Each iteration:

1. **Budget checkpoint (Phase 3.5).** Update `time-budget.md` and `.deep-research/session-state.json`. Determine current mode (`explore`, `commit`, `sprint`, `last-stand`, `halt`). If a threshold is crossed, follow `time-budget.md` decision rules and escalate via `human-escalation-policy.md` if needed.

2. **Check `unknowns-registry.md`** — pick the highest-priority open unknown that blocks a decision, respecting the current mode.

3. **Research it** — use `@skills:landscape-scan` (scoped, bounded) or `@skills:deep-dive` (bounded depth) to investigate. Pass an explicit budget envelope. Update the registry with the answer and verifier verdict.

4. **Invoke verifier for P0/P1 unknowns** before marking `verified`:
   - Extract the `claim_set` from the deep-dive or landscape-scan output.
   - Call `@skills:verify` with the source, `unknown_id`, `claim_set`, `verdict_type: pre-commit`, and a budget.
   - If verifier returns `aligned` or `minor-drift`, record the verifier verdict and proceed.
   - If `major-drift` or `inconclusive`, downgrade the unknown, record the verdict, create a follow-up unknown if needed, and do not commit.

5. **Update `hypothesis-tree.md`** — add/refine/prune branches based on new knowledge. Ensure every P0/P1 branch has a `proxy-log.md` entry before confidence scoring.

6. **Pick the next execution step (Phase 7)** — from the highest-priority hypothesis branch (≥MEDIUM confidence, acceptable cost). Write the abstract alignment sentence, define the concrete step, set success / kill criteria, and define a process reward proxy. Check `human-escalation-policy.md` preventive triggers. Populate `mega-plan.md` with the concrete step.

7. **Execute 1 bounded unit of work** — run pending probes first, then implement, test, measure. Record results in `proxy-log.md`.

8. **Learn** — update proxy correlation, hypothesis tree, unknowns registry, decision log. Decide: continue loop, switch approach, escalate, or done?

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
