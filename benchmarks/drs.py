import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchmarks.action_parser import parse_action
from benchmarks.llm import query_llm
from benchmarks.search import web_search

_REPO_DIR = Path(__file__).resolve().parents[1]

# Minimum word count and structural requirements for a valid final report
_MIN_WORDS = 150        # ~600-800 chars of prose
_MIN_HEADINGS = 2       # at least two markdown headings
_PLACEHOLDER_RE = re.compile(r"\[.*?placeholder.*?\]|\[Project Title\]|TODO", re.I)


def _parse_current_phase(status_stdout: str) -> Optional[str]:
    m = re.search(r"Current Phase:\s*([\d\.]+)", status_stdout)
    return m.group(1) if m else None


def _validate_final_report(workspace: Path) -> tuple[bool, str]:
    """
    A DRS run is only 'success' when final-report.md:
      1. Exists and is a regular file.
      2. Has >= _MIN_WORDS words.
      3. Contains >= _MIN_HEADINGS markdown headings.
      4. Does not contain obvious template placeholders.
    Returns (is_valid, content_or_error_message).
    """
    report_path = workspace / "final-report.md"
    if not report_path.exists():
        return False, "final-report.md does not exist."
    if not report_path.is_file():
        return False, "final-report.md is not a regular file."

    content = report_path.read_text(encoding="utf-8")
    word_count = len(content.split())
    if word_count < _MIN_WORDS:
        return False, f"final-report.md too short ({word_count} words < {_MIN_WORDS} required)."

    heading_count = len(re.findall(r"^#{1,6}\s+", content, re.MULTILINE))
    if heading_count < _MIN_HEADINGS:
        return False, f"final-report.md has only {heading_count} headings (need >= {_MIN_HEADINGS})."

    if _PLACEHOLDER_RE.search(content):
        return False, "final-report.md still contains template placeholders."

    return True, content


class DERSAgent:
    """
    DRS agent benchmark wrapper.

    Fix log:
      * parse_action() uses json.loads() — no eval().
      * Terminal-phase confirmation: after transition, re-read phase from CLI
        AND verify final-report.md passes structural validation.
      * Stronger report validation: word count + headings + placeholder check.
      * Wall-clock budget propagated to every blocking call (model, CLI).
      * Path security via .relative_to() instead of string-prefix comparison.
      * PYTHONPATH built with os.pathsep.
      * Auto-bootstrap templates so no step budget is wasted on placeholders.
      * Saves action_trajectory and incomplete_reason.
    """

    def __init__(self, model: str = "Gemini 3.5 Flash (Low)"):
        self.model = model

    def _run_drs_cmd(
        self,
        workspace: Path,
        args: List[str],
        timeout: float = 60.0,
    ) -> subprocess.CompletedProcess:
        drs_bin = str(_REPO_DIR / "drs")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(_REPO_DIR) + os.pathsep + env.get("PYTHONPATH", "")
        try:
            return subprocess.run(
                [drs_bin] + args,
                cwd=str(workspace),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            # Return a fake result so callers can handle it uniformly
            class _FakeResult:
                returncode = -1
                stdout = ""
                stderr = "drs command timed out"
            return _FakeResult()

    def run(
        self,
        prompt: str,
        max_steps: int = 50,
        wall_clock_budget: float = 720.0,
    ) -> Dict[str, Any]:
        deadline = time.monotonic() + wall_clock_budget
        workspace = Path(tempfile.mkdtemp(prefix="drs-bench-"))

        metrics: Dict[str, int] = {
            "search_calls": 0,
            "read_calls": 0,
            "write_calls": 0,
            "cli_calls": 0,
            "exec_calls": 0,
            "model_calls": 0,
            "tokens_estimated": 0,
        }
        action_trajectory: List[Dict] = []

        def _tool_calls_total() -> int:
            return sum(
                v for k, v in metrics.items()
                if k.endswith("_calls") and k != "model_calls"
            )

        def _remaining() -> float:
            return deadline - time.monotonic()

        def _budget_ok() -> bool:
            return time.monotonic() < deadline

        def _incomplete(reason: str) -> Dict[str, Any]:
            return {
                "report": "",
                "metrics": metrics,
                "tool_calls": _tool_calls_total(),
                "action_trajectory": action_trajectory,
                "status": "incomplete",
                "incomplete_reason": reason,
            }

        try:
            # ── Init workspace ────────────────────────────────────────────
            init_res = self._run_drs_cmd(
                workspace, ["init", "--total-minutes", "10", "--kind", "hard"],
                timeout=min(30.0, _remaining()),
            )
            if init_res.returncode != 0:
                return _incomplete(f"DRS init failed: {init_res.stderr}")

            self._bootstrap_templates(workspace, prompt)

            # ── System prompt ─────────────────────────────────────────────
            system_instruction = (
                "You are the Deep Research System (DRS) agent. Complete the current "
                "phase, then advance.\n\n"
                "Each turn: write your reasoning, then output EXACTLY ONE fenced JSON block:\n"
                "```json\n"
                '{"tool": "CLI", "arguments": {"args": "transition 2 3"}}\n'
                "```\n\n"
                "Allowed tools:\n"
                '  CLI    — {"tool":"CLI",    "arguments":{"args":"<drs sub-command>"}}\n'
                '  Search — {"tool":"Search", "arguments":{"query":"<query>"}}\n'
                '  Read   — {"tool":"Read",   "arguments":{"path":"<filename>"}}\n'
                '  Write  — {"tool":"Write",  "arguments":{"path":"<filename>","content":"<text>"}}\n'
                '  Exec   — {"tool":"Exec",   "arguments":{"command":"python3 script.py"}}\n'
            )

            phase_guidance = {
                "1":   "Phase 1 templates are pre-populated. Transition immediately: CLI[transition 1 2].",
                "2":   "Phase 2 (Feasibility): Search for prior work on the topic. Then CLI[transition 2 3].",
                "3":   "Phase 3 (Broad Sweep): Search for 2-3 approaches or papers. Then CLI[transition 3 3.5].",
                "3.5": "Phase 3.5: CLI[budget] then CLI[transition 3.5 4].",
                "4":   "Phase 4: Read unknowns-registry.md and identify the key unknown. Then CLI[transition 4 5].",
                "5":   "Phase 5: Deep Search on the key unknown. Update probe-registry.md with findings. Then CLI[transition 5 6].",
                "6":   "Phase 6: Read hypothesis-tree.md, add ranked hypotheses. Then CLI[transition 6 7].",
                "7":   "Phase 7: Update mega-plan.md with the chosen execution step. Then CLI[transition 7 8].",
                "8":   "Phase 8: Write or Exec your synthesis. Then CLI[transition 8 9].",
                "9":   (
                    "Phase 9 (FINAL): Write a comprehensive research report of AT LEAST 150 words "
                    "with at least 2 markdown headings to 'final-report.md'. "
                    "Use Write tool. Then CLI[transition 9 10]."
                ),
            }

            history: List[str] = []

            # ── Main loop ─────────────────────────────────────────────────
            for step in range(max_steps):
                if not _budget_ok():
                    return _incomplete("wall_clock_budget_exceeded")

                # Read phase
                status_res = self._run_drs_cmd(
                    workspace, ["status"], timeout=min(15.0, _remaining())
                )
                current_phase = _parse_current_phase(status_res.stdout) or "1"

                # Terminal phase: confirm with authoritative status check
                if current_phase == "10":
                    valid, content = _validate_final_report(workspace)
                    if valid:
                        return {
                            "report": content,
                            "metrics": metrics,
                            "tool_calls": _tool_calls_total(),
                            "action_trajectory": action_trajectory,
                            "status": "success",
                        }
                    else:
                        return _incomplete(f"Phase 10 reached but: {content}")

                guidance = phase_guidance.get(
                    current_phase,
                    f"Phase {current_phase}: complete requirements then transition.",
                )

                chat_context = (
                    f"Objective: {prompt}\n\n"
                    f"PHASE GUIDANCE:\n{guidance}\n\n"
                    "State your reasoning, then output your fenced JSON tool-call."
                )
                if history:
                    chat_context += "\n\n" + "\n".join(history[-8:])

                if not _budget_ok():
                    return _incomplete("wall_clock_budget_exceeded")

                try:
                    metrics["model_calls"] += 1
                    response = query_llm(
                        chat_context,
                        system_instruction=system_instruction,
                        model=self.model,
                        timeout=min(90.0, _remaining()),
                    )
                    metrics["tokens_estimated"] += (len(chat_context) + len(response)) // 4
                except Exception as e:
                    return _incomplete(f"LLM call failed: {e}")

                history.append(response)

                tool_name, args = parse_action(response)
                if tool_name is None:
                    history.append(
                        "System: Invalid format. Output exactly one fenced ```json block.\n"
                        'Example: ```json\n{"tool": "Search", "arguments": {"query": "..."}}\n```'
                    )
                    continue

                action_trajectory.append({"step": step + 1, "tool": tool_name, "args": args})
                print(f"[{step+1}] DRS: {tool_name}({list(args.keys())})")

                observation = self._dispatch(workspace, tool_name, args, metrics, _remaining)
                history.append(f"Observation: {observation}")

                # After a CLI transition, check if we reached Phase 10
                if tool_name == "CLI":
                    cli_args = args.get("args", "").split()
                    if (
                        "transition" in cli_args
                        and "10" in cli_args
                    ):
                        # Re-read phase authoritatively
                        recheck = self._run_drs_cmd(
                            workspace, ["status"], timeout=min(15.0, _remaining())
                        )
                        confirmed_phase = _parse_current_phase(recheck.stdout)
                        if confirmed_phase == "10":
                            valid, content = _validate_final_report(workspace)
                            if valid:
                                return {
                                    "report": content,
                                    "metrics": metrics,
                                    "tool_calls": _tool_calls_total(),
                                    "action_trajectory": action_trajectory,
                                    "status": "success",
                                }
                            else:
                                # Still need to write the report — don't exit, let loop continue
                                history.append(
                                    f"System: Reached Phase 10 but report is invalid: {content}. "
                                    "You must write final-report.md with >=150 words and >=2 headings."
                                )

            return _incomplete(f"max_steps={max_steps} exhausted without reaching Phase 10")

        finally:
            shutil.rmtree(str(workspace), ignore_errors=True)

    # ── Template bootstrap ────────────────────────────────────────────────

    def _bootstrap_templates(self, workspace: Path, prompt: str) -> None:
        short = prompt[:200].strip()

        for filename, content in [
            (
                "unknowns-registry.md",
                f"# Unknowns Registry\n\n## Research Question\n{short}\n\n"
                "## Open Unknowns\n- What approaches exist and what are their trade-offs?\n"
                "- Which approach best fits the stated constraints?\n"
                "- What does current empirical evidence say?\n",
            ),
            (
                "mega-plan.md",
                f"# Research Plan\n\n## Topic\n{short}\n\n"
                "## Goal\nProduce a comprehensive comparison and recommendation report.\n\n"
                "## Steps\n1. Broad survey\n2. Deep dive on key unknowns\n3. Synthesise\n",
            ),
            (
                "probe-registry.md",
                f"# Probe Registry\n\n## Active Probe\nFeasibility check for: {short}\n\n"
                "## Status\nOpen\n",
            ),
        ]:
            path = workspace / filename
            if path.exists():
                path.write_text(content, encoding="utf-8")

    # ── Tool dispatcher ───────────────────────────────────────────────────

    def _dispatch(
        self,
        workspace: Path,
        tool_name: str,
        args: Dict,
        metrics: Dict,
        remaining_fn,
    ) -> str:
        if tool_name == "CLI":
            metrics["cli_calls"] += 1
            cli_args = args.get("args", "").split()
            res = self._run_drs_cmd(workspace, cli_args, timeout=min(30.0, remaining_fn()))
            return (
                f"Exit Code: {res.returncode}\n"
                f"Stdout: {res.stdout}\n"
                f"Stderr: {res.stderr}"
            )

        elif tool_name == "Search":
            metrics["search_calls"] += 1
            results = web_search(args.get("query", ""), max_results=5)
            parts = [
                f"Title: {r['title']}\nLink: {r['link']}\nSnippet: {r['snippet']}\n---"
                for r in results
            ]
            return "\n".join(parts) or "No results found."

        elif tool_name == "Read":
            metrics["read_calls"] += 1
            return self._safe_read(workspace, args.get("path", ""))

        elif tool_name == "Write":
            metrics["write_calls"] += 1
            return self._safe_write(workspace, args.get("path", ""), args.get("content", ""))

        elif tool_name == "Exec":
            metrics["exec_calls"] += 1
            return self._safe_exec(workspace, args.get("command", ""), remaining_fn)

        else:
            return f"Unknown tool '{tool_name}'. Allowed: CLI, Search, Read, Write, Exec."

    # ── Sandboxed file operations ─────────────────────────────────────────

    @staticmethod
    def _sandbox(workspace: Path, rel_path: str) -> Optional[Path]:
        """Return resolved absolute path if it stays inside workspace, else None."""
        try:
            target = (workspace / rel_path).resolve()
            target.relative_to(workspace.resolve())  # raises ValueError on escape
            return target
        except (ValueError, Exception):
            return None

    def _safe_read(self, workspace: Path, rel_path: str) -> str:
        target = self._sandbox(workspace, rel_path)
        if target is None:
            return "Error: path escapes workspace."
        if not target.exists():
            return f"Error: '{rel_path}' not found."
        if target.is_dir():
            return f"Error: '{rel_path}' is a directory."
        try:
            return target.read_text(encoding="utf-8")[:5000]
        except Exception as e:
            return f"Error reading file: {e}"

    def _safe_write(self, workspace: Path, rel_path: str, content: str) -> str:
        target = self._sandbox(workspace, rel_path)
        if target is None:
            return "Error: path escapes workspace."
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Written '{rel_path}' ({len(content.split())} words)."
        except Exception as e:
            return f"Error writing: {e}"

    def _safe_exec(self, workspace: Path, command: str, remaining_fn) -> str:
        if not command.startswith("python3 "):
            return "Error: only 'python3 <script>' is permitted."
        parts = command.split()
        if len(parts) < 2:
            return "Error: missing script name."
        script = self._sandbox(workspace, parts[1])
        if script is None:
            return "Error: script path escapes workspace."
        try:
            res = subprocess.run(
                ["python3", str(script)] + parts[2:],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=min(10.0, remaining_fn()),
            )
            return f"Exit: {res.returncode}\nStdout: {res.stdout}\nStderr: {res.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: exec timed out."
        except Exception as e:
            return f"Error: {e}"
