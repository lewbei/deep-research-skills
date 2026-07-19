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
| Normalized Score | 100.0% ± 0.0% | 100.0% ± 0.0% | 28.6% ± 0.0% |
| Pass Rate | 100.0% ± 0.0% | 100.0% ± 0.0% | 50.0% ± 0.0% |
| Breadth Depth | 100.0% ± 0.0% | 100.0% ± 0.0% | 0.0% ± 0.0% |
| Factual Accuracy | 100.0% ± 0.0% | 100.0% ± 0.0% | 40.0% ± 0.0% |
| Search Requests | 0.0 ± 0.0 | 0.0 ± 0.0 | 2.0 ± 0.0 |
| File Reads | 0.0 ± 0.0 | 0.0 ± 0.0 | 2.0 ± 0.0 |
| File Writes | 0.0 ± 0.0 | 0.0 ± 0.0 | 2.0 ± 0.0 |
| CLI Commands | 0.0 ± 0.0 | 0.0 ± 0.0 | 19.0 ± 0.0 |
| Exec Calls | 0.0 ± 0.0 | 0.0 ± 0.0 | 1.0 ± 0.0 |
| Model Calls | 1.0 ± 0.0 | 10.0 ± 0.0 | 30.0 ± 0.0 |
| Estimated Tokens | 409.0 ± 0.0 | 64805.0 ± 0.0 | 89368.0 ± 0.0 |
| Wall Clock | 19.3s ± 0.0s | 122.1s ± 0.0s | 829.9s ± 0.0s |

## Per-Task Results

### pilot-01: technology

| Run | Condition | Score | Pass Rate | Searches | Reads | Writes | CLIs | Execs | Model Calls | Est Tokens | Time | Status |
|-----|-----------|-------|-----------|----------|-------|--------|------|-------|-------------|------------|------|--------|
| 1 | direct | 100.0% | 100.0% | 0 | 0 | 0 | 0 | 0 | 1 | 409 | 19.3s | success |
| 1 | react | 100.0% | 100.0% | 0 | 0 | 0 | 0 | 0 | 10 | 64805 | 122.1s | success |
| 1 | drs | 28.6% | 50.0% | 2 | 2 | 2 | 19 | 1 | 30 | 89368 | 829.9s | success |

## Conclusion
This run validates the benchmark suite with complete granular telemetry instrumentation. Standard deviations and tool usage logs across conditions reflect actual agentic work.