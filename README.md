# deep-research-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)
[![Workflow](https://img.shields.io/badge/Workflow-Interleaved--Research-orange.svg)](.agents/skills/research-loop/docs/research-workflow.md)

An operationalized, time-aware interleaved deep-research and execution workflow for Devin and Antigravity agents. Designed specifically for time-constrained competitions, hackathons, and research-heavy tasks.

Unlike naive upfront-research loops, this repository implements a continuous research -> execute 1 bounded unit of work -> learn -> repeat cycle driven by a persistent unknowns registry and enforced by a deterministic python state-machine runtime.

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

- **Time-Budget Pacing:** Continuously adjusts behavior (explore -> commit -> sprint -> last-stand -> halt) as the wall-clock time is consumed.
- **Goodhart's Law Guardrails:** Prevents chasing fake proxies by validating process-reward metrics against real outcomes using Spearman rank correlation (requires at least 5 observations).
- **Read-Only Subagents:** Prevents write-conflict state drift by keeping research subagents read-only and returning structured summaries to the orchestrator.
- **Independent Verification:** Integrates a skeptical verification subagent that confirms all extracted claims against primary sources to significantly reduce source-claim drift and identify inconsistencies.
- **Preventive & Reactive Escalation:** Outlines clear human-in-the-loop triggers (budget thresholds, plan divergence, flat progress) to ensure the human is notified before resource waste occurs.

---

## Deterministic Control Layer (drs CLI Tool)

To ensure the agent executes the workflow graph correctly and reliably, this repository provides a unified control layer packaged as a Python package (`deep_research`) with a command-line interface (`drs`):

- **drs init:** Pre-instantiates all core markdown templates, generates a unique session UUID, and sets up the session state JSON.
- **drs status:** Tally elapsed pacing metrics and prints active phase, remaining time, and R/E budget consumption.
- **drs transition <from> <to>:** Enforces graph transitions, checking transitions against transitions.yaml or default graph, and blocks research phases in sprint/halt modes.
- **drs budget:** Updates elapsed time and changes active budget pacing mode.
- **drs proxy <id> --add <val>:<true>:** Tracks proxy observations and runs a mathematically correct Spearman rank correlation to detect metric drift.
- **drs validate:** Runs validation checks against all templates, skills frontmatter, and session state ledger integrity.

---

## Project Structure

```
deep-research-skills/
├── README.md                      # Project documentation
├── LICENSE                        # License file
├── CONTRIBUTING.md                # Contributing guidelines
├── install.py                     # Installer script
├── pyproject.toml                 # Package configuration metadata
├── drs                            # CLI executable wrapper
├── deep_research/                 # Unified Python runtime package
│   ├── models.py                  # Dataclasses and strict validation schemas
│   ├── storage.py                 # Atomic storage and file utilities
│   ├── state_machine.py           # Transition checker and graphs
│   ├── budget.py                  # Time budget calculations
│   ├── proxies.py                 # Spearman correlation rank math
│   ├── validation.py              # Frontmatter and templates validators
│   └── cli.py                     # CLI command line endpoints
└── .agents/
    └── skills/                    # Auto-discovered skills directory
        ├── research-loop/
        │   ├── SKILL.md           # Main orchestrator skill
        │   ├── docs/
        │   │   ├── research-workflow.md # Detailed workflow
        │   │   └── mega-plan-guide.md   # Reference guide
        │   └── templates/         # Core workflow templates
        │       ├── unknowns-registry.md
        │       ├── landscape-table.md
        │       ├── hypothesis-tree.md
        │       ├── decision-log.md
        │       ├── archive.md
        │       ├── probe-registry.md
        │       ├── time-budget.md
        │       ├── proxy-log.md
        │       ├── human-escalation-policy.md
        │       ├── session-state.json
        │       └── mega-plan.md
        ├── landscape-scan/
        │   └── SKILL.md           # Sweep subagent skill
        ├── deep-dive/
        │   └── SKILL.md           # Deep-dive subagent skill
        └── verify/
            └── SKILL.md           # Independent verifier skill
```

---

## Installation & Setup

1. Install the CLI package in editable mode:
   ```bash
   pip install -e .
   ```
2. Run the installer script to place the skills in the correct auto-discovery location:
   ```bash
   python3 install.py
   ```
3. Initialize the deep research session:
   ```bash
   drs init --total-minutes 120 --kind soft
   ```
4. Run phase transitions during execution:
   ```bash
   drs transition 1 2
   ```
