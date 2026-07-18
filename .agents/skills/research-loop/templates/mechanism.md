# Mechanism: <approach name>

Detailed how-it-works for one approach. Extracted by the deep-dive subagent and saved by the orchestrator to `approaches/<name>/mechanism.md`.

## Source
- **URL:**
- **Type:** paper / code / writeup / official docs
- **Author / team:**
- **Date:**

## Probe script (if applicable)
- **Unknown ID:** U<id>
- **Probe path:** `probes/<unknown-id>.py`
- **What it tests:**
- **Result:** passed / failed / not run / blocked
- **Stdout / stderr:** (if run)

## Architecture
- What model or algorithm is used?
- What are the components and how do they connect?
- Include a flowchart (Mermaid or ASCII) showing data/control flow.

## Math
- Core equations: loss function, search formula, update rule, policy gradient, etc.
- Write them in LaTeX or plain notation and explain each variable.

## Training
- What data is used? (replays, self-play, demonstrations, etc.)
- What hyperparameters? (learning rate, batch size, epochs, search budget)
- What infrastructure? (GPU, CPU, distributed, single machine)
- How long does training take?

## Inference
- What is the decision process at runtime? (search depth, model forward pass, rule application)
- What is the latency? (ms per decision)
- What information does it use? (full state, partial state, history)

## Key insights
- What is the core trick that makes this approach work?
- What would break if removed?
- What are the limitations or assumptions?

## Implementation notes
- What dependencies are needed?
- What gotchas or edge cases are mentioned?
- What parameters need tuning?
- What is the expected performance with our constraints?
- What exact code or pseudo-code is needed?

## Answer to the specific unknown
- Direct answer to the question that triggered this deep-dive.
- Evidence: exact passage or code snippet from the source.

## Limitations / gaps
- What the source does not cover.
- Any contradictory evidence found.
