import argparse
import sys
import os
import json
import time
import numpy as np
from typing import List, Dict, Any
from benchmarks.tasks import load_tasks_from_yaml, BenchmarkTask
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
    report_lines.append("# Evaluation Report")
    report_lines.append(f"\n## Configuration")
    report_lines.append(f"- **Tasks:** {len(tasks)} tasks, domains: {', '.join(set(t.domain for t in tasks))}")
    report_lines.append(f"- **Conditions:** {', '.join(conditions)}")
    report_lines.append(f"- **Runs per condition:** {runs_per_condition}")
    report_lines.append(f"- **Agent model:** {model}")
    report_lines.append(f"- **Judge model:** {model}")
    
    report_lines.append(f"\n## Summary Results")
    report_lines.append("\n| Metric | ReAct (mean ± std) | DRS (mean ± std) | Δ |")
    report_lines.append("|--------|--------------------|--------------------|---|")
    
    # Compute aggregates
    stats = {}
    for cond in conditions:
        scores = [r["normalized_score"] for r in metrics_by_cond[cond]]
        passes = [r["pass_rate"] for r in metrics_by_cond[cond]]
        tools = [r["tool_calls"] for r in metrics_by_cond[cond]]
        times = [r["wall_clock_seconds"] for r in metrics_by_cond[cond]]
        
        # Axis breakdown
        axis_vals = {}
        for r in metrics_by_cond[cond]:
            for axis, val in r["axis_scores"].items():
                if axis not in axis_vals:
                    axis_vals[axis] = []
                axis_vals[axis].append(val)
                
        stats[cond] = {
            "score_mean": np.mean(scores),
            "score_std": np.std(scores),
            "pass_mean": np.mean(passes),
            "pass_std": np.std(passes),
            "tools_mean": np.mean(tools),
            "tools_std": np.std(tools),
            "time_mean": np.mean(times),
            "time_std": np.std(times),
            "axis_stats": {axis: (np.mean(vals), np.std(vals)) for axis, vals in axis_vals.items()}
        }
        
    react = stats.get("react")
    drs = stats.get("drs")
    
    if react and drs:
        # Score diff
        diff_score = drs["score_mean"] - react["score_mean"]
        diff_pass = drs["pass_mean"] - react["pass_mean"]
        diff_tools = drs["tools_mean"] - react["tools_mean"]
        diff_time = drs["time_mean"] - react["time_mean"]
        
        report_lines.append(f"| Normalized Score | {react['score_mean']:.1f} ± {react['score_std']:.1f} | {drs['score_mean']:.1f} ± {drs['score_std']:.1f} | {diff_score:+.1f} |")
        report_lines.append(f"| Pass Rate | {react['pass_mean']:.1f}% ± {react['pass_std']:.1f}% | {drs['pass_mean']:.1f}% ± {drs['pass_std']:.1f}% | {diff_pass:+.1f}% |")
        
        # Axis stats
        all_axes = set(react["axis_stats"].keys()).union(drs["axis_stats"].keys())
        for axis in all_axes:
            r_axis = react["axis_stats"].get(axis, (0.0, 0.0))
            d_axis = drs["axis_stats"].get(axis, (0.0, 0.0))
            diff_axis = d_axis[0] - r_axis[0]
            axis_name = axis.replace("_", " ").title()
            report_lines.append(f"| {axis_name} | {r_axis[0]:.1f} ± {r_axis[1]:.1f} | {d_axis[0]:.1f} ± {d_axis[1]:.1f} | {diff_axis:+.1f} |")
            
        report_lines.append(f"| Tool Calls | {react['tools_mean']:.1f} ± {react['tools_std']:.1f} | {drs['tools_mean']:.1f} ± {drs['tools_std']:.1f} | {diff_tools:+.1f} |")
        report_lines.append(f"| Wall Clock (s) | {react['time_mean']:.1f} ± {react['time_std']:.1f} | {drs['time_mean']:.1f} ± {drs['time_std']:.1f} | {diff_time:+.1f}s |")
        
    report_lines.append(f"\n## Per-Task Results")
    for task in tasks:
        report_lines.append(f"\n### {task.task_id}: {task.domain}")
        report_lines.append("\n| Run | Condition | Score | Pass Rate | Tools | Time | Status |")
        report_lines.append("|-----|-----------|-------|-----------|-------|------|--------|")
        task_runs = [r for r in raw_runs if r["task_id"] == task.task_id]
        for r in task_runs:
            report_lines.append(f"| {r['run_index']} | {r['condition']} | {r['normalized_score']:.1f}% | {r['pass_rate']:.1f}% | {r['tool_calls']} | {r['wall_clock_seconds']:.1f}s | {r['status']} |")
            
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
    parser.add_argument("--conditions", type=str, default="react,drs", help="Comma-separated conditions to compare.")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per condition.")
    parser.add_argument("--model", type=str, default="Gemini 3.5 Flash (Low)", help="LLM model to use.")
    args = parser.parse_args()
    
    conditions_list = [c.strip() for c in args.conditions.split(",")]
    run_benchmarks(args.tasks, conditions_list, args.runs, args.model)
