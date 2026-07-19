import subprocess
import sys
import os
import json
from typing import Optional

def query_llm(prompt: str, system_instruction: Optional[str] = None, model: str = "Gemini 3.5 Flash (Low)", temperature: float = 0.0) -> str:
    """
    Invokes the agy CLI tool non-interactively using the specified model to get a response.
    """
    # Build prompt, optionally prepending system instructions if supported
    full_prompt = prompt
    if system_instruction:
        full_prompt = f"System Instructions: {system_instruction}\n\nUser Prompt: {prompt}"
        
    cmd = ["agy", "--model", model, "--print", full_prompt]
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Run agy command with 90 seconds timeout
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=90)
            return res.stdout.strip()
        except subprocess.TimeoutExpired:
            print(f"Warning: agy CLI model '{model}' timed out (Attempt {attempt+1}/{max_retries}). Retrying...", file=sys.stderr)
            if attempt == max_retries - 1:
                raise RuntimeError(f"agy CLI execution timed out after {max_retries} attempts.")
        except subprocess.CalledProcessError as e:
            print(f"Error running agy CLI model '{model}': {e.stderr} (Attempt {attempt+1}/{max_retries}). Retrying...", file=sys.stderr)
            if attempt == max_retries - 1:
                raise RuntimeError(f"agy CLI execution failed: {e.stderr}") from e
