import re
import os
from typing import Dict, Any, List
from benchmarks.llm import query_llm
from benchmarks.search import web_search

class ReactAgent:
    def __init__(self, model: str = "Gemini 3.5 Flash (Low)"):
        self.model = model
        
    def run(self, prompt: str, max_steps: int = 15) -> Dict[str, Any]:
        """
        Runs the ReAct loop on the given prompt.
        """
        system_instruction = (
            "You are a deep research agent. You must research the user's topic and write a comprehensive, "
            "detailed, objective report. You have access to the following tools:\n"
            "1. Search[query] - Searches the web and returns a list of results (title, link, snippet).\n"
            "2. Read[filepath] - Reads the contents of a local file in the workspace.\n"
            "3. Respond[report] - Ends the loop and submits your final completed report.\n\n"
            "Use the ReAct cycle:\n"
            "Thought: <your reasoning about the next step>\n"
            "Action: <ToolName>[<args>]\n"
            "Observation: <result of the tool execution>\n\n"
            "Start by thinking, then calling a tool. Loop until you have gathered enough information, "
            "then use Action: Respond[your final complete report]. Do not output placeholders."
        )
        
        history = []
        current_prompt = f"Objective: {prompt}\n\nBegin. Start with a Thought."
        tool_calls = 0
        
        for step in range(max_steps):
            # Format conversational history
            chat_context = current_prompt
            if history:
                chat_context = current_prompt + "\n\n" + "\n".join(history)
                
            try:
                # Query LLM
                response = query_llm(chat_context, system_instruction=system_instruction, model=self.model)
            except Exception as e:
                return {
                    "report": f"ReAct execution failed: {e}",
                    "tool_calls": tool_calls,
                    "status": "failed"
                }
                
            history.append(response)
            
            # Parse thought and action
            action_match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response, re.DOTALL)
            if not action_match:
                # If no action is matching, ask the model to produce an action
                history.append("System: Invalid format. Please output an Action: ToolName[arg].")
                continue
                
            tool_name = action_match.group(1).strip()
            tool_arg = action_match.group(2).strip()
            
            print(f"[{step+1}] ReAct Action: {tool_name}[{tool_arg[:100]}]")
            
            if tool_name == "Respond":
                return {
                    "report": tool_arg,
                    "tool_calls": tool_calls,
                    "status": "success"
                }
            elif tool_name == "Search":
                tool_calls += 1
                search_results = web_search(tool_arg, max_results=5)
                # Format observation
                obs_parts = []
                for res in search_results:
                    obs_parts.append(f"Title: {res['title']}\nLink: {res['link']}\nSnippet: {res['snippet']}\n---")
                observation = "\n".join(obs_parts) if obs_parts else "No results found."
                history.append(f"Observation: {observation}")
            elif tool_name == "Read":
                tool_calls += 1
                # Sandbox check: prevent directory escapes
                normalized_path = os.path.normpath(tool_arg)
                if normalized_path.startswith("..") or os.path.isabs(normalized_path):
                    observation = "Error: Access denied (path traversal blocked)."
                elif not os.path.exists(normalized_path):
                    observation = f"Error: File '{tool_arg}' not found."
                elif os.path.isdir(normalized_path):
                    observation = f"Error: '{tool_arg}' is a directory."
                else:
                    try:
                        with open(normalized_path, "r", encoding="utf-8") as f:
                            observation = f.read()[:5000] # Read first 5000 chars
                    except Exception as e:
                        observation = f"Error reading file: {e}"
                history.append(f"Observation: {observation}")
            else:
                history.append(f"Observation: Unknown tool '{tool_name}'. Allowed tools: Search, Read, Respond.")
                
        # Timeout/Max steps exceeded fallback
        # Ask for a final response if max steps reached
        final_prompt = chat_context + "\n\nSystem: Maximum steps reached. Output your final complete report now using Action: Respond[report]."
        try:
            response = query_llm(final_prompt, system_instruction=system_instruction, model=self.model)
            action_match = re.search(r"Action:\s*Respond\[(.*?)\]", response, re.DOTALL)
            if action_match:
                return {
                    "report": action_match.group(1).strip(),
                    "tool_calls": tool_calls,
                    "status": "success"
                }
            else:
                # If still no Respond, just return the raw response
                return {
                    "report": response,
                    "tool_calls": tool_calls,
                    "status": "timeout_no_respond"
                }
        except Exception as e:
            return {
                "report": f"ReAct execution timeout recovery failed: {e}",
                "tool_calls": tool_calls,
                "status": "failed"
            }
