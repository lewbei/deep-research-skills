# v1.0 Handoff and Architectural Roadmap Report

This document details the architectural audit of the current `deep-research-skills` package and outlines the implementation specifications for the next phase (**v1.0**).

---

## 1. Execution Verification & Package Integrity Audit

The automated python integration test suite has been verified on the repository codebase:
* **Command:** `python -m unittest discover -s tests -p "test_*.py"`
* **Status:** **PASSED CLEANLY (OK)**
* **Metrics:** 9 integration and regression tests run and completed in 5.562s with 0 failures or errors.

### Package Structure Verification:
* **Core Runtime ([deep_research/](file:///home/lewbei/deep_learning/research%20planning/deep-research-skills/deep_research)):** Implements the state machine engine, CLI routing, budget calculations, and format validations.
* **Orchestrator Skills ([.agents/skills/](file:///home/lewbei/deep_learning/research%20planning/deep-research-skills/.agents/skills)):** Declares agent workflows for the `research-loop` and specialized read-only subagents (`landscape-scan`, `deep-dive`, `verify`).
* **Fixed Code Completeness Gap:** Created [__init__.py](file:///home/lewbei/deep_learning/research%20planning/deep-research-skills/deep_research/__init__.py) in the `deep_research/` directory to ensure implicit import namespaces are robust across standard Python toolchains and type checkers.

---

## 2. SQLite Event-Sourced Storage Architecture

To transition from a mutable JSON document to a crash-resilient, parallel-safe storage layer, we propose a **SQLite Event-Sourcing (ES)** architecture.

### 2.1 Design Specification
1. **State as a Stream of Events**: All state changes are stored as an append-only log of immutable domain events. The current state is reconstructed by replaying the event stream in chronological order.
2. **Database Tables**:
   - `events` table: Logs atomic changes.
   - `snapshots` table: Stores periodic state snapshots to prevent replaying long streams.

```mermaid
erDiagram
    EVENTS {
        int id PK
        text event_id UNIQUE
        text session_id FK
        int sequence_number
        int schema_version
        text event_type
        text payload
        text idempotency_key
        text actor
        text correlation_id
        text causation_id
        text metadata
        text created_at
    }
    SNAPSHOTS {
        text session_id PK
        int sequence_number
        text state_json
        text checksum
        text updated_at
    }
    EVENTS ||--o| SNAPSHOTS : "rebuilds"
```

### 2.2 Database Schema (SQLite)
```sql
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    schema_version INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL, -- JSON formatted data
    idempotency_key TEXT,
    actor TEXT,
    correlation_id TEXT,
    causation_id TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(session_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS idx_events_session_seq ON events(session_id, sequence_number);

CREATE TABLE IF NOT EXISTS snapshots (
    session_id TEXT PRIMARY KEY,
    sequence_number INTEGER NOT NULL,
    state_json TEXT NOT NULL,
    checksum TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 2.3 Concurrency & Serialized Retries (WAL Mode)
WAL (Write-Ahead Logging) mode improves reader–writer concurrency, while writes remain serialized and require bounded retry handling. 

To prevent concurrent write conflicts, the repository database layer will enforce:
1. **`PRAGMA busy_timeout = 5000;`** to set a 5-second busy handler.
2. **Bounded Exponential Retry** for handling `SQLITE_BUSY` write locks when concurrent writers collide.
3. **Strict Optimistic Locking**: The append API will accept an `expected_sequence_number`. If the current sequence number in the database differs from `expected_sequence_number`, the write is rejected to prevent race conditions.
4. **Idempotency Keys**: Checking `idempotency_key` on events to prevent duplicate event delivery.
5. **Replay & Schema Protections**: Deterministic replay tests, snapshot SHA-256 checksum verification, and migrations for managing schema versions.

---

## 3. Comparative Benchmarking Framework

To scientifically evaluate the dual planning/evidence-graph structure and verification-centric design, we specify a benchmarking framework to run against standard **ReAct (Reasoning + Action)** loops.

### 3.1 Evaluation Methodology & Ablation Ladder
We will evaluate models using standard deep research benchmarks:
1. **DRACO (cs.AI/2602.11685)**: Evaluating cross-domain accuracy, completeness, and objectivity.
2. **DeepSearchQA (cs.CL/2601.20975)**: Kaggle-hosted benchmark covering multi-step, high-intensity retrieval.
3. **ReportBench (cs.CL/2508.15804)**: Evaluating survey writing.
4. **LiveDRBench (cs.AI/2508.04183)**: Comprehensive long-horizon research benchmark.

Rather than comparing only ReAct vs. the full Deep Research System (DRS), evaluations will run on a structured **Ablation Ladder**:
*   **A.** Standard ReAct loop
*   **B.** Prompt-only research loop
*   **C.** DRS state machine without verification exit gates
*   **D.** DRS with verification exit gates
*   **E.** DRS with verification + proxy/probe gates
*   **F.** DRS v1 with SQLite event sourcing + parallel research workers

#### Controlled Evaluation Parameters
To ensure valid comparative benchmarks, every condition will hold constant:
* Same model version and temperature settings.
* Identical search API credentials and local tools access.
* Same maximum tool calls limit.
* Identical token budget and wall-clock budget envelopes.
* Identical benchmark task ordering and input instructions.
* At least 5 repeated runs per task to compute paired bootstrap confidence intervals.
* Cost-normalized performance evaluations.
* Human audits on a random sample of LLM-judge outputs to compute inter-rater agreement (Cohen's Kappa).

### 3.2 Operational Metrics (Inspired by LiveDRBench `2508.04183`)
For a generated research report containing atomic claims $A = \{a_1, a_2, ..., a_n\}$ and ground-truth subclaims $G = \{g_1, g_2, ..., g_m\}$, an LLM judge evaluates factuality and coverage:

- **Fact Precision ($P$)**: Operational definition for the proportion of generated claims verified as correct:
  $$P = \frac{\sum_{a \in A} \mathbb{I}(\text{LLM\_Verify}(a) == \text{True})}{|A|}$$
- **Subclaim Recall ($R$)**: Operational definition for the proportion of ground-truth subclaims covered by the report:
  $$R = \frac{\sum_{g \in G} \mathbb{I}(\text{LLM\_Covered}(g) == \text{True})}{|G|}$$
- **F1 Score**: Harmonic mean of $P$ and $R$.
- **Triangulation Ratio**: The percentage of critical claims backed by $\ge 2$ independent web channels (or 1 channel + 1 empirical code probe).
- **Execution Efficiency**: Average API token cost, execution time, and tool call count.

---

## 4. Parallel Agent Async Orchestrator

Transitioning from synchronous subagent calls to parallel execution scales up search efficiency. The challenge lies in executing concurrent search queries while enforcing rate limits and avoiding write collisions.

### 4.1 Single-Writer Async Architecture
To preserve the single-writer guarantee and prevent concurrent write lock clashes, the orchestrator implements a **Single-Writer Consolidation** pipeline:

```text
Workers (landscape-scan / deep-dive)
    ↓ [Emit Immutable Result Envelopes]
Async Orchestrator Queue
    ↓ [Sequential Process Queue]
Single Event-Writer Task
    ↓ [Sequential SQLite Event Writes]
SQLite Event Store (WAL Mode)
    ↓ [Event-Driven Projection Updates]
Markdown Projections (landscape-table.md, unknowns-registry.md, etc.)
```

1.  **Workers remain 100% read-only**: Subagents are completely barred from writing to SQLite or markdown files directly. They return immutable result envelopes to the orchestrator.
2.  **Async Orchestrator Queue**: The orchestrator queues subagent outputs.
3.  **Single Event-Writer Task**: A dedicated orchestrator worker processes the queue sequentially, appending events to the SQLite event store and updating markdown projections as a **single writer**.

---

## 5. Bibliography & Grounding Literature

1. **A Comprehensive Survey of Deep Research** ([2506.12594](file:///home/lewbei/deep_learning/research%20planning/papers/markdown/2506.12594.md)) — Establishes taxonomy and four fundamental technical dimensions of deep research.
2. **Characterizing Deep Research: A Benchmark and Formal Definition** ([2508.04183](file:///home/lewbei/deep_learning/research%20planning/papers/markdown/2508.04183.md)) — Formalizes LiveDRBench and evaluation protocols for long-form research.
3. **ReportBench: Evaluating Deep Research Agents via Academic Survey Tasks** ([2508.15804](file:///home/lewbei/deep_learning/research%20planning/papers/markdown/2508.15804.md)) — Evaluates structural coherence and fact-density metrics.
4. **DeepSearchQA: Bridging the Comprehensiveness Gap** ([2601.20975](file:///home/lewbei/deep_learning/research%20planning/papers/markdown/2601.20975.md)) — Kaggle-hosted dataset focusing on search intensity and target search recall.
5. **DRACO: A Cross-Domain Benchmark for Deep Research Accuracy, Completeness, and Objectivity** ([2602.11685](file:///home/lewbei/deep_learning/research%20planning/papers/markdown/2602.11685.md)) — Standardizes testing scenarios and evaluation rubrics.
6. **Marco DeepResearch: Unlocking Efficient Deep Research Agents via Verification-Centric Design** ([2603.28376](file:///home/lewbei/deep_learning/research%20planning/papers/markdown/2603.28376.md)) — Details verification-driven trajectories and test-time verification.
7. **Hypothesis-Driven Deep Research (hdri) with LLMs** ([2605.10224](file:///home/lewbei/deep_learning/research%20planning/papers/markdown/2605.10224.md)) — Grounding for hypothesis-driven organization, subject locking, gap-driven iteration and persistent structured storage.
8. **Quest: Training Frontier Deep Research Agents with Fully Synthetic Tasks** ([2605.24218](file:///home/lewbei/deep_learning/research%20planning/papers/markdown/2605.24218.md)) — Synthesizes long-horizon planning, self-correction patterns, and built-in context management for long-horizon research.
