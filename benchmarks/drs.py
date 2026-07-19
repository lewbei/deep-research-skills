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
        drs_bin = os.path.join(self.repo_dir, "drs")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.pathsep.join([self.repo_dir, env.get("PYTHONPATH", "")])
        return subprocess.run([drs_bin] + args, cwd=workspace, env=env, capture_output=True, text=True)

    def run(self, prompt: str, max_steps: int = 50) -> Dict[str, Any]:
        """
        Runs the DRS agent simulation loop with dynamic phase guidance to prevent hallucinations.
        """
        workspace = tempfile.mkdtemp(prefix="drs-bench-")
        
        metrics = {
            "search_calls": 0,
            "read_calls": 0,
            "write_calls": 0,
            "cli_calls": 0,
            "exec_calls": 0,
            "model_calls": 0,
            "tokens_estimated": 0
        }
        
        try:
            # 1. Initialize session
            init_res = self._run_drs_cmd(workspace, ["init", "--total-minutes", "10", "--kind", "hard"])
            if init_res.returncode != 0:
                return {
                    "report": f"DRS init failed: {init_res.stderr}",
                    "metrics": metrics,
                    "tool_calls": 0,
                    "status": "failed"
                }
                
            history = []
            
            # System instruction defines the allowed tools and format rules
            system_instruction = (
                "You are the Deep Research System (DRS) agent. Your job is to complete the current research phase.\n"
                "You MUST respond using exactly one action tool call at the end of your response:\n"
                "Action: ToolName[arg]\n\n"
                "Allowed Tools:\n"
                "1. CLI[args...] - Runs the drs CLI tool (e.g., CLI[transition 1 2], CLI[status], CLI[budget]).\n"
                "2. Search[query] - Searches the web.\n"
                "3. Read[filepath] - Reads a file in the workspace.\n"
                "4. Write[filepath, content] - Writes a file in the workspace. Used to clear placeholders.\n"
                "5. Exec[command] - Runs python scripts.\n\n"
                "Always check the instructions for your current phase and execute the required action."
            )
            
            # Phase guide maps current phase to clear instructions
            phase_guidance = {
                "1": "You are in Phase 1 (Goal & Constraints). Read 'unknowns-registry.md' and 'mega-plan.md', overwrite them using Write[filename, content] to remove their placeholders (e.g. replacing 'placeholder — replace with first real unknown' with actual text and '[Project Title]' in mega-plan.md with real text), then run CLI[transition 1 2].",
                "2": "You are in Phase 2 (Feasibility). Perform a Web Search using Search[query] to check for prior solutions, then run CLI[transition 2 3].",
                "3": "You are in Phase 3 (Broad Sweep). Perform a Web Search using Search[query] to map the landscape, then run CLI[transition 3 3.5].",
                "3.5": "You are in Phase 3.5 (Budget Checkpoint). Run CLI[budget] to update the budget mode, then run CLI[transition 3.5 4].",
                "4": "You are in Phase 4 (Check Unknowns). Read 'unknowns-registry.md', select a blocking unknown, then run CLI[transition 4 5].",
                "5": "You are in Phase 5 (Research Unknown). Perform a deep research search using Search[query]. Overwrite 'probe-registry.md' and 'unknowns-registry.md' to remove template placeholders, then run CLI[transition 5 6].",
                "6": "You are in Phase 6 (Hypothesis Tree). Read/update 'hypothesis-tree.md', then run CLI[transition 6 7].",
                "7": "You are in Phase 7 (Next Step). Pick the next execution step and update 'mega-plan.md', then run CLI[transition 7 8].",
                "8": "You are in Phase 8 (Execute). Run your execution probes (using Write, Read, or Exec tools), then run CLI[transition 8 9].",
                "9": "You are in Phase 9 (Proxies & Synthesis). Write your final comprehensive research report to 'final-report.md' using Write[final-report.md, <content>], then run CLI[transition 9 10]."
            }
            
            # Start loop
            for step in range(max_steps):
                # 2. Get current phase from CLI
                status_res = self._run_drs_cmd(workspace, ["status"])
                current_phase = "1"
                phase_match = re.search(r"Current Phase:\s*([\d\.]+)", status_res.stdout)
                if phase_match:
                    current_phase = phase_match.group(1)
                    
                # If we reached Phase 10, check for final report and exit
                if current_phase == "10":
                    report_path = os.path.join(workspace, "final-report.md")
                    if not os.path.exists(report_path):
                        report_path = os.path.join(workspace, "mega-plan.md")
                    if os.path.exists(report_path):
                        with open(report_path, "r", encoding="utf-8") as f:
                            report_content = f.read()
                        return {
                            "report": report_content,
                            "metrics": metrics,
                            "tool_calls": sum(metrics[k] for k in metrics if k.endswith("_calls") and k != "model_calls"),
                            "status": "success"
                        }
                        
                # Get guidance for the active phase
                guidance = phase_guidance.get(current_phase, f"You are in Phase {current_phase}. Complete the phase requirements and transition.")
                
                # Format current prompt
                current_prompt = (
                    f"Objective: {prompt}\n\n"
                    f"SYSTEM GUIDANCE:\n{guidance}\n\n"
                    "Provide your thought and your next action."
                )
                
                chat_context = current_prompt
                if history:
                    chat_context = current_prompt + "\n\n" + "\n".join(history[-10:])
                    
                # Query LLM
                try:
                    metrics["model_calls"] += 1
                    response = query_llm(chat_context, system_instruction=system_instruction, model=self.model)
                    metrics["tokens_estimated"] += (len(chat_context) + len(response)) // 4
                except Exception as e:
                    return {
                        "report": f"DRS execution failed: {e}",
                        "metrics": metrics,
                        "tool_calls": sum(metrics[k] for k in metrics if k.endswith("_calls") and k != "model_calls"),
                        "status": "failed"
                    }
                    
                history.append(response)
                
                # Parse Action
                action_match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response, re.DOTALL)
                if not action_match:
                    print(f"[{step+1}] Warning: No Action format found. Guidance re-prompted.")
                    history.append("System: Invalid format. You must output an action using the exact syntax: Action: ToolName[arguments].")
                    continue
                    
                tool_name = action_match.group(1).strip()
                tool_arg = action_match.group(2).strip()
                
                print(f"[{step+1}] DRS Action: {tool_name}[{tool_arg[:100]}]")
                
                if tool_name == "CLI":
                    metrics["cli_calls"] += 1
                    args = tool_arg.split()
                    cli_res = self._run_drs_cmd(workspace, args)
                    observation = f"Exit Code: {cli_res.returncode}\nStdout: {cli_res.stdout}\nStderr: {cli_res.stderr}"
                    history.append(f"Observation: {observation}")
                    
                    if "transition" in args and "10" in args and cli_res.returncode == 0:
                        report_path = os.path.join(workspace, "final-report.md")
                        if not os.path.exists(report_path):
                            report_path = os.path.join(workspace, "mega-plan.md")
                        if os.path.exists(report_path):
                            with open(report_path, "r", encoding="utf-8") as f:
                                report_content = f.read()
                            return {
                                "report": report_content,
                                "metrics": metrics,
                                "tool_calls": sum(metrics[k] for k in metrics if k.endswith("_calls") and k != "model_calls"),
                                "status": "success"
                            }
                elif tool_name == "Search":
                    metrics["search_calls"] += 1
                    search_results = web_search(tool_arg, max_results=5)
                    obs_parts = []
                    for res in search_results:
                        obs_parts.append(f"Title: {res['title']}\nLink: {res['link']}\nSnippet: {res['snippet']}\n---")
                    observation = "\n".join(obs_parts) if obs_parts else "No results found."
                    history.append(f"Observation: {observation}")
                elif tool_name == "Read":
                    metrics["read_calls"] += 1
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
                    metrics["write_calls"] += 1
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
                    metrics["exec_calls"] += 1
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
                    
            # Check fallback
            report_path = os.path.join(workspace, "final-report.md")
            if not os.path.exists(report_path):
                report_path = os.path.join(workspace, "mega-plan.md")
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report_content = f.read()
                return {
                    "report": report_content,
                    "metrics": metrics,
                    "tool_calls": sum(metrics[k] for k in metrics if k.endswith("_calls") and k != "model_calls"),
                    "status": "success"
                }
                
            return {
                "report": "DRS failed to generate final report within max steps.",
                "metrics": metrics,
                "tool_calls": sum(metrics[k] for k in metrics if k.endswith("_calls") and k != "model_calls"),
                "status": "timeout"
            }
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
