# Evaluation Harness Run Report

## Configuration
- **Tasks:** 1 tasks, domains: technology
- **Conditions:** direct, react, drs
- **Runs per condition:** 1
- **Agent model:** Gemini 3.5 Flash (Low)
- **Judge model:** Gemini 3.5 Flash (Low)

## Summary Results

| Metric | DIRECT (mean ± std) | REACT (mean ± std) | DRS (mean ± std) |
|---|---|---|---|
| Normalized Score | 100.0% ± 0.0% | 57.1% ± 0.0% | 0.0% ± 0.0% |
| Pass Rate | 100.0% ± 0.0% | 75.0% ± 0.0% | 25.0% ± 0.0% |
| Breadth Depth | 100.0% ± 0.0% | 100.0% ± 0.0% | 0.0% ± 0.0% |
| Factual Accuracy | 100.0% ± 0.0% | 40.0% ± 0.0% | 0.0% ± 0.0% |
| Search Requests | 0.0 ± 0.0 | 1.0 ± 0.0 | 0.0 ± 0.0 |
| File Reads | 0.0 ± 0.0 | 0.0 ± 0.0 | 2.0 ± 0.0 |
| File Writes | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| CLI Commands | 0.0 ± 0.0 | 0.0 ± 0.0 | 9.0 ± 0.0 |
| Exec Calls | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| Model Calls | 1.0 ± 0.0 | 3.0 ± 0.0 | 30.0 ± 0.0 |
| Estimated Tokens | 484.0 ± 0.0 | 9365.0 ± 0.0 | 92366.0 ± 0.0 |
| Wall Clock | 10.7s ± 0.0s | 65.6s ± 0.0s | 486.9s ± 0.0s |

## Per-Task Results

### pilot-01: technology

| Run | Condition | Score | Pass Rate | Searches | Reads | Writes | CLIs | Execs | Model Calls | Est Tokens | Time | Status |
|-----|-----------|-------|-----------|----------|-------|--------|------|-------|-------------|------------|------|--------|
| 1 | direct | 100.0% | 100.0% | 0 | 0 | 0 | 0 | 0 | 1 | 484 | 10.7s | success |
| 1 | react | 57.1% | 75.0% | 1 | 0 | 0 | 0 | 0 | 3 | 9365 | 65.6s | success |
| 1 | drs | 0.0% | 25.0% | 0 | 2 | 0 | 9 | 0 | 30 | 92366 | 486.9s | success |

## Conclusion
This run validates the benchmark suite with complete granular telemetry instrumentation. Standard deviations and tool usage logs across conditions reflect actual agentic work.