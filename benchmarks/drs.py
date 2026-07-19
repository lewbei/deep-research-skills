import subprocess
import shutil
import tempfile
import os
import re
import json
from typing import Dict, Any, List
from benchmarks.llm import query_llm
from benchmarks.search import web_search

class DERSAgent:
    def __init__(self, model: str = "Gemini 3.5 Flash (Low)"):
        self.model = model
        self.repo_dir = "/home/lewbei/deep_learning/research planning/deep-research-skills"
        
    def _run_drs_cmd(self, workspace: str, args: List[str]) -> subprocess.CompletedProcess:
        # Runs the drs wrapper CLI
        drs_bin = os.path.join(self.repo_dir, "drs")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.pathsep.join([self.repo_dir, env.get("PYTHONPATH", "")])
        return subprocess.run([drs_bin] + args, cwd=workspace, env=env, capture_output=True, text=True)

    def run(self, prompt: str, max_steps: int = 30) -> Dict[str, Any]:
        """
        Runs the DRS agent simulation loop using the drs CLI tool and workspace templates.
        """
        # 1. Create temporary workspace and initialize
        workspace = tempfile.mkdtemp(prefix="drs-bench-")
        
        try:
            # Run drs init
            init_res = self._run_drs_cmd(workspace, ["init", "--total-minutes", "10", "--kind", "hard"])
            if init_res.returncode != 0:
                return {
                    "report": f"DRS init failed: {init_res.stderr}",
                    "tool_calls": 0,
                    "status": "failed"
                }
                
            tool_calls = 0
            history = []
            
            system_instruction = (
                "You are the Deep Research System (DRS) orchestrator. Your job is to run the interleaved research-and-execute loop.\n"
                "You MUST use the `drs` CLI tool to progress through the phases from 1 to 10. The current phase is tracked by the CLI.\n"
                "Here is the exact step-by-step sequence of phases you MUST execute:\n"
                "- Phase 1: Read unknowns-registry.md and mega-plan.md, edit them to remove/replace their placeholders, then run Action: CLI[transition 1 2].\n"
                "- Phase 2: Perform web search for feasibility, then run Action: CLI[transition 2 3].\n"
                "- Phase 3: Perform broad research sweep, then run Action: CLI[transition 3 3.5].\n"
                "- Phase 3.5: Run Action: CLI[budget] to update budget mode, then run Action: CLI[transition 3.5 4].\n"
                "- Phase 4: Select blocking unknowns in unknowns-registry.md, then run Action: CLI[transition 4 5].\n"
                "- Phase 5: Research unknowns, edit unknowns-registry.md and probe-registry.md (clear placeholders in both), then run Action: CLI[transition 5 6].\n"
                "- Phase 6: Update hypothesis-tree.md, then run Action: CLI[transition 6 7].\n"
                "- Phase 7: Pick next execution step in mega-plan.md, then run Action: CLI[transition 7 8].\n"
                "- Phase 8: Execute code/experiments (use Exec[...] or write files), then run Action: CLI[transition 8 9].\n"
                "- Phase 9: Learn/validate proxies, write your final research report to 'final-report.md', then run Action: CLI[transition 9 10].\n\n"
                "Allowed Tools:\n"
                "1. CLI[args...] - Runs a `drs` command (e.g. CLI[transition 1 2], CLI[status], CLI[budget]).\n"
                "2. Search[query] - Searches the web.\n"
                "3. Read[filepath] - Reads a file.\n"
                "4. Write[filepath, content] - Writes a file. MUST be used to overwrite templates and clear placeholders before transitioning!\n"
                "5. Exec[command] - Runs python scripts.\n\n"
                "CRITICAL: To transition to the next phase, you MUST clear all placeholders in the required files. For example:\n"
                "- Before transition 1 2: Write to 'unknowns-registry.md' and replace 'placeholder — replace with first real unknown' with actual text, and replace '[Project Title]' in 'mega-plan.md' with actual text.\n"
                "- Before transition 5 6: Clear placeholders in 'probe-registry.md' and 'unknowns-registry.md'.\n"
                "- Before transition 9 10: You must Write the final research report to 'final-report.md'.\n\n"
                "Start by running CLI[status] to confirm the workspace is initialized."
            )
            
            current_prompt = f"Objective: {prompt}\n\nBegin. Start by thinking, then calling a tool."
            
            for step in range(max_steps):
                # Format context
                chat_context = current_prompt
                if history:
                    chat_context = current_prompt + "\n\n" + "\n".join(history[-10:]) # Keep last 10 turns to avoid context overflow
                    
                # Query LLM
                try:
                    response = query_llm(chat_context, system_instruction=system_instruction, model=self.model)
                except Exception as e:
                    return {
                        "report": f"DRS execution failed: {e}",
                        "tool_calls": tool_calls,
                        "status": "failed"
                    }
                    
                history.append(response)
                
                # Parse action
                action_match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response, re.DOTALL)
                if not action_match:
                    print(f"[{step+1}] Warning: No Action format found in model response: {response[:300]}...")
                    # Check if model finished or transitioned to phase 10
                    # Let's inspect if final-report.md exists
                    report_path = os.path.join(workspace, "final-report.md")
                    if os.path.exists(report_path):
                        with open(report_path, "r", encoding="utf-8") as f:
                            report_content = f.read()
                        return {
                            "report": report_content,
                            "tool_calls": tool_calls,
                            "status": "success"
                        }
                    history.append("System: Invalid format. You must output an action using the exact syntax: Action: ToolName[arguments] (e.g., Action: CLI[status] or Action: Write[filename, content]).")
                    continue
                    
                tool_name = action_match.group(1).strip()
                tool_arg = action_match.group(2).strip()
                
                print(f"[{step+1}] DRS Action: {tool_name}[{tool_arg[:100]}]")
                
                if tool_name == "CLI":
                    tool_calls += 1
                    # Parse CLI args
                    args = tool_arg.split()
                    cli_res = self._run_drs_cmd(workspace, args)
                    observation = f"Exit Code: {cli_res.returncode}\nStdout: {cli_res.stdout}\nStderr: {cli_res.stderr}"
                    history.append(f"Observation: {observation}")
                    
                    # If transitioned to phase 10, finish
                    if "transition" in args and "10" in args and cli_res.returncode == 0:
                        report_path = os.path.join(workspace, "final-report.md")
                        if not os.path.exists(report_path):
                            # Try reading from mega-plan or landscape-table as fallback
                            report_path = os.path.join(workspace, "mega-plan.md")
                        if os.path.exists(report_path):
                            with open(report_path, "r", encoding="utf-8") as f:
                                report_content = f.read()
                            return {
                                "report": report_content,
                                "tool_calls": tool_calls,
                                "status": "success"
                            }
                elif tool_name == "Search":
                    tool_calls += 1
                    search_results = web_search(tool_arg, max_results=5)
                    obs_parts = []
                    for res in search_results:
                        obs_parts.append(f"Title: {res['title']}\nLink: {res['link']}\nSnippet: {res['snippet']}\n---")
                    observation = "\n".join(obs_parts) if obs_parts else "No results found."
                    history.append(f"Observation: {observation}")
                elif tool_name == "Read":
                    tool_calls += 1
                    normalized_path = os.path.normpath(tool_arg)
                    if normalized_path.startswith("..") or os.path.isabs(normalized_path):
                        observation = "Error: Access denied (path traversal blocked)."
                    else:
                        full_path = os.path.join(workspace, normalized_path)
                        if not os.path.exists(full_path):
                            observation = f"Error: File '{tool_arg}' not found."
                        elif os.path.isdir(full_path):
                            observation = f"Error: '{tool_arg}' is a directory."
                        else:
                            try:
                                with open(full_path, "r", encoding="utf-8") as f:
                                    observation = f.read()[:5000]
                            except Exception as e:
                                observation = f"Error reading file: {e}"
                    history.append(f"Observation: {observation}")
                elif tool_name == "Write":
                    tool_calls += 1
                    # Extract target file and contents
                    # format: Write[filename, content]
                    # Since content can have commas, parse carefully. Split at first comma.
                    comma_idx = tool_arg.find(",")
                    if comma_idx == -1:
                        observation = "Error: Invalid Write format. Use Write[filename, content]."
                    else:
                        filename = tool_arg[:comma_idx].strip()
                        content = tool_arg[comma_idx+1:].strip()
                        normalized_path = os.path.normpath(filename)
                        if normalized_path.startswith("..") or os.path.isabs(normalized_path):
                            observation = "Error: Access denied (path traversal blocked)."
                        else:
                            full_path = os.path.join(workspace, normalized_path)
                            try:
                                with open(full_path, "w", encoding="utf-8") as f:
                                    f.write(content)
                                observation = f"File '{filename}' successfully written."
                            except Exception as e:
                                observation = f"Error writing file: {e}"
                    history.append(f"Observation: {observation}")
                elif tool_name == "Exec":
                    tool_calls += 1
                    # Execute python script
                    # For safety, limit commands to python3 scripts in workspace
                    if not tool_arg.startswith("python3"):
                        observation = "Error: Only 'python3 <script>' execution is permitted."
                    else:
                        script_parts = tool_arg.split()
                        if len(script_parts) < 2:
                            observation = "Error: Missing script name."
                        else:
                            script_name = os.path.normpath(script_parts[1])
                            if script_name.startswith("..") or os.path.isabs(script_name):
                                observation = "Error: Access denied."
                            else:
                                try:
                                    res = subprocess.run(["python3", script_name] + script_parts[2:], cwd=workspace, capture_output=True, text=True, timeout=10)
                                    observation = f"Exit Code: {res.returncode}\nStdout: {res.stdout}\nStderr: {res.stderr}"
                                except subprocess.TimeoutExpired:
                                    observation = "Error: Command timed out after 10 seconds."
                                except Exception as e:
                                    observation = f"Error executing: {e}"
                    history.append(f"Observation: {observation}")
                else:
                    history.append(f"Observation: Unknown tool '{tool_name}'. Allowed tools: CLI, Search, Read, Write, Exec.")
                    
            # Check for final report fallback at the end of loop
            report_path = os.path.join(workspace, "final-report.md")
            if not os.path.exists(report_path):
                report_path = os.path.join(workspace, "mega-plan.md")
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report_content = f.read()
                return {
                    "report": report_content,
                    "tool_calls": tool_calls,
                    "status": "success"
                }
                
            return {
                "report": "DRS failed to generate final report within max steps.",
                "tool_calls": tool_calls,
                "status": "timeout"
            }
        finally:
            # Clean up temp workspace
            shutil.rmtree(workspace, ignore_errors=True)
