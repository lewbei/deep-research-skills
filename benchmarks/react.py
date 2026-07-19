import re
import os
import time
from pathlib import Path
from typing import Dict, Any, List
from benchmarks.llm import query_llm
from benchmarks.search import web_search
from benchmarks.action_parser import parse_action


class ReactAgent:
    """
    Research agent following a Thought → Action → Observation loop.

    Completion requirements:
      - Must perform >= MIN_SEARCH_CALLS web searches before submitting.
      - Reports submitted without enough searches → status='incomplete_no_search'.
      - Max steps exceeded without Respond → status='timeout'.
      - Wall-clock deadline exceeded → status='budget_exceeded'.

    Tool-call format (fenced JSON block):
      ```json
      {"tool": "Search", "arguments": {"query": "..."}}
      ```
    """

    MIN_SEARCH_CALLS = 2

    def __init__(self, model: str = "Gemini 3.5 Flash (Low)"):
        self.model = model

    def run(
        self,
        prompt: str,
        max_steps: int = 15,
        wall_clock_budget: float = 600.0,
    ) -> Dict[str, Any]:
        deadline = time.monotonic() + wall_clock_budget

        system_instruction = (
            "You are a deep research agent. You MUST research the user's topic "
            "thoroughly and produce a comprehensive, well-cited report.\n\n"
            "You have access to these tools:\n"
            "  Search  — search the web\n"
            "  Read    — read a local file\n"
            "  Respond — submit your final report (only after ≥2 searches)\n\n"
            "You MUST perform at least two web searches before submitting.\n\n"
            "Each turn: write your reasoning, then output EXACTLY ONE fenced JSON block:\n"
            "```json\n"
            '{"tool": "Search", "arguments": {"query": "your query"}}\n'
            "```\n"
            "```json\n"
            '{"tool": "Read", "arguments": {"path": "filename.md"}}\n'
            "```\n"
            "```json\n"
            '{"tool": "Respond", "arguments": {"report": "your full report here"}}\n'
            "```\n\n"
            "Do NOT output placeholders. Do NOT submit without searching first."
        )

        history: List[str] = []
        action_trajectory: List[Dict] = []
        current_prompt = (
            f"Objective: {prompt}\n\n"
            "State your research plan, then call your first Search tool."
        )

        metrics = {
            "search_calls": 0,
            "read_calls": 0,
            "write_calls": 0,
            "cli_calls": 0,
            "exec_calls": 0,
            "model_calls": 0,
            "tokens_estimated": 0,
        }

        def _remaining() -> float:
            return deadline - time.monotonic()

        def _budget_ok() -> bool:
            return time.monotonic() < deadline

        for step in range(max_steps):
            if not _budget_ok():
                return self._result("", metrics, action_trajectory, "budget_exceeded")

            chat_context = current_prompt
            if history:
                chat_context = current_prompt + "\n\n" + "\n".join(history)

            remaining = _remaining()
            try:
                metrics["model_calls"] += 1
                response = query_llm(
                    chat_context,
                    system_instruction=system_instruction,
                    model=self.model,
                    timeout=min(90.0, remaining),
                )
                metrics["tokens_estimated"] += (len(chat_context) + len(response)) // 4
            except Exception as e:
                return self._result("", metrics, action_trajectory, "failed")

            history.append(response)

            tool_name, args = parse_action(response)
            if tool_name is None:
                history.append(
                    "System: Invalid format. Output exactly one fenced ```json block "
                    'with keys "tool" and "arguments".\n'
                    'Example: ```json\n{"tool": "Search", "arguments": {"query": "..."}}\n```'
                )
                continue

            action_trajectory.append({"step": step + 1, "tool": tool_name, "args": args})
            print(f"[{step+1}] ReAct: {tool_name}({list(args.keys())})")

            if tool_name == "Respond":
                report_text = args.get("report", "")
                if metrics["search_calls"] < self.MIN_SEARCH_CALLS:
                    return self._result(
                        report_text, metrics, action_trajectory, "incomplete_no_search"
                    )
                return self._result(report_text, metrics, action_trajectory, "success")

            elif tool_name == "Search":
                metrics["search_calls"] += 1
                query = args.get("query", "")
                results = web_search(query, max_results=5)
                parts = [
                    f"Title: {r['title']}\nLink: {r['link']}\nSnippet: {r['snippet']}\n---"
                    for r in results
                ]
                history.append("Observation: " + ("\n".join(parts) or "No results found."))

            elif tool_name == "Read":
                metrics["read_calls"] += 1
                raw = args.get("path", "")
                observation = self._safe_read(raw)
                history.append(f"Observation: {observation}")

            else:
                history.append(
                    f"Observation: Unknown tool '{tool_name}'. "
                    "Allowed: Search, Read, Respond."
                )

        return self._result("", metrics, action_trajectory, "timeout")

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _safe_read(raw_path: str) -> str:
        root = Path.cwd().resolve()
        try:
            target = (root / raw_path).resolve()
            target.relative_to(root)  # raises ValueError on escape
        except ValueError:
            return "Error: path escapes workspace."
        if not target.exists():
            return f"Error: '{raw_path}' not found."
        if target.is_dir():
            return f"Error: '{raw_path}' is a directory."
        try:
            return target.read_text(encoding="utf-8")[:5000]
        except Exception as e:
            return f"Error reading file: {e}"

    @staticmethod
    def _result(report, metrics, trajectory, status):
        return {
            "report": report,
            "metrics": metrics,
            "tool_calls": metrics["search_calls"] + metrics["read_calls"],
            "action_trajectory": trajectory,
            "status": status,
        }
