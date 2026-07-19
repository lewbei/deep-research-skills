from typing import Dict, Any
from benchmarks.llm import query_llm

class DirectAgent:
    def __init__(self, model: str = "Gemini 3.5 Flash (Low)"):
        self.model = model
        
    def run(self, prompt: str, wall_clock_budget: float = 720.0) -> Dict[str, Any]:
        """
        Queries the model directly exactly once without any tools.
        """
        system_instruction = (
            "You are a research agent. Research the user's topic and write a comprehensive, "
            "detailed, objective report. Answer directly from your knowledge base. Do not write placeholders."
        )
        
        metrics = {
            "search_calls": 0,
            "read_calls": 0,
            "write_calls": 0,
            "cli_calls": 0,
            "exec_calls": 0,
            "model_calls": 1,
            "tokens_estimated": 0
        }
        
        try:
            response = query_llm(prompt, system_instruction=system_instruction, model=self.model)
            metrics["tokens_estimated"] = (len(prompt) + len(response)) // 4
            return {
                "report": response,
                "metrics": metrics,
                "tool_calls": 0,
                "status": "success"
            }
        except Exception as e:
            return {
                "report": f"Direct execution failed: {e}",
                "metrics": metrics,
                "tool_calls": 0,
                "status": "failed"
            }
