# deep-research-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)
[![Workflow](https://img.shields.io/badge/Workflow-Interleaved--Research-orange.svg)](.agents/skills/research-loop/docs/research-workflow.md)

An operationalized, time-aware **interleaved deep-research and execution workflow** for Devin and Antigravity agents. Designed specifically for time-constrained competitions, hackathons, and research-heavy tasks.

Unlike naive upfront-research loops, this repository implements a continuous **research → execute 1 bounded unit of work → learn → repeat** cycle driven by a persistent unknowns registry.

---

## 🚀 Workflow Architecture

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

## ✨ Key Features

- **Time-Budget Pacing:** Continuously adjusts behavior (`explore` → `commit` → `sprint` → `last-stand` → `halt`) as the wall-clock time is consumed.
- **Goodhart's Law Guardrails:** Prevents chasing fake proxies by validating process-reward metrics against real outcomes using Spearman rank correlation (requires at least 5 observations).
- **Read-Only Subagents:** Prevents write-conflict state drift by keeping research subagents read-only and returning structured summaries to the orchestrator.
- **Independent Verification:** Integrates a skeptical verification subagent that confirms all extracted claims against primary sources to significantly reduce source-claim drift and identify inconsistencies.
- **Preventive & Reactive Escalation:** Outlines clear human-in-the-loop triggers (budget thresholds, plan divergence, flat progress) to ensure the human is notified before resource waste occurs.

---

## ⚙️ Deterministic Control Layer

To ensure the agent executes the workflow graph correctly and reliably, this repository provides a **deterministic control layer** in the `scripts/` directory:

- **`scripts/initialize_session.py`:** Pre-instantiates all core markdown templates and sets up the session state JSON.
- **`scripts/calculate_budget.py`:** Automatically tracks elapsed wall-clock time, checks budget pacing thresholds, and updates the session mode.
- **`scripts/calculate_proxy.py`:** Records proxy metrics versus true outcomes and calculates Spearman rank correlation (with tie-handling) over at least 5 observations.
- **`scripts/advance_phase.py`:** Validates phase transitions against the allowed graph schema to prevent transition bypasses.
- **`scripts/validate_state.py`:** Automates validation of `SKILL.md` frontmatter formatting and template schemas.

---

## 📦 Project Structure

```
deep-research-skills/
├── README.md                      # Project documentation
├── LICENSE                        # License file
├── CONTRIBUTING.md                # Contributing guidelines
├── install.py                     # Installer script
├── scripts/                       # Deterministic runtime control scripts
│   ├── initialize_session.py
│   ├── calculate_budget.py
│   ├── calculate_proxy.py
│   ├── advance_phase.py
│   └── validate_state.py
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

## 🛠️ Available Skills

### `@skills:research-loop` (Orchestrator)
The central loop coordinator. Manages time budgeting, updates persistent registries, delegates research, and implements the step-by-step execution path.

### `@skills:landscape-scan` (Subagent)
Performs scoped, bounded sweeps of rules, leaderboard results, public code, and write-ups/papers. Emits a verification-ready `claim_set`.

### `@skills:deep-dive` (Subagent)
Conducts a bounded depth-dive into a specific paper, codebase, or technique to extract concrete mathematical/architectural definitions.

### `@skills:verify` (Subagent)
A skeptical verifier that re-reads primary sources to confirm that claims are aligned, partially supported, or contradicted.

---

## 💻 Installation

Devin and Antigravity discover custom project skills inside `.agents/skills/`.

1. Clone this repository into your workspace.
2. Run the installer script to place the skills in the correct auto-discovery location:
   ```bash
   python3 install.py
   ```
3. Initialize the deep research session:
   ```bash
   python3 scripts/initialize_session.py --total-minutes 120
   ```
