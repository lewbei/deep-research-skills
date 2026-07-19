"""
benchmarks/llm.py
-----------------
Thin wrapper around the `agy --print` CLI for non-interactive LLM queries.

Changes:
  - `timeout` parameter now respected (default 90 s, can be overridden by callers
    that track remaining wall-clock budget).
  - Exponential back-off between retries.
  - Quota errors (exit code != 0 with "quota" in stderr) are not retried more
    than once, to avoid burning the retry budget during a hard quota block.
"""

import subprocess
import sys
import time
from typing import Optional


def query_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    model: str = "Gemini 3.5 Flash (Low)",
    temperature: float = 0.0,
    timeout: float = 90.0,
    max_retries: int = 3,
) -> str:
    """
    Invoke `agy --model <model> --print <prompt>` and return the response text.

    Parameters
    ----------
    prompt            : the user prompt
    system_instruction: prepended as a system-level block when provided
    model             : agy model string
    temperature       : unused (agy CLI does not currently expose temperature)
    timeout           : per-attempt subprocess timeout in seconds
    max_retries       : maximum number of attempts before raising RuntimeError
    """
    full_prompt = prompt
    if system_instruction:
        full_prompt = f"System Instructions: {system_instruction}\n\nUser Prompt: {prompt}"

    cmd = ["agy", "--model", model, "--print", full_prompt]

    for attempt in range(1, max_retries + 1):
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
            )
            return res.stdout.strip()

        except subprocess.TimeoutExpired:
            msg = f"agy timed out (attempt {attempt}/{max_retries}, timeout={timeout:.0f}s)"
            print(f"Warning: {msg}", file=sys.stderr)
            if attempt == max_retries:
                raise RuntimeError(msg)
            time.sleep(2 ** attempt)  # 2s, 4s back-off

        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            is_quota = "quota" in stderr.lower()
            msg = f"agy failed (attempt {attempt}/{max_retries}): {stderr.strip()}"
            print(f"Error running agy CLI model '{model}': {stderr.strip()} "
                  f"(Attempt {attempt}/{max_retries}). Retrying...", file=sys.stderr)
            if attempt == max_retries or is_quota:
                raise RuntimeError(msg) from e
            time.sleep(2 ** attempt)

    raise RuntimeError("query_llm: unreachable")
