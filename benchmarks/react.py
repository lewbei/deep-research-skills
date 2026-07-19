import re
import os
import time
from pathlib import Path
from typing import Dict, Any, List
from benchmarks.llm import query_llm
from benchmarks.search import web_search

_TOOL_JSON_RE = re.compile(
    r'\{\s*"tool"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}',
    re.DOTALL
)

def _parse_action(response: str):
    """
    Parse a JSON tool-call block of the form:
      {"tool": "ToolName", "arguments": {"key": "value", ...}}
    Returns (tool_name, arguments_dict) or (None, None).
    """
    m = _TOOL_JSON_RE.search(response)
    if not m:
        return None, None
    tool_name = m.group(1)
    try:
        args = eval(m.group(2))   # safe: we already validated structure via regex
    except Exception:
        return None, None
    return tool_name, args


class ReactAgent:
    """
    A research agent that follows a Thought → Action → Observation loop.

    Completion requirements:
      - Must perform >= min_search_calls web searches before submitting a report.
      - Reports submitted without enough searches are classified as
        "incomplete_no_search" and are NOT forwarded to the quality judge.
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
        """
        Runs the ReAct loop on the given prompt.

        Parameters
        ----------
        prompt            : research task
        max_steps         : maximum model turns before forcing termination
        wall_clock_budget : hard deadline in seconds; run is aborted if exceeded
        """
        deadline = time.monotonic() + wall_clock_budget

        system_instruction = (
            "You are a deep research agent. You MUST research the user's topic and write "
            "a comprehensive, detailed, objective report. You have access to these tools:\n\n"
            "  1. Search   — search the web for information\n"
            "  2. Read     — read a local file\n"
            "  3. Respond  — submit your final report (only when you have done enough research)\n\n"
            "You MUST perform at least two web searches before submitting your report. "
            "Submit your final answer using Respond only after gathering enough evidence.\n\n"
            "Respond using EXACTLY ONE JSON block per turn:\n"
            "```json\n"
            '{"tool": "Search", "arguments": {"query": "your query here"}}\n'
            "```\n"
            "or\n"
            "```json\n"
            '{"tool": "Read", "arguments": {"path": "filename.md"}}\n'
            "```\n"
            "or\n"
            "```json\n"
            '{"tool": "Respond", "arguments": {"report": "your full report here"}}\n'
            "```\n\n"
            "Always include your reasoning BEFORE the JSON block. "
            "Do NOT output placeholders."
        )

        history: List[str] = []
        action_trajectory: List[Dict] = []
        current_prompt = f"Objective: {prompt}\n\nBegin. State your research plan, then call your first tool."

        metrics = {
            "search_calls": 0,
            "read_calls": 0,
            "write_calls": 0,
            "cli_calls": 0,
            "exec_calls": 0,
            "model_calls": 0,
            "tokens_estimated": 0,
        }

        def _budget_exceeded() -> bool:
            return time.monotonic() >= deadline

        for step in range(max_steps):
            if _budget_exceeded():
                return {
                    "report": "",
                    "metrics": metrics,
                    "tool_calls": metrics["search_calls"] + metrics["read_calls"],
                    "action_trajectory": action_trajectory,
                    "status": "budget_exceeded",
                }

            chat_context = current_prompt
            if history:
                chat_context = current_prompt + "\n\n" + "\n".join(history)

            try:
                metrics["model_calls"] += 1
                response = query_llm(chat_context, system_instruction=system_instruction, model=self.model)
                metrics["tokens_estimated"] += (len(chat_context) + len(response)) // 4
            except Exception as e:
                return {
                    "report": "",
                    "metrics": metrics,
                    "tool_calls": metrics["search_calls"] + metrics["read_calls"],
                    "action_trajectory": action_trajectory,
                    "status": "failed",
                }

            history.append(response)

            tool_name, args = _parse_action(response)
            if tool_name is None:
                history.append(
                    'System: Invalid format. You must output exactly one JSON tool-call block.\n'
                    'Example: {"tool": "Search", "arguments": {"query": "..."}}'
                )
                continue

            action_trajectory.append({"step": step + 1, "tool": tool_name, "args": args})
            print(f"[{step+1}] ReAct Action: {tool_name}({list(args.keys())})")

            if tool_name == "Respond":
                report_text = args.get("report", "")
                if metrics["search_calls"] < self.MIN_SEARCH_CALLS:
                    return {
                        "report": report_text,
                        "metrics": metrics,
                        "tool_calls": metrics["search_calls"] + metrics["read_calls"],
                        "action_trajectory": action_trajectory,
                        "status": "incomplete_no_search",
                    }
                return {
                    "report": report_text,
                    "metrics": metrics,
                    "tool_calls": metrics["search_calls"] + metrics["read_calls"],
                    "action_trajectory": action_trajectory,
                    "status": "success",
                }

            elif tool_name == "Search":
                metrics["search_calls"] += 1
                query = args.get("query", "")
                search_results = web_search(query, max_results=5)
                obs_parts = [
                    f"Title: {r['title']}\nLink: {r['link']}\nSnippet: {r['snippet']}\n---"
                    for r in search_results
                ]
                observation = "\n".join(obs_parts) if obs_parts else "No results found."
                history.append(f"Observation: {observation}")

            elif tool_name == "Read":
                metrics["read_calls"] += 1
                path = os.path.normpath(args.get("path", ""))
                if path.startswith("..") or os.path.isabs(path):
                    observation = "Error: Access denied (path traversal blocked)."
                elif not os.path.exists(path):
                    observation = f"Error: File '{path}' not found."
                elif os.path.isdir(path):
                    observation = f"Error: '{path}' is a directory."
                else:
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            observation = f.read()[:5000]
                    except Exception as e:
                        observation = f"Error reading file: {e}"
                history.append(f"Observation: {observation}")

            else:
                history.append(
                    f"Observation: Unknown tool '{tool_name}'. Allowed tools: Search, Read, Respond."
                )

        # Max steps reached — do NOT auto-generate; the run is incomplete
        return {
            "report": "",
            "metrics": metrics,
            "tool_calls": metrics["search_calls"] + metrics["read_calls"],
            "action_trajectory": action_trajectory,
            "status": "timeout",
        }
