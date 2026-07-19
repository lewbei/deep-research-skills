import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import time
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from benchmarks.tasks import load_tasks_from_yaml, BenchmarkTask
from benchmarks.direct import DirectAgent
from benchmarks.react import ReactAgent
from benchmarks.drs import DERSAgent
from benchmarks.judge import RubricJudge

_REPO_DIR = Path(__file__).resolve().parents[1]

# Statuses that represent genuine execution success — only these are forwarded to the judge.
_VALID_STATUSES = {"success"}


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(_REPO_DIR),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _git_dirty() -> bool:
    """True if working tree has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(_REPO_DIR),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


_HARNESS_FILES = [
    "benchmarks/runner.py",
    "benchmarks/react.py",
    "benchmarks/drs.py",
    "benchmarks/judge.py",
    "benchmarks/action_parser.py",
    "benchmarks/direct.py",
]


def _harness_sha256s() -> Dict[str, str]:
    return {
        f: _sha256(str(_REPO_DIR / f))
        for f in _HARNESS_FILES
    }


def _sha256(path: str) -> str:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "unknown"


def score_math(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes scores from judge verdicts.

    Positive criteria: add weight on MET.
    Negative criteria: subtract |weight| on UNMET (fell into pitfall).
    JUDGE_ERROR criteria: excluded from scoring (not counted in pass rate or max_possible).
    Pass rate: fraction of scoreable criteria correctly handled.
    """
    raw_score = 0.0
    max_possible = 0.0
    met_count = 0
    judge_error_count = 0
    scoreable = 0

    axis_raw: Dict[str, float] = {}
    axis_max: Dict[str, float] = {}

    for res in results:
        weight = res["weight"]
        verdict = res["verdict"]
        axis = res["axis"]
        axis_raw.setdefault(axis, 0.0)
        axis_max.setdefault(axis, 0.0)

        # Skip JUDGE_ERROR — do not count toward score or pass rate
        if verdict == "JUDGE_ERROR":
            judge_error_count += 1
            continue

        scoreable += 1

        if weight > 0:
            max_possible += weight
            axis_max[axis] += weight
            if verdict == "MET":
                raw_score += weight
                axis_raw[axis] += weight
                met_count += 1
        else:
            # Negative criterion
            if verdict == "MET":
                # Avoided the pitfall — good
                met_count += 1
            else:
                raw_score += weight  # reduces score
                axis_raw[axis] += weight

    normalized = (
        max(0.0, min(max_possible, raw_score)) / max_possible * 100.0
        if max_possible > 0 else 0.0
    )
    pass_rate = met_count / scoreable * 100.0 if scoreable > 0 else 0.0

    axis_scores = {
        axis: (
            max(0.0, min(axis_max[axis], axis_raw[axis])) / axis_max[axis] * 100.0
            if axis_max[axis] > 0 else 0.0
        )
        for axis in axis_max
    }

    return {
        "normalized_score": normalized,
        "pass_rate": pass_rate,
        "axis_scores": axis_scores,
        "judge_error_count": judge_error_count,
        "scoreable_criteria": scoreable,
    }


def run_benchmarks(
    tasks_path: str,
    conditions: List[str],
    runs_per_condition: int,
    model: str,
    run_id: Optional[str] = None,
):
    tasks_path = str(Path(tasks_path).resolve())
    print(f"Loading tasks from: {tasks_path}")
    tasks = load_tasks_from_yaml(tasks_path)
    print(f"Loaded {len(tasks)} tasks.")

    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    git_commit = _git_commit()
    git_dirty  = _git_dirty()
    task_file_sha = _sha256(tasks_path)
    harness_shas  = _harness_sha256s()

    if git_dirty:
        print("WARNING: working tree has uncommitted changes — provenance is approximate.")

    print(f"Run ID   : {run_id}")
    print(f"Git HEAD : {git_commit}  (dirty={git_dirty})")
    print(f"Tasks SHA: {task_file_sha}")

    # Equal wall-clock budget for every condition (12 min)
    WALL_CLOCK_BUDGET = 720.0

    agents: Dict[str, Any] = {}
    if "direct" in conditions:
        agents["direct"] = DirectAgent(model=model)
    if "react" in conditions:
        agents["react"] = ReactAgent(model=model)
    if "drs" in conditions:
        agents["drs"] = DERSAgent(model=model)

    judge = RubricJudge(model=model)

    raw_runs: List[Dict] = []
    metrics_by_cond: Dict[str, List[Dict]] = {c: [] for c in conditions}

    # Save run config + task snapshot to evaluation_runs/<run_id>/
    run_dir = _REPO_DIR / "evaluation_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    import shutil
    shutil.copy(tasks_path, str(run_dir / "tasks.yaml"))
    run_config = {
        "run_id": run_id,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "harness_files_sha256": harness_shas,
        "task_file": tasks_path,
        "task_file_sha256": task_file_sha,
        "conditions": conditions,
        "runs_per_condition": runs_per_condition,
        "wall_clock_budget_seconds": WALL_CLOCK_BUDGET,
        "model": model,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")

    for task in tasks:
        print(f"\n{'='*54}")
        print(f"Task: {task.task_id}  Domain: {task.domain}")
        print(f"Prompt: {task.prompt[:120]}...")
        print("=" * 54)

        for cond in conditions:
            agent = agents[cond]
            for run_idx in range(runs_per_condition):
                print(f"\n---> {cond.upper()} run {run_idx+1}/{runs_per_condition}")
                start = time.time()
                out = agent.run(task.prompt, wall_clock_budget=WALL_CLOCK_BUDGET)
                elapsed = time.time() - start

                exec_status = out["status"]
                print(f"     status={exec_status}  time={elapsed:.1f}s  tool_calls={out['tool_calls']}")

                # ── Level 1: Execution validity ──────────────────────────
                if exec_status not in _VALID_STATUSES:
                    scores = {"normalized_score": 0.0, "pass_rate": 0.0, "axis_scores": {},
                              "judge_error_count": 0, "scoreable_criteria": 0}
                    judge_results: List[Dict] = []
                    print(f"     [SKIP JUDGE] status={exec_status} — output not forwarded to judge.")
                else:
                    # ── Level 2: Report quality ───────────────────────────
                    print("     Evaluating report with LLM judge...")
                    judge_results = judge.evaluate_all(out["report"], task.criteria)
                    scores = score_math(judge_results)
                    je = scores['judge_error_count']
                    warn = f"  ⚠ {je} JUDGE_ERROR(s)" if je else ""
                    print(f"     Score={scores['normalized_score']:.1f}%  PassRate={scores['pass_rate']:.1f}%{warn}")

                run_record = {
                    # Reproducibility fields
                    "run_id": run_id,
                    "git_commit": git_commit,
                    "task_file": tasks_path,
                    "task_file_sha256": task_file_sha,
                    "task_snapshot": {
                        "task_id": task.task_id,
                        "domain": task.domain,
                        "prompt": task.prompt,
                    },
                    "criteria_snapshot": [dataclasses.asdict(c) for c in task.criteria],
                    "runner_config": run_config,
                    # Execution fields
                    "task_id": task.task_id,
                    "condition": cond,
                    "run_index": run_idx + 1,
                    "exec_status": exec_status,
                    "incomplete_reason": out.get("incomplete_reason", ""),
                    "normalized_score": scores["normalized_score"],
                    "pass_rate": scores["pass_rate"],
                    "axis_scores": scores["axis_scores"],
                    "tool_calls": out["tool_calls"],
                    "metrics": out.get("metrics", {}),
                    "action_trajectory": out.get("action_trajectory", []),
                    "wall_clock_seconds": elapsed,
                    "report_len": len(out.get("report", "")),
                    "judge_results": judge_results,
                }

                raw_runs.append(run_record)
                metrics_by_cond[cond].append(run_record)

    print_markdown_report(tasks, conditions, runs_per_condition, model, metrics_by_cond, raw_runs, run_id, git_commit)

    # Save raw JSON into run dir
    (run_dir / "raw_runs.json").write_text(json.dumps(raw_runs, indent=2), encoding="utf-8")
    print(f"\nRun artifacts saved to: {run_dir}")


def print_markdown_report(
    tasks: List[BenchmarkTask],
    conditions: List[str],
    runs_per_condition: int,
    model: str,
    metrics_by_cond: Dict[str, List[Dict]],
    raw_runs: List[Dict],
    run_id: str,
    git_commit: str,
):
    print("\n\n" + "#" * 60)
    print("FINAL EVALUATION REPORT GENERATED")
    print("#" * 60 + "\n")

    lines = []
    lines.append("# Evaluation Harness Run Report")
    lines.append(f"\n## Run Metadata")
    lines.append(f"- **Run ID:** `{run_id}`")
    lines.append(f"- **Git commit:** `{git_commit}`")
    lines.append(f"- **Tasks:** {len(tasks)} ({', '.join(set(t.domain for t in tasks))})")
    lines.append(f"- **Conditions:** {', '.join(conditions)}")
    lines.append(f"- **Runs per condition:** {runs_per_condition}")
    lines.append(f"- **Agent model:** {model}")
    lines.append(f"- **Judge model:** {model} (same-family; results should be interpreted cautiously)")

    lines.append(f"\n## Execution Validity Summary")
    lines.append("Only runs with `exec_status=success` are forwarded to the quality judge.")
    lines.append("")

    # Validity table
    valid_hdr = ["Condition"] + [t.task_id for t in tasks] + ["Total Success"]
    lines.append("| " + " | ".join(valid_hdr) + " |")
    lines.append("|" + "---|" * len(valid_hdr))
    for cond in conditions:
        row = [cond]
        total_ok = 0
        for task in tasks:
            task_runs = [r for r in metrics_by_cond[cond] if r["task_id"] == task.task_id]
            ok = sum(1 for r in task_runs if r["exec_status"] == "success")
            total_ok += ok
            row.append(f"{ok}/{runs_per_condition}")
        row.append(str(total_ok))
        lines.append("| " + " | ".join(row) + " |")

    lines.append(f"\n## Quality Results (successful runs only)")
    headers = ["Metric"] + [f"{c.upper()}" for c in conditions]
    lines.append("\n| " + " | ".join(headers) + " |")
    lines.append("|" + "---|" * len(headers))

    stats: Dict[str, Dict] = {}
    all_axes: set = set()

    for cond in conditions:
        valid_runs = [r for r in metrics_by_cond[cond] if r["exec_status"] == "success"]
        if not valid_runs:
            stats[cond] = None
            continue

        def _mean_std(vals):
            if not vals:
                return 0.0, 0.0
            return float(np.mean(vals)), float(np.std(vals))

        scores = [r["normalized_score"] for r in valid_runs]
        passes = [r["pass_rate"] for r in valid_runs]
        times  = [r["wall_clock_seconds"] for r in valid_runs]
        searches = [r["metrics"].get("search_calls", 0) for r in valid_runs]
        reads    = [r["metrics"].get("read_calls",   0) for r in valid_runs]
        writes   = [r["metrics"].get("write_calls",  0) for r in valid_runs]
        clis     = [r["metrics"].get("cli_calls",    0) for r in valid_runs]
        execs    = [r["metrics"].get("exec_calls",   0) for r in valid_runs]
        models   = [r["metrics"].get("model_calls",  0) for r in valid_runs]
        tokens   = [r["metrics"].get("tokens_estimated", 0) for r in valid_runs]

        axis_vals: Dict[str, List[float]] = {}
        for r in valid_runs:
            for axis, val in r["axis_scores"].items():
                all_axes.add(axis)
                axis_vals.setdefault(axis, []).append(val)

        stats[cond] = {
            "n":           len(valid_runs),
            "score":       _mean_std(scores),
            "pass":        _mean_std(passes),
            "time":        _mean_std(times),
            "search":      _mean_std(searches),
            "read":        _mean_std(reads),
            "write":       _mean_std(writes),
            "cli":         _mean_std(clis),
            "exec":        _mean_std(execs),
            "model":       _mean_std(models),
            "tokens":      _mean_std(tokens),
            "axis_stats":  {a: _mean_std(v) for a, v in axis_vals.items()},
        }

    def _fmt(cond, key, suffix=""):
        s = stats.get(cond)
        if s is None:
            return "—"
        m, sd = s[key]
        return f"{m:.1f}{suffix} ± {sd:.1f}{suffix}  (n={s['n']})"

    def _row(label, key, suffix=""):
        cols = [label] + [_fmt(c, key, suffix) for c in conditions]
        return "| " + " | ".join(cols) + " |"

    lines.append(_row("Normalized Score", "score", "%"))
    lines.append(_row("Pass Rate",        "pass",  "%"))
    for axis in sorted(all_axes):
        row = [axis.replace("_", " ").title()]
        for cond in conditions:
            s = stats.get(cond)
            if s is None:
                row.append("—")
            else:
                m, sd = s["axis_stats"].get(axis, (0.0, 0.0))
                row.append(f"{m:.1f}% ± {sd:.1f}%")
        lines.append("| " + " | ".join(row) + " |")
    lines.append(_row("Search Requests",  "search"))
    lines.append(_row("File Reads",       "read"))
    lines.append(_row("File Writes",      "write"))
    lines.append(_row("CLI Commands",     "cli"))
    lines.append(_row("Exec Calls",       "exec"))
    lines.append(_row("Model Calls",      "model"))
    lines.append(_row("Est. Tokens",      "tokens"))
    lines.append(_row("Wall Clock",       "time",  "s"))

    lines.append(f"\n## Per-Run Detail")
    col_hdrs = "| Run | Condition | Exec Status | Score | Pass | Searches | Reads | Writes | CLIs | Execs | Models | Tokens | Time |"
    col_sep  = "|-----|-----------|-------------|-------|------|----------|-------|--------|------|-------|--------|--------|------|"
    for task in tasks:
        lines.append(f"\n### {task.task_id}: {task.domain}")
        lines.append(col_hdrs)
        lines.append(col_sep)
        for r in [x for x in raw_runs if x["task_id"] == task.task_id]:
            m = r["metrics"]
            lines.append(
                f"| {r['run_index']} | {r['condition']} | {r['exec_status']} "
                f"| {r['normalized_score']:.1f}% | {r['pass_rate']:.1f}% "
                f"| {m.get('search_calls',0)} | {m.get('read_calls',0)} "
                f"| {m.get('write_calls',0)} | {m.get('cli_calls',0)} "
                f"| {m.get('exec_calls',0)} | {m.get('model_calls',0)} "
                f"| {m.get('tokens_estimated',0)} | {r['wall_clock_seconds']:.1f}s |"
            )

    lines.append("\n## Conclusion")
    lines.append(
        "This run exercises the three-condition evaluation pipeline and records "
        "action-level telemetry per run. Failed and incomplete runs were excluded from "
        "quality scoring. The results are diagnostic — they do not yet constitute a "
        "statistically valid comparison. Limitations include: same-model judging, "
        "single task, single run per condition, and no token-exact accounting."
    )

    md = "\n".join(lines)
    print(md)

    report_path = _REPO_DIR / "evaluation-comparison-report.md"
    report_path.write_text(md, encoding="utf-8")

    raw_path = _REPO_DIR / "evaluation-raw-runs.json"
    raw_path.write_text(json.dumps(raw_runs, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run A/B agent benchmarks.")
    parser.add_argument("--tasks",   default=".agents/skills/evaluate/tasks/pilot_tasks.yaml")
    parser.add_argument("--conditions", default="direct,react,drs")
    parser.add_argument("--runs",    type=int, default=1)
    parser.add_argument("--model",  default="Gemini 3.5 Flash (Low)")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    run_benchmarks(
        args.tasks,
        [c.strip() for c in args.conditions.split(",")],
        args.runs,
        args.model,
        run_id=args.run_id,
    )
