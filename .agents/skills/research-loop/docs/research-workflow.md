# Research-First Workflow: Interleaved Deep Research

A standalone workflow for competition, hackathon, and research-heavy tasks. The core idea: **research just enough for the next step, execute it, learn, research the next step.** Each research round is informed by real execution results.

This is an **interleaved loop**, not upfront-then-execute:

```
research → do 1 bounded unit of work → research → do 1 bounded unit of work → ...
```

The `@skills:research-loop` skill calls this document. It also works standalone — any agent or human can follow it without the skill.

---

## When to use this

| Signal | Use this workflow |
|--------|-------------------|
| Goal needs feasibility validation (can I reach X?) | Yes |
| Multiple competing approaches exist | Yes |
| Success depends on landscape knowledge (competitions, papers, SOTA) | Yes |
| Main work is finding the right approach, not just implementing | Yes |
| Each step's results change what the next step should be | Yes |

---

## Core artifacts

These persist as files throughout the workflow and survive across sessions:

| Artifact | File | Purpose |
|----------|------|---------|
| **Unknowns registry** | `unknowns-registry.md` | Every open question, unknown, and thing-to-investigate. Grows across iterations. The research loop reads this each round to decide what to research next. |
| **Landscape table** | `landscape-table.md` | All known solutions with scores, approaches, models, training methods. |
| **Hypothesis tree** | `hypothesis-tree.md` | All considered approaches with predicted outcomes, confidence, and evidence. MCTS-like branching. |
| **Decision log** | `decision-log.md` | What was selected, what was pruned, and why. |
| **Context archive** | `archive.md` | Compressed summaries of eliminated branches. Full technical traces are moved here so active artifacts stay small and avoid the "Lost in the Middle" attention degradation. |
| **Probe registry** | `probe-registry.md` | Tracks pending probe scripts, what they test, and their results. Carries probes from research (Phase 5) to execution (Phase 8). |
| **Time budget** | `time-budget.md` | Total budget, elapsed time, current mode, and threshold log. Updated every loop iteration. |
| **Session state** | `.deep-research/session-state.json` | Machine-readable budget state for fast parsing. Created from `skills/research-loop/templates/session-state.json`. |
| **Proxy log** | `proxy-log.md` | Process reward proxies with validation status, correlation evidence, and gaming risk. |
| **Human escalation policy** | `human-escalation-policy.md` | Preventive and reactive triggers, pre-approved conditions, and escalation log. |
| **Mechanism files** | `approaches/<name>/mechanism.md` | Detailed how-it-works for each approach: architecture, math, flowchart, training, inference. |
| **Implementation plan** | `mega-plan.md` | The concrete plan for the selected approach. Created from template in Phase 1; populated in Phase 7. |

### State-lock rule (single-writer)

Only one agent may write to any core artifact at a time. The orchestrator (`research-loop`) is the only writer that updates:
- `unknowns-registry.md`
- `hypothesis-tree.md`
- `decision-log.md`
- `archive.md`
- `landscape-table.md`
- `probe-registry.md`
- `time-budget.md`
- `proxy-log.md`
- `human-escalation-policy.md`
- `.deep-research/session-state.json`
- `approaches/<name>/mechanism.md`
- `probes/<unknown-id>.py`

Subagents (`landscape-scan`, `deep-dive`) are **read-only**. They return their findings in their response; the orchestrator integrates them into the artifacts.

**Why this matters:** If two agents write to the same markdown files concurrently, the registry, hypothesis tree, and decision log will drift. Even in a single-agent session, ambiguity about whether the subagent already updated an artifact causes missed updates or duplicate entries.

**Enforcement:**
- Subagent SKILL.md files explicitly state "Do not write any file." Their `allowed-tools` do not include `write` or `edit`.
- The orchestrator finishes one subagent call, integrates its output, then starts the next. No parallel subagent writes.
- If a future version supports parallel subagents, replace this rule with a `state-lock.json` or a lightweight SQLite runtime state store.

*Future upgrade:* If the plugin is used with many parallel subagents, replace this single-writer rule with a SQLite runtime state store and export artifacts asynchronously. For the current design, single-writer is sufficient and simpler.

---

## The interleaved loop

```
Phase 1: Extract goal & constraints (once)
→ Phase 2: Validate feasibility (once, or re-validate when evidence changes)
→ Phase 3: Broad research sweep (once, or re-sweep when a new area is discovered)
→ ┌─── INTERLEAVED LOOP ───────────────────────────────────┐
  │                                                          │
  │  3.5. Budget checkpoint                                  │
  │  → update time-budget.md + session-state.json            │
  │                                                          │
  │  4. Check unknowns registry                              │
  │  → pick highest-priority unknown that blocks a decision  │
  │                                                          │
  │  5. Research that unknown (deep-dive)                    │
  │  → extract mechanism, math, flowchart                    │
  │  → update mechanism files + landscape table              │
  │  → mark unknown as answered (or add new unknowns)        │
  │                                                          │
  │  6. Update hypothesis tree                               │
  │  → add/refine branches based on new knowledge            │
  │  → re-score predictions                                  │
  │  → prune branches that are now eliminated                │
  │                                                          │
  │  7. Pick next execution step                             │
  │  → from the highest-priority hypothesis branch           │
  │  → define the step, its success criterion, kill criterion │
  │                                                          │
  │  8. Execute 1 bounded unit of work                       │
  │  → implement, test, measure                              │
  │  → record results                                        │
  │                                                          │
  │  9. Learn from execution                                 │
  │  → what worked? what didn't?                             │
  │  → what new unknowns surfaced? → add to registry         │
  │  → does the hypothesis tree need updating?               │
  │  → does the goal need re-validation?                     │
  │                                                          │
  │  └── back to 3.5 (loop) ────────────────────────────────┘
  │
  → Phase 10: Done (goal reached or all approaches exhausted)
```

---

## Phase 1: Extract goal & constraints (once)

**Input:** The user's prompt.

**Output:** A structured goal statement + initial unknowns.

1. **Pre-condition:** all core artifacts are created from templates before Phase 1 starts (`unknowns-registry.md`, `landscape-table.md`, `hypothesis-tree.md`, `decision-log.md`, `archive.md`, `probe-registry.md`, `time-budget.md`, `proxy-log.md`, `human-escalation-policy.md`, `.deep-research/session-state.json`, and optionally `mega-plan.md`).

2. Parse the prompt into:
   - **Target:** specific outcome (e.g., "1250 Elo on the Kaggle Pokemon simulation leaderboard")
   - **Context:** competition/platform/task
   - **Constraints:** time, compute, allowed tools/data, submission format
   - **Implicit preferences:** language, framework, model size (ask if unclear)

3. Identify initial unknowns and add them to `unknowns-registry.md`:
   - "Is 1250 Elo achievable?" → P0 (blocks everything)
   - "What approaches have been tried?" → P1
   - "What compute is available?" → P1
   - "What's the submission format?" → P1

4. **Extract the time budget** and populate `time-budget.md` and `.deep-research/session-state.json`:
   - Ask the user (or infer from the prompt) for the total budget `T` in minutes and whether it is `hard` or `soft`.
   - If unspecified, default to `T = 120` minutes, `kind = soft`.
   - Set default research allocation `R = 40%`, execution allocation `E = 60%`.
   - If the goal is clearly research-only, set `R = 70%`, `E = 30%`.
   - If the goal is clearly execution-heavy (hackathon / Kaggle), set `R = 25%`, `E = 75%`.

5. State the goal as a **hypothesis to validate**:
   - "H0: 1250 Elo is achievable with approach X, given constraints Y."

**Stop condition:** goal parsed, constraints explicit, initial unknowns in registry, budget populated in `time-budget.md`.

---

## Phase 2: Validate feasibility (once, re-validate when evidence changes)

**Input:** Structured goal + unknowns registry + `time-budget.md`.

**Output:** Feasibility verdict backed by evidence.

1. **Check budget:** record the start of this phase in `time-budget.md`. If elapsed budget > 25% and this phase has not completed, escalate via `human-escalation-policy.md` (trigger P1/P6).

2. **Leaderboard scan:** run `@skills:landscape-scan` with scope `competition-surface` and budget envelope (8 min, 6 sources, 250 words).
   - Near top → STRETCH. Near median → ACHIEVABLE. Above top → UNACHIEVABLE. No leaderboard → UNKNOWN.

3. **Prior-solution scan:** run `@skills:landscape-scan` with scope `public-code` and budget envelope (10 min, 8 sources, 300 words).
   - For each: extract score, approach, model, training, compute, time.
   - Record in `landscape-table.md`.

4. **Writeup scan (optional):** run `@skills:landscape-scan` with scope `writeups-papers` and budget envelope (10 min, 6 sources, 300 words) if research budget allows.

5. **Verdict:** ACHIEVABLE / STRETCH / UNACHIEVABLE / UNKNOWN.
   - Mark the "Is 1250 Elo achievable?" unknown as `answered` in the registry with the verdict + evidence.
   - If feasibility shifts to UNACHIEVABLE/UNKNOWN, trigger `human-escalation-policy.md` P6.

6. **Re-validation trigger:** if Phase 9 reveals the landscape is different than expected, re-run this phase.

**Stop condition:** verdict stated with ≥2 independent evidence packets in `landscape-table.md` that directly address target achievability.

**Time cap:** this phase must complete within the research allocation `R` of the total budget; if it cannot, record partial evidence and escalate.

---

## Phase 3: Broad research sweep (once, re-sweep when new area discovered)

**Input:** Feasibility verdict + landscape table.

**Output:** Categorized approach tree.

This is **breadth-first** research. Map the landscape, don't dive deep yet.

1. **Competition research:** Kaggle discussions, public code, bot strategies, leaderboard progression.
2. **Code research:** GitHub repos for the competition + approach.
3. **Categorize all approaches into a tree** (rule-based, search-based, ML-based, hybrid).
4. **For each category:** who used it, what score, strengths, weaknesses, compute needs.
5. **Add unknowns to registry:** for each approach that looks promising but unclear, add an unknown ("How does MCTS handle partial observability in this sim?" → P1).

**Stop condition:** every major approach category has ≥1 source with score + strengths/weaknesses.

**Re-sweep trigger:** if Phase 9 discovers an approach category not in the tree, re-run this phase for that category only.

---

## Phase 3.5: Budget checkpoint (every iteration)

**Input:** `time-budget.md`, `.deep-research/session-state.json`, current phase.

**Output:** Updated budget ledger + current mode + recommended action.

1. At the start of every iteration (Phase 3.5), update the ledger:
   - Record the previous phase's start/end timestamps and duration.
   - Categorize as `research` (Phases 1-6) or `execution` (Phases 7-9).
   - Recompute elapsed percentages.

2. Determine current mode from `time-budget.md` decision rules.

3. If a new threshold (25%, 50%, 75%, 90%, 100%) has been crossed, run the corresponding rule and record it in the threshold log.

4. If the recommended action is `escalate`, follow `human-escalation-policy.md`.

5. Write updated state to `time-budget.md` and `.deep-research/session-state.json`.

**Stop condition:** budget state is current and mode is explicit before Phase 4 begins.

---

## Phase 3.5-9: The interleaved loop

This is the core of the workflow. Each iteration is one pass through steps 3.5-9.

### Phase 4: Check unknowns registry

**Input:** `unknowns-registry.md`

**Output:** The next unknown to research.

1. Read the registry.
2. Find all `open` entries.
3. Sort by priority (P0 first, then P1, then P2).
4. Among P0/P1, pick the one that blocks the most decisions or the next execution step.
5. If no P0/P1 unknowns remain, either:
   - Pick a P2 (if research budget allows), or
   - Skip to Phase 7 (pick next execution step) — there's nothing blocking to research.

**Stop condition:** one unknown selected for research, or "no blocking unknowns" verdict.

---

### Phase 5: Research that unknown (deep-dive)

**Input:** The selected unknown from Phase 4.

**Output:** Answer + mechanism extraction + updated artifacts.

1. **Choose depth and budget for this unknown:**
   - `answer-only` for yes/no or factual lookups.
   - `mechanism-sketch` for high-level understanding.
   - `full-mechanism` only for P0/P1 blocking unknowns where the approach must be implementable from notes.
   - Pass a budget envelope: wall time, max sources, max output words, max probes.

2. **Run the bounded deep-dive subagent:**
   - Provide `unknown_id`, `question`, `context`, `depth`, `budget`, and `stop_when`.
   - The subagent returns a `subagent-summary.md` (for `answer-only`/`mechanism-sketch`) or full `mechanism.md` content (for `full-mechanism`).

3. **Invoke the verifier for P0/P1 unknowns before committing:**
   - Extract the `claim_set` from the deep-dive or landscape-scan output (the YAML block with `claim_id`, `claim_text`, `original_evidence`, `claim_type` for each claim).
   - Call `@skills:verify` with the source, `unknown_id`, `claim_set`, `verdict_type: pre-commit`, and a budget (e.g., 10 minutes, source only).
   - If verifier returns `aligned` or `minor-drift`, record the `Verifier verdict` in `unknowns-registry.md` and proceed.
   - If `major-drift` or `inconclusive`, record the verdict, downgrade the unknown, create a follow-up unknown if needed, and do not commit.

4. **Update artifacts:**
   - Mark the unknown in the registry with triangulation status and verifier verdict.
   - If the deep-dive returned a probe script, add it to `probe-registry.md` with status `pending` and link it to the unknown.
   - Update `landscape-table.md` with any new solutions found.
   - **Add any new unknowns** that surfaced during research to the registry.

**Stop condition (triangulation requirement):**
- For **P0/P1 unknowns**: stop when the answer is corroborated by ≥2 independent primary sources (`verified`), OR 1 authoritative source + 1 empirical micro-validation (`verified`). If only 1 source found after exhaustive search, mark `provisional` and inject a Phase 8 step to empirically test the claim before committing.
- For **P2/P3 unknowns**: stop when answered with ≥1 primary source (`verified` if authoritative, `provisional` otherwise).
- Mark `eliminated` if the question became irrelevant.

**Triangulation bypass rule (anti-deadlock):** Do not search forever. After 3 distinct search attempts across different channels (Kaggle, arXiv, GitHub, official docs, paper, code), if no second source exists:
- Mark the P0/P1 unknown as `provisional-high-risk`.
- Define a **probe script** (small executable test) that validates the claim directly.
- Execute the probe in Phase 8. If it passes → `empirically validated`; if it fails → `eliminated` and prune dependent branches.
- Always inform the user when a P0/P1 unknown is resolved via bypass.

*Source: MoAgent framework — evidence triangulation achieves 4x F1 improvement over single-source ReAct agents (ai4d3.github.io/2025/papers/20_MoAgent).*

---

### Phase 6: Update hypothesis tree

**Input:** New knowledge from Phase 5 + existing `hypothesis-tree.md`.

**Output:** Updated hypothesis tree.

1. **Add new branches** if a new approach was discovered.
2. **Refine existing branches** if the mechanism is now better understood (update predicted score, confidence, and quantitative proxy metric).
3. **Prune branches** that are now eliminated (e.g., "MCTS doesn't work because the sim is partially observable" → prune MCTS branch, record reason in decision log).
4. **Re-score predictions** based on new evidence.
5. **Compress eliminated branches:** move the full technical trace to `archive.md` and replace the active entry with a single sentence ("Approach X failed due to Y, do not attempt"). This prevents artifact bloat and the "Lost in the Middle" attention degradation.

**Quantitative proxy metric:** every branch must have a measurable proxy (e.g., predicted loss, execution latency, heuristic reward score, partial progress metric), not just a binary success prediction. This enables continuous confidence scoring rather than pass/fail.

**Stop condition:** tree is consistent with current knowledge. No branch contradicts available evidence. Active tree contains only viable branches + their immediate context.

*Source: "Lost in the Middle" (Liu et al. 2023, Stanford/Samaya AI) — LLMs exhibit a U-shaped attention curve with 20-30% accuracy drop for information in the middle of long contexts. Artifact bloat directly degrades the agent's ability to reason over its own state.*

---

### Phase 7: Pick next execution step (Abstract → Concrete → Execute)

**Input:** Updated hypothesis tree + unknowns registry.

**Output:** One concrete step to execute, with abstract alignment, success + kill criteria, and process reward proxy.

1. **Select the highest-priority hypothesis branch** (highest predicted score with acceptable cost and ≥MEDIUM confidence).

2. **Abstract alignment:** before defining the concrete step, explicitly state how this step logically advances the overarching goal from Phase 1. Write one sentence: "This step serves the goal by [logical connection to the outcome]." This prevents logic drift — the concrete step must be traceable to the abstract objective, not just to the previous step.

3. **Define the concrete step:** map the abstract alignment to specific code/API calls or experiments.
   - What specifically to implement or test.
   - What is the minimum viable test? (simplest thing that validates the hypothesis)

4. **Define criteria:**
   - **Success criterion:** what result confirms this branch? (e.g., "MCTS rollout achieves 1000+ Elo in 100 games")
   - **Process reward proxy:** a measurable metric to gauge partial progress (e.g., "script runs and feature variance > 0.8", "search depth reaches 3 with valid moves"). This enables continuous confidence scoring rather than binary pass/fail.
   - **Kill criterion:** what result kills this branch? (e.g., "after 500 self-play games, Elo < 900 → abandon")

5. **Populate `mega-plan.md`:** write the concrete step into the implementation plan (selected approach, milestone, required artifact, objectives, gate, and known research gaps).

6. **If no branch is ready for execution** (all have LOW confidence or blocking unknowns), go back to Phase 3.5 to update the budget, then Phase 4 to research more. If this is the second consecutive Phase 3.5→7→3.5 cycle, escalate via `human-escalation-policy.md` P3 instead of looping again.

**Stop condition:** one step defined with abstract alignment, concrete implementation, success criterion, process reward proxy, and kill criterion, and `mega-plan.md` updated.

*Source: ACE architecture (NDSS 2026, arXiv 2504.20984) — separating abstract planning from concrete execution prevents intermediate-output corruption and improves robustness. The security benefit (0% attack success on InjecAgent) is a side effect of the structural separation; the primary transferable idea is the abstract-concrete boundary itself.*

---

### Phase 8: Execute 1 bounded unit of work

**Input:** The step from Phase 7 + `probe-registry.md` with pending probes.

**Output:** Execution results + updated probe registry.

1. **Run pending probes first.** Before executing the chosen implementation step, run all pending probes for the active branch's P0/P1 unknowns. Check `probe-registry.md` for probes with status `pending` linked to the current branch's unknowns.
   - If a probe passes → mark the unknown `empirically-validated` in the registry and update the probe registry to `passed`.
   - If a probe fails → mark the unknown `eliminated` in the registry, update the probe registry to `failed`, and prune the branch before any implementation begins.
   - If a probe cannot be run due to environment constraints → document the blocker, mark the probe `blocked`, and escalate to the user for P0/P1 unknowns.

2. **Implement the step** (write code, run experiment, build prototype).
3. **Run the success criterion check.**
4. **Record results:**
   - What was the outcome? (score, metric, observation)
   - Did it meet the success criterion? (pass/fail)
   - Did it hit the kill criterion? (kill/continue)
   - What worked? What didn't?
   - **What new unknowns surfaced?** → add to `unknowns-registry.md`
   - **What did we learn about the hypothesis?** → update hypothesis tree if needed

**Stop condition:** step is complete (pass, fail, or kill).

---

### Phase 9: Learn from execution

**Input:** Execution results from Phase 8.

**Output:** Updated artifacts + loop decision.

1. **Update unknowns registry:**
   - Add any new unknowns that surfaced during execution.
   - Mark any unknowns that were answered by execution (e.g., "Does the sim support X?" → answered by trying it, mark as `empirically validated`).

2. **Update proxy-log.md:**
   - Record the new proxy value and true outcome for this step.
   - If at least 5 paired observations exist, compute Spearman correlation (keep as candidate/provisional if fewer than 5 observations).
   - Promote proxy from `candidate` to `validated` if |ρ| ≥ 0.7, sample size ≥ 5, and sign matches intended direction.
   - Mark proxy `degraded` if 0.4 ≤ |ρ| < 0.7 or if one observation shows proxy gain ≥20% with true outcome gain <5% (or opposite).
   - Mark proxy `rejected` if |ρ| < 0.4 or sign is wrong.
   - A `degraded` proxy requires recalibration or a new proxy before the next P0/P1 decision.

3. **Update hypothesis tree with continuous scoring:**
   - Use only `validated` proxies for P0/P1 confidence updates. `candidate` proxies may be used only for exploration.
   - If the step passed → increase confidence in this branch using the validated proxy score, plan the next step on it.
   - If the step failed but kill criterion not met → debug and retry (max 2 retries before switching).
   - If kill criterion met → switch to secondary approach (record in decision log).
   - If a new approach idea emerged → add as new branch.
   - **Update the confidence label** of the branch based on the process reward proxy, not just pass/fail. Use the mapping from `skills/research-loop/templates/hypothesis-tree.md`: LOW (0.0–0.3), MEDIUM (0.3–0.6), HIGH (0.6–1.0). Keep MEDIUM+ branches active; prune LOW branches after ≥2 attempts. The numeric score is an optional aid; the qualitative label is the source of truth.

4. **Human escalation triggers:** consult `human-escalation-policy.md`. The following reactive triggers halt the loop and ask the user:
   - R1: highest-priority branch killed AND secondary approach also fails.
   - R2: 3 consecutive steps with zero measurable progress (proxy flat) OR 2 hours with no absolute progress.
   - R3: P0 unknown marked `provisional` and cannot be empirically validated.
   - R4: new P0 unknown invalidates current branch's core assumption.
   - R5: probe for P0/P1 unknown failed twice.
   - R6: external dependency unavailable.
   - R7: safety/ethics/rules boundary crossed.
   - R8: exceptional success (already above target).

   *Source: ScienceAgentBench (Chen et al. 2024, arXiv 2410.05080) — best-performing agents solve only 32.4% of scientific tasks independently, 34.3% with expert knowledge. Full autonomy is a fallacy; human-in-the-loop is required for structural walls.*

5. **Re-validate goal if needed:**
   - If results are far below predictions → is the goal still achievable? Re-run Phase 2 if evidence changed significantly.

6. **Loop decision:**
   - If goal is reached → Phase 10 (done).
   - If all approaches are exhausted → Phase 10 (done, report what was learned).
   - If human escalation triggered → halt and wait for user input.
   - If `time-budget.md` current mode is `halt` → Phase 10 (done).
   - If current mode is `last-stand` → produce a submission/artifact from the best branch, then Phase 10.
   - Otherwise → back to Phase 3.5 (Budget checkpoint).

---

## Phase 10: Terminal reflection & human handoff

**Output:** Final report with interactive handoff.

1. **What was achieved** (final score / outcome).
2. **The exact mechanism of the working approach** (from mechanism files — architecture, math, training, inference).
3. **A compressed list of falsified hypotheses** (from `archive.md` — "Approach X failed due to Y, do not attempt"). This saves the human from repeating mistakes.
4. **Remaining un-triangulated unknowns** (from registry — unknowns still marked `provisional` or `open`).
5. **What would be done differently** (retrospective).

This is a handoff, not just a report. The user should be able to pick up from here — either by continuing the loop, adjusting the goal, or taking the findings to a different task.

---

## Stopping rules for research

Research does not continue indefinitely. At each Phase 5 (deep-dive):

- **Stop researching** when the unknown is triangulated (P0/P1: ≥2 sources or 1 source + empirical validation; P2/P3: ≥1 source).
- **Stop the entire research phase** when no P0/P1 unknowns remain and the hypothesis tree has ≥1 branch with MEDIUM+ confidence.
- **Force-commit** if research has consumed >50% of the total time budget — pick the best-available approach and start executing.

Analysis paralysis is a failure mode. The interleaved loop exists to prevent it: research just enough for the next step, then execute and learn.

---

## File structure

```
project-root/
├── unknowns-registry.md           ← the living question queue (core artifact)
├── landscape-table.md             ← all known solutions + scores
├── hypothesis-tree.md             ← all approaches with predictions (active only)
├── decision-log.md                ← what was selected, what was pruned
├── archive.md                     ← compressed summaries of eliminated branches
├── mega-plan.md                   ← the implementation plan (if needed)
├── approaches/
│   ├── mcts-pokemon/
│   │   ├── mechanism.md           ← architecture, math, flowchart
│   │   ├── source.md              ← paper/writeup summary
│   │   └── notes.md               ← implementation notes
│   └── rl-self-play/
│       └── ...
└── papers/
    └── markdown/
        └── (extracted paper texts)
```
