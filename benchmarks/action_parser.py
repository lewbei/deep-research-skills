"""
benchmarks/action_parser.py
---------------------------
Shared, safe JSON tool-call parser used by react.py and drs.py.

Model responses must contain a fenced ```json ... ``` block holding exactly:
  {"tool": "<name>", "arguments": {<key>: <value>, ...}}

Design decisions:
  - Uses json.loads() only — no eval().
  - Scans all ```json blocks in the response (last-match wins, allowing
    the model to reason before the action).
  - Non-greedy regex on the fence avoids truncation when report content
    contains braces or nested code blocks.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def parse_action(response: str) -> tuple[str | None, dict[str, Any] | None]:
    """
    Extract the last valid JSON tool-call block from a model response.

    Returns (tool_name, arguments_dict) on success, or (None, None) if no
    valid block is found.
    """
    blocks = _FENCE_RE.findall(response)

    for block in reversed(blocks):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue

        if (
            isinstance(payload, dict)
            and isinstance(payload.get("tool"), str)
            and isinstance(payload.get("arguments"), dict)
        ):
            return payload["tool"], payload["arguments"]

    return None, None
