# Pilot End-to-End Harness and Workflow-Compliance Test

This document reports the execution results of the initial workflow compliance test comparing a direct-generation baseline and the DRS state-machine orchestrator.

## Configuration
- **Tasks:** 1 task (pilot-01, technology domain)
- **Conditions:** Direct Answer Baseline, DRS
- **Runs per condition:** 1
- **Agent model:** Gemini 3.5 Flash (Low)
- **Judge model:** Gemini 3.5 Flash (Low)

## Summary Results

| Metric | Direct Answer Baseline | DRS | Δ |
|--------|------------------------|-----|---|
| Normalized Score | 100.0% | 100.0% | +0.0% |
| Pass Rate | 100.0% | 100.0% | +0.0% |
| Factual Accuracy | 100.0% | 100.0% | +0.0% |
| Breadth & Depth | 100.0% | 100.0% | +0.0% |
| Harness Tool Invocations | 0 | 2 | +2 |
| Wall Clock (s) | 25.3s | 189.3s | +164.0s |

## Per-Task Results

### pilot-01: technology

| Run | Condition | Score | Pass Rate | Tools | Time | Status |
|-----|-----------|-------|-----------|-------|------|--------|
| 1 | Direct Answer Baseline | 100.0% | 100.0% | 0 | 25.3s | success |
| 1 | DRS | 100.0% | 100.0% | 2 | 189.3s | success |

## Conclusion
Both the direct baseline and DRS satisfied the limited pilot rubric. The run validates automated DRS workspace orchestration and artifact production, but does not demonstrate a quality advantage due to the single easy task, one run per condition, rubric saturation, same-model judging, and incomplete internal tool-call accounting. DRS incurred substantially higher latency in this pilot.