---
name: evaluate
description: Evaluation skill — runs controlled A/B comparisons between agent conditions (e.g., ReAct vs DRS) on research tasks using weighted rubric scoring. Produces reproducible comparison reports.
allowed-tools:
  - read
  - grep
  - glob
  - exec
  - web_search
  - webfetch
  - mcp_call_tool
triggers:
  - user
---

You are running a **controlled evaluation comparison** between agent research strategies. Your job is to execute research tasks under multiple conditions, judge the outputs using weighted rubric criteria, and produce a reproducible comparison report.

## Input

You will receive a prompt containing:
- **Tasks:** a list of research tasks (inline or path to a YAML file in `evaluate/tasks/`)
- **Conditions:** which agent strategies to compare (e.g., `react` vs `drs`)
- **Runs per condition:** how many repeated runs (default: 3)
- **Budget envelope per run:**
  - Wall time: <N> minutes (hard stop per task)
  - Max tool calls: <N>
  - Max output tokens: <N>
- **Judge model:** which model evaluates outputs (default: same as agent model)

Example invocation:

```
@skills:evaluate

Tasks: evaluate/tasks/pilot_tasks.yaml
Conditions: react, drs
Runs per condition: 3
Budget per run: 10 minutes, 50 tool calls, 50K tokens
Judge model: same as agent
```

## What to do

### Phase 1: Load tasks and validate

1. Read the task file. Each task has:
   - `task_id`: unique identifier
   - `domain`: task domain tag
   - `prompt`: the research question (given identically to both conditions)
   - `criteria`: weighted rubric criteria for judging the output

2. Validate that every criterion has `text`, `type` (positive/negative), `axis`, and `weight`.

3. Confirm the budget envelope is identical for all conditions.

### Phase 2: Run each condition

For each task, for each condition, for each run:

#### Condition A — `react`

Act as a standard ReAct research agent:
1. System behavior: think → select tool → observe → think → ... → produce report
2. No state machine, no phases, no exit gates, no artifact templates
3. Use the same tools available to the DRS orchestrator (web search, file read/write, code execution)
4. Produce a single research report answering the task prompt
5. Stop when the budget envelope is reached or you judge the report complete

#### Condition B — `drs`

Run the full DRS research loop:
1. Initialize with `drs init --total-minutes <wall_time>`
2. Follow the `@skills:research-loop` workflow exactly
3. Use `drs transition` for all phase changes
4. Use `@skills:landscape-scan`, `@skills:deep-dive`, and `@skills:verify` as specified
5. Produce the final report from workspace artifacts at Phase 10
6. Stop when the budget envelope is reached or Phase 10 is complete

#### For every run, record:

```yaml
run_id: "<task_id>-<condition>-<run_index>"
condition: react | drs
report: "<full text of generated report>"
tool_calls: <count>
wall_clock_seconds: <elapsed>
tokens_used: <input + output>
# DRS-only fields:
phases_completed: <list>
final_mode: explore | commit | sprint | last-stand | halt
exit_gates_passed: <count>
exit_gates_failed: <count>
```

### Phase 3: Judge each output

For each run's report, evaluate every rubric criterion independently.

#### Judge protocol (DRACO-compatible)

For each criterion in the task's `criteria` list:

1. Read the criterion text and the generated report
2. Determine: is this criterion **MET** or **UNMET**?
3. Write a 1-2 sentence explanation

Use this judge prompt template:

```
You are evaluating a research report against a specific rubric criterion.

CRITERION TYPE: <positive or negative>
CRITERION: <criterion text>

REPORT:
<full report text>

RULES:
- For POSITIVE criteria: verdict is MET if the report satisfies the requirement.
- For NEGATIVE criteria: verdict is MET if the report AVOIDS the described pitfall.
- Be strict. Vague or partial satisfaction is UNMET for positive criteria.
- Explain your reasoning in 1-2 sentences before giving the verdict.

Respond with JSON:
{"explanation": "<reasoning>", "verdict": "MET" or "UNMET"}
```

#### Scoring math

For each run, compute:

- **Normalized score** = max(0, min(1, raw / max_possible)) × 100%
  - Where `raw` = Σ (weight × 1[verdict == MET]) for all criteria
  - Where `max_possible` = Σ max(0, weight) for all criteria
- **Pass rate** = (positive criteria MET + negative criteria UNMET) / total criteria × 100%
- **Per-axis scores**: compute normalized score within each axis (factual_accuracy, breadth_depth, presentation, citation)

### Phase 4: Produce comparison report

Return a structured comparison report:

```markdown
# Evaluation Report

## Configuration
- **Tasks:** <count> tasks, domains: <list>
- **Conditions:** <list>
- **Runs per condition:** <N>
- **Budget:** <wall time>, <max tool calls>, <max tokens>
- **Judge model:** <model name>
- **Agent model:** <model name>
- **Temperature:** <value>

## Summary Results

| Metric | ReAct (mean ± std) | DRS (mean ± std) | Δ |
|--------|--------------------|--------------------|---|
| Normalized Score | X.X ± Y.Y | X.X ± Y.Y | +/- Z.Z |
| Pass Rate | X.X% ± Y.Y% | X.X% ± Y.Y% | +/- Z.Z% |
| Factual Accuracy | X.X ± Y.Y | X.X ± Y.Y | +/- Z.Z |
| Breadth & Depth | X.X ± Y.Y | X.X ± Y.Y | +/- Z.Z |
| Presentation | X.X ± Y.Y | X.X ± Y.Y | +/- Z.Z |
| Citation Quality | X.X ± Y.Y | X.X ± Y.Y | +/- Z.Z |
| Tool Calls | X.X ± Y.Y | X.X ± Y.Y | +/- Z.Z |
| Tokens Used | X.X ± Y.Y | X.X ± Y.Y | +/- Z.Z |
| Wall Clock (s) | X.X ± Y.Y | X.X ± Y.Y | +/- Z.Z |

## Per-Task Results

### <task_id>: <domain>

| Run | Condition | Score | Pass Rate | Tools | Tokens | Time |
|-----|-----------|-------|-----------|-------|--------|------|
| 1 | react | X.X | X.X% | N | N | Ns |
| 1 | drs | X.X | X.X% | N | N | Ns |
| ... | ... | ... | ... | ... | ... | ... |

**Winner:** <condition> by <margin>
**Key differences:** <1-2 sentences>

## Per-Criterion Analysis

List criteria where conditions diverged most:

| Criterion | Axis | Weight | ReAct MET% | DRS MET% | Δ |
|-----------|------|--------|------------|----------|---|
| <text> | <axis> | <wt> | X% | X% | +/-X% |

## Cost-Normalized Performance

| Condition | Score per 1K tokens | Score per tool call | Score per minute |
|-----------|--------------------|--------------------|-----------------|
| react | X.X | X.X | X.X |
| drs | X.X | X.X | X.X |

## Interpretation

<2-4 paragraphs analyzing:>
- Which condition produced higher quality reports?
- Where did each condition's strengths and weaknesses lie?
- Was the DRS overhead justified by quality improvements?
- What does this suggest for the next development phase?

## Raw Data

<Link to or inline the full per-run records for reproducibility>
```

## Task file format

Tasks are defined in YAML. Each task file contains a list:

```yaml
- task_id: pilot-01
  domain: technology
  prompt: >
    Research the current state of KV-cache optimization techniques for
    large language models. Compare at least 3 approaches, discuss their
    trade-offs, and recommend which is most suitable for inference on
    consumer GPUs with 24GB VRAM.
  criteria:
    - text: "Mentions Multi-Query Attention (MQA) or Grouped-Query Attention (GQA)"
      type: positive
      axis: factual_accuracy
      weight: 10
    - text: "Correctly states that GQA uses fewer KV heads than MHA but more than MQA"
      type: positive
      axis: factual_accuracy
      weight: 15
    - text: "Discusses memory savings quantitatively"
      type: positive
      axis: breadth_depth
      weight: 10
    - text: "Recommends a specific approach with stated reasoning"
      type: positive
      axis: breadth_depth
      weight: 10
    - text: "Includes at least one citation to a primary source"
      type: positive
      axis: citation
      weight: 10
    - text: "Claims KV-cache optimization has no drawbacks"
      type: negative
      axis: factual_accuracy
      weight: -20
```

## Rules

- **Identical inputs.** Both conditions receive the exact same task prompt. No hints about the evaluation.
- **Identical budgets.** Same wall time, tool calls, tokens, and tools for every condition.
- **Independent runs.** Each run starts from a clean workspace. No state carries between runs.
- **Independent judging.** The judge evaluates each criterion against the report without knowing which condition produced it.
- **Record everything.** Every run's full report, metrics, and judge verdicts are preserved for audit.
- **Do not cherry-pick.** Report all runs, including failures and timeouts. A timed-out run scores whatever criteria the partial report satisfies.
- **Declare limitations.** If the judge model is the same family as the agent model, note this as a potential bias source.
