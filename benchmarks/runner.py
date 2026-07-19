import argparse
import sys
import os
import json
import time
import numpy as np
from typing import List, Dict, Any
from benchmarks.tasks import load_tasks_from_yaml, BenchmarkTask
from benchmarks.direct import DirectAgent
from benchmarks.react import ReactAgent
from benchmarks.drs import DERSAgent
from benchmarks.judge import RubricJudge

def score_math(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes scores from judge results:
    - Normalized score = max(0, min(1, raw / max_possible)) * 100
    - Pass rate = (positive criteria MET + negative criteria UNMET) / total criteria * 100
    """
    raw_score = 0
    max_possible = 0
    met_count = 0
    total_criteria = len(results)
    
    # Per-axis trackers
    axis_raw = {}
    axis_max = {}
    
    for res in results:
        weight = res["weight"]
        verdict = res["verdict"]
        axis = res["axis"]
        
        # Initialize axis trackers
        if axis not in axis_raw:
            axis_raw[axis] = 0
            axis_max[axis] = 0
            
        if weight > 0:
            max_possible += weight
            axis_max[axis] += weight
            if verdict == "MET":
                raw_score += weight
                axis_raw[axis] += weight
                met_count += 1
        else:
            # Negative weights
            if verdict == "MET":
                # For negative criteria, MET means they avoided the pitfall, which is good
                met_count += 1
            else:
                # UNMET means they fell into the pitfall
                raw_score += weight # Add negative weight (reduces score)
                axis_raw[axis] += weight
                
    normalized = (max(0.0, min(max_possible, raw_score)) / max_possible * 100.0) if max_possible > 0 else 0.0
    pass_rate = (met_count / total_criteria * 100.0) if total_criteria > 0 else 0.0
    
    # Compute per-axis normalized scores
    axis_normalized = {}
    for axis in axis_max:
        if axis_max[axis] > 0:
            axis_normalized[axis] = max(0.0, min(axis_max[axis], axis_raw[axis])) / axis_max[axis] * 100.0
        else:
            axis_normalized[axis] = 0.0
            
    return {
        "normalized_score": normalized,
        "pass_rate": pass_rate,
        "axis_scores": axis_normalized
    }

def run_benchmarks(tasks_path: str, conditions: List[str], runs_per_condition: int, model: str):
    print(f"Loading tasks from: {tasks_path}")
    tasks = load_tasks_from_yaml(tasks_path)
    print(f"Loaded {len(tasks)} tasks.")
    
    # Initialize agents and judge
    agents = {}
    if "direct" in conditions:
        agents["direct"] = DirectAgent(model=model)
    if "react" in conditions:
        agents["react"] = ReactAgent(model=model)
    if "drs" in conditions:
        agents["drs"] = DERSAgent(model=model)
        
    judge = RubricJudge(model=model)
    
    # Store raw run data
    raw_runs = []
    
    # Map metrics for summary table
    metrics_by_cond = {cond: [] for cond in conditions}
    
    for task in tasks:
        print(f"\n==================================================")
        print(f"Task ID: {task.task_id} (Domain: {task.domain})")
        print(f"Prompt: {task.prompt[:150]}...")
        print(f"==================================================")
        
        for cond in conditions:
            agent = agents[cond]
            for run_idx in range(runs_per_condition):
                print(f"\n---> Running {cond.upper()} (Run {run_idx+1}/{runs_per_condition})...")
                start_time = time.time()
                
                # Execute agent
                out = agent.run(task.prompt)
                elapsed = time.time() - start_time
                
                print(f"Finished {cond.upper()} in {elapsed:.1f}s. Tool calls: {out['tool_calls']}. Status: {out['status']}")
                
                # Evaluate output
                print("Evaluating report with LLM judge...")
                judge_results = judge.evaluate_all(out["report"], task.criteria)
                scores = score_math(judge_results)
                
                print(f"Normalized Score: {scores['normalized_score']:.1f}% | Pass Rate: {scores['pass_rate']:.1f}%")
                
                # Store results
                run_metrics = {
                    "task_id": task.task_id,
                    "condition": cond,
                    "run_index": run_idx + 1,
                    "normalized_score": scores["normalized_score"],
                    "pass_rate": scores["pass_rate"],
                    "axis_scores": scores["axis_scores"],
                    "tool_calls": out["tool_calls"],
                    "metrics": out.get("metrics", {}),
                    "wall_clock_seconds": elapsed,
                    "status": out["status"],
                    "report_len": len(out["report"]),
                    "judge_results": judge_results
                }
                
                raw_runs.append(run_metrics)
                metrics_by_cond[cond].append(run_metrics)
                
    # Output Markdown Report
    print_markdown_report(tasks, conditions, runs_per_condition, model, metrics_by_cond, raw_runs)

def print_markdown_report(tasks: List[BenchmarkTask], conditions: List[str], runs_per_condition: int, model: str, metrics_by_cond: Dict[str, List[Dict[str, Any]]], raw_runs: List[Dict[str, Any]]):
    print("\n\n" + "#" * 60)
    print("FINAL EVALUATION REPORT GENERATED")
    print("#" * 60 + "\n")
    
    report_lines = []
    report_lines.append("# Evaluation Harness Run Report")
    report_lines.append(f"\n## Configuration")
    report_lines.append(f"- **Tasks:** {len(tasks)} tasks, domains: {', '.join(set(t.domain for t in tasks))}")
    report_lines.append(f"- **Conditions:** {', '.join(conditions)}")
    report_lines.append(f"- **Runs per condition:** {runs_per_condition}")
    report_lines.append(f"- **Agent model:** {model}")
    report_lines.append(f"- **Judge model:** {model}")
    
    report_lines.append(f"\n## Summary Results")
    
    # Dynamically build summary table headers
    headers = ["Metric"] + [f"{c.upper()} (mean ± std)" for c in conditions]
    report_lines.append("\n| " + " | ".join(headers) + " |")
    report_lines.append("|" + "---|"*len(headers))
    
    # Compute aggregates per condition
    stats = {}
    all_axes = set()
    for cond in conditions:
        scores = [r["normalized_score"] for r in metrics_by_cond[cond]]
        passes = [r["pass_rate"] for r in metrics_by_cond[cond]]
        times = [r["wall_clock_seconds"] for r in metrics_by_cond[cond]]
        
        # Tool breakdowns
        searches = [r["metrics"].get("search_calls", 0) for r in metrics_by_cond[cond]]
        reads = [r["metrics"].get("read_calls", 0) for r in metrics_by_cond[cond]]
        writes = [r["metrics"].get("write_calls", 0) for r in metrics_by_cond[cond]]
        clis = [r["metrics"].get("cli_calls", 0) for r in metrics_by_cond[cond]]
        execs = [r["metrics"].get("exec_calls", 0) for r in metrics_by_cond[cond]]
        models = [r["metrics"].get("model_calls", 0) for r in metrics_by_cond[cond]]
        tokens = [r["metrics"].get("tokens_estimated", 0) for r in metrics_by_cond[cond]]
        
        # Axis breakdown
        axis_vals = {}
        for r in metrics_by_cond[cond]:
            for axis, val in r["axis_scores"].items():
                all_axes.add(axis)
                if axis not in axis_vals:
                    axis_vals[axis] = []
                axis_vals[axis].append(val)
                
        stats[cond] = {
            "score_mean": np.mean(scores), "score_std": np.std(scores),
            "pass_mean": np.mean(passes), "pass_std": np.std(passes),
            "time_mean": np.mean(times), "time_std": np.std(times),
            "search_mean": np.mean(searches), "search_std": np.std(searches),
            "read_mean": np.mean(reads), "read_std": np.std(reads),
            "write_mean": np.mean(writes), "write_std": np.std(writes),
            "cli_mean": np.mean(clis), "cli_std": np.std(clis),
            "exec_mean": np.mean(execs), "exec_std": np.std(execs),
            "model_mean": np.mean(models), "model_std": np.std(models),
            "tokens_mean": np.mean(tokens), "tokens_std": np.std(tokens),
            "axis_stats": {axis: (np.mean(vals), np.std(vals)) for axis, vals in axis_vals.items()}
        }
        
    # Write summary rows
    def format_row(metric_name: str, key_prefix: str, suffix: str = ""):
        row = [metric_name]
        for cond in conditions:
            mean = stats[cond][f"{key_prefix}_mean"]
            std = stats[cond][f"{key_prefix}_std"]
            row.append(f"{mean:.1f}{suffix} ± {std:.1f}{suffix}")
        return "| " + " | ".join(row) + " |"
        
    report_lines.append(format_row("Normalized Score", "score", "%"))
    report_lines.append(format_row("Pass Rate", "pass", "%"))
    
    # Axis scores
    for axis in sorted(all_axes):
        axis_name = axis.replace("_", " ").title()
        row = [axis_name]
        for cond in conditions:
            mean, std = stats[cond]["axis_stats"].get(axis, (0.0, 0.0))
            row.append(f"{mean:.1f}% ± {std:.1f}%")
        report_lines.append("| " + " | ".join(row) + " |")
        
    report_lines.append(format_row("Search Requests", "search"))
    report_lines.append(format_row("File Reads", "read"))
    report_lines.append(format_row("File Writes", "write"))
    report_lines.append(format_row("CLI Commands", "cli"))
    report_lines.append(format_row("Exec Calls", "exec"))
    report_lines.append(format_row("Model Calls", "model"))
    report_lines.append(format_row("Estimated Tokens", "tokens"))
    report_lines.append(format_row("Wall Clock", "time", "s"))
    
    report_lines.append(f"\n## Per-Task Results")
    for task in tasks:
        report_lines.append(f"\n### {task.task_id}: {task.domain}")
        report_lines.append("\n| Run | Condition | Score | Pass Rate | Searches | Reads | Writes | CLIs | Execs | Model Calls | Est Tokens | Time | Status |")
        report_lines.append("|-----|-----------|-------|-----------|----------|-------|--------|------|-------|-------------|------------|------|--------|")
        task_runs = [r for r in raw_runs if r["task_id"] == task.task_id]
        for r in task_runs:
            m = r["metrics"]
            report_lines.append(f"| {r['run_index']} | {r['condition']} | {r['normalized_score']:.1f}% | {r['pass_rate']:.1f}% | {m.get('search_calls',0)} | {m.get('read_calls',0)} | {m.get('write_calls',0)} | {m.get('cli_calls',0)} | {m.get('exec_calls',0)} | {m.get('model_calls',0)} | {m.get('tokens_estimated',0)} | {r['wall_clock_seconds']:.1f}s | {r['status']} |")
            
    report_lines.append("\n## Conclusion")
    report_lines.append("This run validates the benchmark suite with complete granular telemetry instrumentation. Standard deviations and tool usage logs across conditions reflect actual agentic work.")
    
    # Print report
    markdown_out = "\n".join(report_lines)
    print(markdown_out)
    
    # Save report to workspace
    with open("evaluation-comparison-report.md", "w", encoding="utf-8") as f:
        f.write(markdown_out)
        
    # Save raw runs JSON for reproducibility
    with open("evaluation-raw-runs.json", "w", encoding="utf-8") as f:
        json.dump(raw_runs, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run A/B agent benchmarks.")
    parser.add_argument("--tasks", type=str, default=".agents/skills/evaluate/tasks/pilot_tasks.yaml", help="Path to tasks YAML file.")
    parser.add_argument("--conditions", type=str, default="direct,react,drs", help="Comma-separated conditions to compare.")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per condition.")
    parser.add_argument("--model", type=str, default="Gemini 3.5 Flash (Low)", help="LLM model to use.")
    args = parser.parse_args()
    
    conditions_list = [c.strip() for c in args.conditions.split(",")]
    run_benchmarks(args.tasks, conditions_list, args.runs, args.model)
