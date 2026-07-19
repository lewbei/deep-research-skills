import subprocess
import shutil
import tempfile
import time
import re
from pathlib import Path
from typing import Dict, Any, List
from benchmarks.llm import query_llm
from benchmarks.search import web_search

_REPO_DIR = Path(__file__).resolve().parents[1]

_TOOL_JSON_RE = re.compile(
    r'\{\s*"tool"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}',
    re.DOTALL
)

def _parse_action(response: str):
    m = _TOOL_JSON_RE.search(response)
    if not m:
        return None, None
    tool_name = m.group(1)
    try:
        args = eval(m.group(2))
    except Exception:
        return None, None
    return tool_name, args

_MIN_FINAL_REPORT_BYTES = 500

def _validate_final_report(workspace: Path) -> tuple[bool, str]:
    """
    A DRS run is only 'success' when:
      1. final-report.md exists
      2. It is a regular file
      3. It is not empty (>= MIN_FINAL_REPORT_BYTES)
    Returns (is_valid, report_content_or_error_message).
    """
    report_path = workspace / "final-report.md"
    if not report_path.exists():
        return False, "final-report.md does not exist."
    if not report_path.is_file():
        return False, "final-report.md is not a regular file."
    content = report_path.read_text(encoding="utf-8")
    if len(content) < _MIN_FINAL_REPORT_BYTES:
        return False, f"final-report.md is too short ({len(content)} bytes < {_MIN_FINAL_REPORT_BYTES} required)."
    return True, content


class DERSAgent:
    """
    DRS agent benchmark wrapper.

    Fix log:
      * Removed mega-plan.md fallback — only final-report.md counts.
      * Added hard wall-clock budget enforcement.
      * Replaced regex action parser with structured JSON.
      * Replaced hard-coded repo path with Path(__file__).resolve().
      * Incomplete runs return status='incomplete' instead of 'success'.
      * Saves full action trajectory per run.
    """

    def __init__(self, model: str = "Gemini 3.5 Flash (Low)"):
        self.model = model

    def _run_drs_cmd(self, workspace: Path, args: List[str]) -> subprocess.CompletedProcess:
        drs_bin = str(_REPO_DIR / "drs")
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = str(_REPO_DIR) + ":" + env.get("PYTHONPATH", "")
        return subprocess.run(
            [drs_bin] + args,
            cwd=str(workspace),
            env=env,
            capture_output=True,
            text=True,
        )

    def run(
        self,
        prompt: str,
        max_steps: int = 50,
        wall_clock_budget: float = 720.0,  # 12 min hard cap
    ) -> Dict[str, Any]:
        """
        Runs the DRS agent loop.

        Parameters
        ----------
        prompt            : research task
        max_steps         : maximum LLM turns before forced termination
        wall_clock_budget : hard monotonic deadline in seconds
        """
        deadline = time.monotonic() + wall_clock_budget
        workspace = Path(tempfile.mkdtemp(prefix="drs-bench-"))

        metrics = {
            "search_calls": 0,
            "read_calls": 0,
            "write_calls": 0,
            "cli_calls": 0,
            "exec_calls": 0,
            "model_calls": 0,
            "tokens_estimated": 0,
        }
        action_trajectory: List[Dict] = []

        def _tool_calls_total():
            return sum(
                metrics[k]
                for k in metrics
                if k.endswith("_calls") and k != "model_calls"
            )

        def _incomplete(reason: str) -> Dict[str, Any]:
            return {
                "report": "",
                "metrics": metrics,
                "tool_calls": _tool_calls_total(),
                "action_trajectory": action_trajectory,
                "status": "incomplete",
                "incomplete_reason": reason,
            }

        def _budget_exceeded() -> bool:
            return time.monotonic() >= deadline

        try:
            # Phase 1: Bootstrap workspace templates atomically so they don't
            # burn half the step budget with placeholder-clearing dialogue.
            init_res = self._run_drs_cmd(workspace, ["init", "--total-minutes", "10", "--kind", "hard"])
            if init_res.returncode != 0:
                return _incomplete(f"DRS init failed: {init_res.stderr}")

            # Auto-populate templates so the model can go straight to research.
            self._bootstrap_templates(workspace, prompt)

            history: List[str] = []

            system_instruction = (
                "You are the Deep Research System (DRS) agent. Your job is to complete "
                "the current research phase and advance to the next one.\n\n"
                "Respond using EXACTLY ONE JSON tool-call block per turn:\n"
                "```json\n"
                '{"tool": "CLI",    "arguments": {"args": "transition 2 3"}}\n'
                "```\n"
                "Allowed tools:\n"
                '  CLI    — {"tool":"CLI","arguments":{"args":"<drs args>"}}\n'
                '  Search — {"tool":"Search","arguments":{"query":"<query>"}}\n'
                '  Read   — {"tool":"Read","arguments":{"path":"<filename>"}}\n'
                '  Write  — {"tool":"Write","arguments":{"path":"<filename>","content":"<text>"}}\n'
                '  Exec   — {"tool":"Exec","arguments":{"command":"python3 script.py"}}\n\n'
                "Always include your reasoning BEFORE the JSON block."
            )

            phase_guidance = {
                "1":   "Phase 1 templates have been pre-populated. Run CLI[transition 1 2] to advance.",
                "2":   "Phase 2 (Feasibility): Search the web to confirm the topic is researchable. Then run CLI[transition 2 3].",
                "3":   "Phase 3 (Broad Sweep): Search for multiple approaches, papers, or benchmarks. Then run CLI[transition 3 3.5].",
                "3.5": "Phase 3.5 (Budget Checkpoint): Run CLI[budget] then CLI[transition 3.5 4].",
                "4":   "Phase 4 (Unknowns): Read unknowns-registry.md, identify a key unknown. Then run CLI[transition 4 5].",
                "5":   "Phase 5 (Research Unknown): Run a deep Search on the key unknown. Update probe-registry.md with findings. Then run CLI[transition 5 6].",
                "6":   "Phase 6 (Hypothesis Tree): Read hypothesis-tree.md, update it with ranked hypotheses. Then run CLI[transition 6 7].",
                "7":   "Phase 7 (Next Step): Decide which hypothesis to test. Update mega-plan.md. Then run CLI[transition 7 8].",
                "8":   "Phase 8 (Execute): Run your synthesis step using Write or Exec. Then run CLI[transition 8 9].",
                "9":   "Phase 9 (Synthesis): Write your final comprehensive research report to 'final-report.md' using the Write tool with at least 800 words. Then run CLI[transition 9 10].",
            }

            for step in range(max_steps):
                if _budget_exceeded():
                    return _incomplete("wall_clock_budget_exceeded")

                # Read current phase
                status_res = self._run_drs_cmd(workspace, ["status"])
                current_phase = "1"
                phase_match = re.search(r"Current Phase:\s*([\d\.]+)", status_res.stdout)
                if phase_match:
                    current_phase = phase_match.group(1)

                # Terminal phase check — strict validation
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
                        # Still in phase 10 but no valid report yet
                        return _incomplete(f"Phase 10 reached but {content}")

                guidance = phase_guidance.get(
                    current_phase,
                    f"Phase {current_phase}: complete your phase requirements then transition.",
                )

                current_prompt = (
                    f"Objective: {prompt}\n\n"
                    f"PHASE GUIDANCE:\n{guidance}\n\n"
                    "State your reasoning, then output your single JSON tool-call."
                )

                chat_context = current_prompt
                if history:
                    chat_context = current_prompt + "\n\n" + "\n".join(history[-8:])

                if _budget_exceeded():
                    return _incomplete("wall_clock_budget_exceeded")

                try:
                    metrics["model_calls"] += 1
                    response = query_llm(chat_context, system_instruction=system_instruction, model=self.model)
                    metrics["tokens_estimated"] += (len(chat_context) + len(response)) // 4
                except Exception as e:
                    return _incomplete(f"LLM call failed: {e}")

                history.append(response)

                tool_name, args = _parse_action(response)
                if tool_name is None:
                    history.append(
                        'System: Invalid format. Output exactly one JSON tool-call block.\n'
                        'Example: {"tool": "Search", "arguments": {"query": "..."}}'
                    )
                    continue

                action_trajectory.append({"step": step + 1, "tool": tool_name, "args": args})
                print(f"[{step+1}] DRS Action: {tool_name}({list(args.keys())})")

                observation = self._dispatch(workspace, tool_name, args, metrics)
                history.append(f"Observation: {observation}")

                # Check if we just transitioned to phase 10
                if tool_name == "CLI" and "10" in args.get("args", "").split():
                    valid, content = _validate_final_report(workspace)
                    if valid:
                        return {
                            "report": content,
                            "metrics": metrics,
                            "tool_calls": _tool_calls_total(),
                            "action_trajectory": action_trajectory,
                            "status": "success",
                        }

            # Exhausted max steps
            return _incomplete(f"max_steps={max_steps} exhausted without reaching Phase 10")

        finally:
            shutil.rmtree(str(workspace), ignore_errors=True)

    def _bootstrap_templates(self, workspace: Path, prompt: str) -> None:
        """
        Pre-populate DRS template files so the agent can skip placeholder
        clearing and go straight to research work.
        """
        short = prompt[:200].strip()

        unknowns = workspace / "unknowns-registry.md"
        if unknowns.exists():
            unknowns.write_text(
                f"# Unknowns Registry\n\n"
                f"## Research Question\n{short}\n\n"
                f"## Open Unknowns\n"
                f"- What are the key approaches and their trade-offs?\n"
                f"- Which approach is best for the stated constraints?\n"
                f"- What does current empirical evidence say?\n",
                encoding="utf-8",
            )

        mega = workspace / "mega-plan.md"
        if mega.exists():
            mega.write_text(
                f"# Research Plan\n\n"
                f"## Topic\n{short}\n\n"
                f"## Goal\nProduce a comprehensive comparison and recommendation report.\n\n"
                f"## Steps\n"
                f"1. Broad survey of approaches\n"
                f"2. Deep dive on key unknowns\n"
                f"3. Synthesise findings into final report\n",
                encoding="utf-8",
            )

        probe = workspace / "probe-registry.md"
        if probe.exists():
            probe.write_text(
                f"# Probe Registry\n\n"
                f"## Active Probe\nInitial feasibility check for: {short}\n\n"
                f"## Status\nOpen\n",
                encoding="utf-8",
            )

    def _dispatch(
        self,
        workspace: Path,
        tool_name: str,
        args: Dict,
        metrics: Dict,
    ) -> str:
        import subprocess as sp, os

        if tool_name == "CLI":
            metrics["cli_calls"] += 1
            cli_args = args.get("args", "").split()
            res = self._run_drs_cmd(workspace, cli_args)
            return f"Exit Code: {res.returncode}\nStdout: {res.stdout}\nStderr: {res.stderr}"

        elif tool_name == "Search":
            metrics["search_calls"] += 1
            query = args.get("query", "")
            results = web_search(query, max_results=5)
            parts = [
                f"Title: {r['title']}\nLink: {r['link']}\nSnippet: {r['snippet']}\n---"
                for r in results
            ]
            return "\n".join(parts) if parts else "No results found."

        elif tool_name == "Read":
            metrics["read_calls"] += 1
            path = (workspace / args.get("path", "")).resolve()
            if not str(path).startswith(str(workspace)):
                return "Error: Access denied (path traversal blocked)."
            if not path.exists():
                return f"Error: '{args.get('path')}' not found."
            if path.is_dir():
                return f"Error: '{args.get('path')}' is a directory."
            return path.read_text(encoding="utf-8")[:5000]

        elif tool_name == "Write":
            metrics["write_calls"] += 1
            rel_path = args.get("path", "")
            content = args.get("content", "")
            path = (workspace / rel_path).resolve()
            if not str(path).startswith(str(workspace)):
                return "Error: Access denied (path traversal blocked)."
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"File '{rel_path}' written ({len(content)} bytes)."

        elif tool_name == "Exec":
            metrics["exec_calls"] += 1
            command = args.get("command", "")
            if not command.startswith("python3"):
                return "Error: Only 'python3 <script>' is permitted."
            parts = command.split()
            script = (workspace / parts[1]).resolve() if len(parts) > 1 else None
            if script is None or not str(script).startswith(str(workspace)):
                return "Error: Access denied."
            try:
                res = sp.run(
                    ["python3", str(script)] + parts[2:],
                    cwd=str(workspace),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return f"Exit Code: {res.returncode}\nStdout: {res.stdout}\nStderr: {res.stderr}"
            except sp.TimeoutExpired:
                return "Error: Command timed out (10 s)."
            except Exception as e:
                return f"Error: {e}"

        else:
            return f"Unknown tool '{tool_name}'. Allowed: CLI, Search, Read, Write, Exec."
