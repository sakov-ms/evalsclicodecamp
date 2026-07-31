"""AssertionJudge evaluator — LLM-based judge for behavioural/structural assertions.

Evaluates whether an agent response satisfies a list of free-text assertions.
Each assertion carries a ``level`` ("critical" or "nice-to-have") that affects
its weight in the final score.

Scoring:
  - Critical assertions are weighted 2×; nice-to-have assertions are weighted 1×.
  - The raw weighted score is mapped onto a 1-5 Likert scale.
  - A single critical failure caps the score at `threshold - 1` (so with the
    default threshold 3, the evaluation cannot pass if any critical assertion fails).
Reference it from an eval document like:

    "evaluators": {
        "AssertionJudge": {
            "options": {
                "assertions": [
                    {
                        "text": "Does not direct to Software Center unless available",
                        "level": "critical"
                    },
                    {
                        "text": "Steps are in chronological order",
                        "level": "nice-to-have"
                    }
                ]
            }
        }
    }
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from promptflow.client import load_flow


class AssertionJudge:
    """LLM-based evaluator that judges free-text assertions with weighted scoring."""

    # Weight multipliers by level
    _WEIGHTS = {
        "critical": 2.0,
        "nice-to-have": 1.0,
    }

    def __init__(
        self,
        *,
        model_config: Any,
        threshold: float = 3,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        prepared = dict(model_config)
        prepared.setdefault(
            "type",
            "azure_openai" if "azure_endpoint" in prepared else "openai",
        )
        self._flow = load_flow(
            source=os.path.join(os.path.dirname(__file__), "AssertionJudge.prompty"),
            model={"configuration": prepared},
        )
        self._threshold = threshold

        opts = options or {}
        raw_assertions = opts.get("assertions", [])
        self._assertions: List[Dict[str, str]] = []
        for a in raw_assertions:
            if isinstance(a, str):
                self._assertions.append({"text": a, "level": "critical"})
            elif isinstance(a, dict) and a.get("text"):
                level = a.get("level", "critical").lower()
                if level not in self._WEIGHTS:
                    level = "critical"
                self._assertions.append({"text": a["text"], "level": level})

    def __call__(
        self,
        *,
        prompt: str = "",
        expected_response: str = "",
        response: str = "",
        context: str = "",
        **_: Any,
    ) -> Dict[str, Any]:
        if not self._assertions:
            return {
                "result": "error",
                "score": 0,
                "error": "AssertionJudge requires options.assertions to be a non-empty list.",
                "threshold": self._threshold,
            }

        # Build the numbered assertions block for the prompt
        lines: List[str] = []
        for i, a in enumerate(self._assertions, 1):
            tag = "[CRITICAL]" if a["level"] == "critical" else "[NICE-TO-HAVE]"
            lines.append(f"{i}. {tag} {a['text']}")
        assertions_block = "\n".join(lines)

        raw = self._flow(
            user_prompt=prompt,
            response=response,
            assertions_block=assertions_block,
        )

        return self._compute_score(raw)

    def _compute_score(self, raw: Any) -> Dict[str, Any]:
        try:
            parsed = self._parse_json(raw)
            results_list = parsed.get("results", [])
            if not isinstance(results_list, list):
                raise ValueError("'results' is not a list")
        except Exception as exc:
            return {
                "result": "error",
                "score": 0,
                "error": f"AssertionJudge returned invalid results: {exc}",
                "threshold": self._threshold,
            }

        # Map results back by id (skip malformed entries)
        verdicts: Dict[int, Dict[str, Any]] = {}
        for r in results_list:
            if not isinstance(r, dict):
                continue
            rid = r.get("id")
            if rid is None:
                continue
            try:
                verdicts[int(rid)] = r
            except (TypeError, ValueError):
                continue
        total_weight = 0.0
        earned_weight = 0.0
        critical_failures: List[str] = []
        all_details: List[str] = []

        for i, assertion in enumerate(self._assertions, 1):
            level = assertion["level"]
            weight = self._WEIGHTS.get(level, 1.0)
            total_weight += weight

            verdict = verdicts.get(i)
            if verdict and verdict.get("satisfied"):
                earned_weight += weight
                all_details.append(f"✅ [{level}] {assertion['text']}")
            else:
                reason = verdict.get("reason", "no reason given") if verdict else "not evaluated"
                all_details.append(f"❌ [{level}] {assertion['text']} — {reason}")
                if level == "critical":
                    critical_failures.append(assertion["text"])

        # Weighted ratio → 1-5 scale
        ratio = earned_weight / total_weight if total_weight > 0 else 0
        raw_score = 1 + 4 * ratio  # maps 0→1, 1→5

        # Any critical failure → hard fail (cap at threshold - 1)
        if critical_failures:
            raw_score = min(raw_score, self._threshold - 1)

        score = round(raw_score)
        score = max(1, min(5, score))

        # Build reason summary — group passed and failed for readability
        n_passed = sum(1 for d in all_details if d.startswith("✅"))
        n_failed = sum(1 for d in all_details if d.startswith("❌"))
        n_total = len(self._assertions)

        passed_lines = [d for d in all_details if d.startswith("✅")]
        failed_lines = [d for d in all_details if d.startswith("❌")]

        summary_parts: List[str] = []
        summary_parts.append(f"{n_passed}/{n_total} assertions satisfied, {n_failed} failed.")

        if failed_lines:
            summary_parts.append("")
            summary_parts.append(f"--- FAILED ({n_failed}) ---")
            summary_parts.extend(failed_lines)

        if passed_lines:
            summary_parts.append("")
            summary_parts.append(f"--- PASSED ({n_passed}) ---")
            summary_parts.extend(passed_lines)

        summary = "\n".join(summary_parts)

        return {
            "score": score,
            "threshold": self._threshold,
            "result": "pass" if score >= self._threshold else "fail",
            "reason": summary,
        }

    @staticmethod
    def _parse_json(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if not match:
                    raise ValueError(f"AssertionJudge returned non-JSON: {raw!r}")
                return json.loads(match.group(0))
        raise ValueError(f"Unexpected response type: {type(raw).__name__}")
