# Evaluation Harness Run Report

## Run Metadata
- **Run ID:** `smoke-v3-20260719`
- **Git commit:** `e77cb8b7d74c6b703f5db142db6793002c5e5b17`
- **Tasks:** 1 (technology)
- **Conditions:** direct, react, drs
- **Runs per condition:** 1
- **Agent model:** Gemini 3.5 Flash (Low)
- **Judge model:** Gemini 3.5 Flash (Low) (same-family; results should be interpreted cautiously)

## Execution Validity Summary
Only runs with `exec_status=success` are forwarded to the quality judge.

| Condition | smoke-01 | Total Success |
|---|---|---|
| direct | 1/1 | 1 |
| react | 0/1 | 0 |
| drs | 0/1 | 0 |

## Quality Results (successful runs only)

| Metric | DIRECT | REACT | DRS |
|---|---|---|---|
| Normalized Score | 66.7% ± 0.0%  (n=1) | — | — |
| Pass Rate | 75.0% ± 0.0%  (n=1) | — | — |
| Breadth Depth | 100.0% ± 0.0% | — | — |
| Factual Accuracy | 50.0% ± 0.0% | — | — |
| Search Requests | 0.0 ± 0.0  (n=1) | — | — |
| File Reads | 0.0 ± 0.0  (n=1) | — | — |
| File Writes | 0.0 ± 0.0  (n=1) | — | — |
| CLI Commands | 0.0 ± 0.0  (n=1) | — | — |
| Exec Calls | 0.0 ± 0.0  (n=1) | — | — |
| Model Calls | 1.0 ± 0.0  (n=1) | — | — |
| Est. Tokens | 1761.0 ± 0.0  (n=1) | — | — |
| Wall Clock | 23.8s ± 0.0s  (n=1) | — | — |

## Per-Run Detail

### smoke-01: technology
| Run | Condition | Exec Status | Score | Pass | Searches | Reads | Writes | CLIs | Execs | Models | Tokens | Time |
|-----|-----------|-------------|-------|------|----------|-------|--------|------|-------|--------|--------|------|
| 1 | direct | success | 66.7% | 75.0% | 0 | 0 | 0 | 0 | 0 | 1 | 1761 | 23.8s |
| 1 | react | incomplete_no_search | 0.0% | 0.0% | 1 | 0 | 0 | 0 | 0 | 2 | 2105 | 49.2s |
| 1 | drs | incomplete | 0.0% | 0.0% | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 22.5s |

## Conclusion
This run exercises the three-condition evaluation pipeline and records action-level telemetry per run. Failed and incomplete runs were excluded from quality scoring. The results are diagnostic — they do not yet constitute a statistically valid comparison. Limitations include: same-model judging, single task, single run per condition, and no token-exact accounting.