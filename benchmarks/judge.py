import json
import re
from typing import Dict, Any, List, Optional
from benchmarks.llm import query_llm
from benchmarks.tasks import RubricCriterion

_VERDICT_RE = re.compile(r'"verdict"\s*:\s*"(MET|UNMET)"', re.I)

MAX_JUDGE_RETRIES = 2


class RubricJudge:
    def __init__(self, model: str = "Gemini 3.5 Flash (Low)"):
        self.model = model

    def evaluate_criterion(self, report: str, criterion: RubricCriterion) -> Dict[str, Any]:
        """
        Evaluates a single rubric criterion.

        Returns a dict with keys:
          criterion_text, verdict (MET | UNMET | JUDGE_ERROR), explanation, judge_error
        """
        judge_prompt = (
            "You are evaluating a research report against a rubric criterion.\n\n"
            f"CRITERION TYPE: {criterion.criterion_type.upper()}\n"
            f"CRITERION: {criterion.text}\n\n"
            "REPORT:\n"
            f"{report}\n\n"
            "RULES:\n"
            "- POSITIVE criterion: verdict is MET if the report satisfies the requirement.\n"
            "- NEGATIVE criterion: verdict is MET if the report AVOIDS the pitfall.\n"
            "- Be strict. Vague or partial satisfaction → UNMET for positive criteria.\n"
            "- Explain in 1-2 sentences then give verdict.\n\n"
            "Respond with ONLY this JSON object (no markdown fences, no extra text):\n"
            '{"explanation": "<1-2 sentences>", "verdict": "MET"}\n'
            "or\n"
            '{"explanation": "<1-2 sentences>", "verdict": "UNMET"}'
        )

        last_error: Optional[str] = None

        for attempt in range(1, MAX_JUDGE_RETRIES + 2):  # tries: 1, 2, 3
            try:
                raw = query_llm(judge_prompt, model=self.model, temperature=0.0)
            except Exception as e:
                last_error = f"LLM call failed (attempt {attempt}): {e}"
                continue

            # Try strict json.loads first
            parsed = None
            for extractor in [self._try_json_direct, self._try_json_fence, self._try_json_regex]:
                parsed = extractor(raw)
                if parsed is not None:
                    break

            if parsed is None:
                last_error = f"JSON parse failed (attempt {attempt}): {raw[:200]!r}"
                continue

            verdict = str(parsed.get("verdict", "")).strip().upper()
            if verdict not in ("MET", "UNMET"):
                last_error = f"Invalid verdict '{verdict}' (attempt {attempt})"
                continue

            return {
                "explanation": parsed.get("explanation", ""),
                "verdict": verdict,
                "judge_error": None,
            }

        # All retries exhausted
        return {
            "explanation": f"Judge error after {MAX_JUDGE_RETRIES + 1} attempts: {last_error}",
            "verdict": "JUDGE_ERROR",
            "judge_error": last_error,
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
                "verdict": res["verdict"],
                "judge_error": res["judge_error"],
            })
        return results

    # ── JSON extraction helpers ───────────────────────────────────────────

    @staticmethod
    def _try_json_direct(raw: str) -> Optional[Dict]:
        try:
            return json.loads(raw.strip())
        except Exception:
            return None

    @staticmethod
    def _try_json_fence(raw: str) -> Optional[Dict]:
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        return None

    @staticmethod
    def _try_json_regex(raw: str) -> Optional[Dict]:
        # Last-resort: grab first {...} block
        m = re.search(r"\{[^{}]*\"verdict\"[^{}]*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return None
