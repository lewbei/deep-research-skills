# deep-research-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)
[![CI](https://github.com/lewbei/deep-research-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/lewbei/deep-research-skills/actions/workflows/ci.yml)
[![Workflow](https://img.shields.io/badge/Workflow-Interleaved--Research-orange.svg)](.agents/skills/research-loop/docs/research-workflow.md)

An operationalized, time-aware interleaved deep-research and execution workflow for Devin and Antigravity agents. Designed for time-constrained competitions, hackathons, and research-heavy tasks.

Unlike naive upfront-research loops, this repository implements a continuous **research → execute 1 bounded unit → learn → repeat** cycle driven by a persistent unknowns registry and enforced by a deterministic Python state-machine runtime.

---

## Workflow Architecture

```mermaid
graph TD
    A[Phase 1: Goal & Constraints] --> B[Phase 2: Validate Feasibility]
    B --> C[Phase 3: Broad Sweep]
    C --> D[Phase 3.5: Budget Checkpoint]
    D --> E[Phase 4: Check Unknowns Registry]
    E --> F[Phase 5: Research Blocker subagents]
    F --> G[Phase 6: Update Hypothesis Tree]
    G --> H[Phase 7: Pick Next Step / Mega-Plan]
    H --> I[Phase 8: Run Probes & Execute 1 Unit]
    I --> J[Phase 9: Learn & Validate Proxies]
    J -->|Loop Back| D
    J -->|Stop Condition Met| K[Phase 10: Reflection & Handoff]
```

---

## Key Features

- **Time-Budget Pacing:** Continuously adjusts behavior (explore → commit → sprint → last-stand → halt) as wall-clock time is consumed.
- **Goodhart's Law Guardrails:** Prevents chasing fake proxies by validating process-reward metrics against real outcomes using Spearman rank correlation (requires ≥5 observations).
- **Read-Only Subagents:** Prevents write-conflict state drift by keeping research subagents read-only and returning structured summaries to the orchestrator.
- **Independent Verification:** Integrates a skeptical verification subagent that confirms all extracted claims against primary sources.
- **Preventive & Reactive Escalation:** Clear human-in-the-loop triggers (budget thresholds, plan divergence, flat progress).

---

## Deterministic Control Layer (drs CLI)

The `drs` CLI enforces the workflow graph correctly and reliably:

| Command | Description |
|---|---|
| `drs init --total-minutes N --kind soft\|hard` | Bootstrap all templates and session state |
| `drs status` | Print active phase, remaining time, R/E budget |
| `drs transition <from> <to>` | Enforce graph transitions; block invalid jumps |
| `drs budget` | Update elapsed time and pacing mode |
| `drs proxy <id> --add <val>:<true\|false>` | Track proxy observations; run Spearman correlation |
| `drs validate` | Check all templates, frontmatter, state ledger |

---

## A/B Evaluation Harness

The `benchmarks/` package contains a scientific evaluation harness for comparing three research agent conditions:

| Condition | Description |
|---|---|
| `direct` | Single zero-shot LLM call, no tools |
| `react` | Thought→Action→Observation loop with web search (requires ≥2 searches) |
| `drs` | Full DRS state-machine workflow via `drs` CLI + web search |

### Running benchmarks

```bash
# Run all three conditions on the pilot task set
python3 -m benchmarks.runner \
  --tasks .agents/skills/evaluate/tasks/pilot_tasks.yaml \
  --conditions direct,react,drs \
  --runs 3 \
  --model "Gemini 3.5 Flash (Low)" \
  --run-id my-experiment-01

# Run only direct vs react with a 10-minute budget per agent
python3 -m benchmarks.runner \
  --tasks benchmarks/smoke_task.yaml \
  --conditions direct,react \
  --budget 600
```

Each run saves to `evaluation_runs/<run-id>/`:
- `run_config.json` — git commit, git dirty flag, harness file SHA-256s, task file SHA-256
- `tasks.yaml` — snapshot of the exact task file used
- `raw_runs.json` — per-run telemetry, action trajectory, judge verdicts, scores

### Harness design guarantees

| Property | Implementation |
|---|---|
| **No `eval()`** | All tool-call parsing uses `json.loads()` on fenced ` ```json ``` ` blocks |
| **Phase-10 confirmation** | DRS success requires `drs status` to report Phase 10 AND `final-report.md` to pass structural checks |
| **Three-state judge** | Verdicts are `MET`, `UNMET`, or `JUDGE_ERROR`; errors don't silently become `UNMET` |
| **Equal budgets** | One `--budget` value (default 720 s) is passed identically to all agents |
| **Dirty-tree warning** | `git status --porcelain` checked before every run; `git_dirty=true` recorded in config |
| **Provenance** | SHA-256 of every harness file stored in `run_config.json` |
| **Path sandbox** | All workspace reads/writes validated via `Path.relative_to()` — no string-prefix bypass |

### Running harness regression tests

```bash
python3 benchmarks/test_harness.py
```

All 7 tests must pass before any benchmark data is trustworthy:

```
Test 1 (clean JSON block): PASS
Test 2 (braces in report content): PASS
Test 3 (old Action[] format rejected): PASS
Test 4 (last block wins): PASS
Test 5 (JUDGE_ERROR excluded from score): PASS
Test 6 (path sandbox .relative_to()): PASS
Test 7 (invalid JSON block skipped, valid block parsed): PASS
```

### Writing task files

Task YAML format:

```yaml
- task_id: my-task-01
  domain: technology
  prompt: >
    Compare approach A vs approach B for solving X.
    Search the web for empirical comparisons.
  criteria:
    - text: "Mentions approach A by name"
      type: positive
      axis: factual_accuracy
      weight: 10
    - text: "Discusses a quantitative trade-off"
      type: positive
      axis: breadth_depth
      weight: 15
    - text: "Claims approach A has zero downsides (false)"
      type: negative
      axis: factual_accuracy
      weight: -20
```

`type: negative` criteria use inverted scoring: verdict `MET` means the report **avoided** the pitfall (good); `UNMET` means it fell into it (penalty applied).

---

## Project Structure

```
deep-research-skills/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── pyproject.toml
├── drs                            # CLI executable wrapper
├── benchmarks/                    # A/B evaluation harness
│   ├── action_parser.py           # Safe JSON tool-call parser
│   ├── direct.py                  # Zero-shot baseline agent
│   ├── react.py                   # ReAct agent (requires ≥2 searches)
│   ├── drs.py                     # DRS state-machine agent
│   ├── judge.py                   # Three-state LLM rubric judge
│   ├── runner.py                  # Orchestrator + reporting
│   ├── tasks.py                   # Task/criterion data classes + YAML loader
│   ├── llm.py                     # agy CLI wrapper with timeout
│   ├── search.py                  # Web search wrapper
│   └── test_harness.py            # Regression tests (no API calls)
├── deep_research/                 # DRS runtime package
│   ├── models.py
│   ├── storage.py
│   ├── state_machine.py
│   ├── budget.py
│   ├── proxies.py
│   ├── validation.py
│   └── cli.py
└── .agents/
    └── skills/
        ├── research-loop/         # Main orchestrator skill
        ├── landscape-scan/
        ├── deep-dive/
        └── verify/
```

---

## Installation & Setup

1. Install the package (includes both `deep_research` and `benchmarks`):
   ```bash
   pip install -e .
   ```
2. Run the installer script to place skills in the auto-discovery location:
   ```bash
   python3 install.py
   ```
3. Initialize a deep research session:
   ```bash
   drs init --total-minutes 120 --kind soft
   ```
4. Run phase transitions during execution:
   ```bash
   drs transition 1 2
   ```
