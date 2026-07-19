import json
import re
from typing import Dict, Any, List
from benchmarks.llm import query_llm
from benchmarks.tasks import RubricCriterion

class RubricJudge:
    def __init__(self, model: str = "Gemini 3.5 Flash (Low)"):
        self.model = model
        
    def evaluate_criterion(self, report: str, criterion: RubricCriterion) -> Dict[str, Any]:
        """
        Evaluates a single rubric criterion against the generated report.
        """
        judge_prompt = (
            "You are evaluating a research report against a specific rubric criterion.\n\n"
            f"CRITERION TYPE: {criterion.criterion_type.upper()}\n"
            f"CRITERION: {criterion.text}\n\n"
            "REPORT:\n"
            f"{report}\n\n"
            "RULES:\n"
            "- For POSITIVE criteria: verdict is MET if the report satisfies the requirement.\n"
            "- For NEGATIVE criteria: verdict is MET if the report AVOIDS the described pitfall.\n"
            "- Be strict. Vague, generic, or partial satisfaction is UNMET for positive criteria.\n"
            "- Explain your reasoning in 1-2 sentences before giving the verdict.\n\n"
            "Respond strictly with a JSON object in this format:\n"
            '{"explanation": "<reasoning>", "verdict": "MET" or "UNMET"}'
        )
        
        try:
            response = query_llm(judge_prompt, model=self.model, temperature=0.0)
            
            # Extract JSON from response
            json_match = re.search(r"\{.*?\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                verdict = data.get("verdict", "UNMET").strip().upper()
                if verdict not in ["MET", "UNMET"]:
                    verdict = "UNMET"
                return {
                    "explanation": data.get("explanation", "Failed to parse explanation."),
                    "verdict": verdict
                }
            else:
                return {
                    "explanation": f"Failed to extract JSON from raw response: {response}",
                    "verdict": "UNMET"
                }
        except Exception as e:
            return {
                "explanation": f"LLM judge evaluation failed: {e}",
                "verdict": "UNMET"
            }
            
    def evaluate_all(self, report: str, criteria: List[RubricCriterion]) -> List[Dict[str, Any]]:
        results = []
        for crit in criteria:
            res = self.evaluate_criterion(report, crit)
            results.append({
                "criterion_text": crit.text,
                "criterion_type": crit.criterion_type,
                "axis": crit.axis,
                "weight": crit.weight,
                "explanation": res["explanation"],
                "verdict": res["verdict"]
            })
        return results
