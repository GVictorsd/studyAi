"""
Insights Agent — transforms raw scores and accumulated mistake context into
actionable, human-readable performance analytics.

Produces:
  • Score trend          (improving / declining / stable / insufficient_data)
  • Average score
  • Strongest / weakest area
  • Numerical accuracy vs theory accuracy (from question_type_scores)
  • AI-computed readiness score (0-100)
  • Consistently weak / strong / improving / declining topics
  • Recurring mistake patterns (surfaced from MistakeAnalysisAgent context)
  • Key insights & targeted recommendations
"""
import json
import re
from typing import Any

import google.generativeai as genai

from app.core.config import settings


genai.configure(api_key=settings.GOOGLE_API_KEY)


INSIGHTS_PROMPT = """
You are an expert academic performance analyst.
Analyse the evaluation history and mistake context below, then produce
a comprehensive performance insight report.

━━━ EVALUATION HISTORY ({num_exams} exam(s)) ━━━
{exam_summaries}

━━━ ACCUMULATED MISTAKE CONTEXT ━━━
{mistake_context}

Return a JSON object with this exact shape (no markdown fences):
{{
  "average_score": <float — average overall score across all exams>,
  "score_trend": "improving" | "declining" | "stable" | "insufficient_data",
  "strongest_area": "<topic/chapter with consistently highest scores, or null>",
  "weakest_area":   "<topic/chapter with consistently lowest scores, or null>",
  "numerical_accuracy": <float 0-100 — avg score on numerical questions, or null if no data>,
  "theory_accuracy":    <float 0-100 — avg score on theory/definition/derivation questions, or null>,
  "readiness_score": <int 0-100 — holistic exam readiness estimate>,
  "consistently_weak_topics":   ["topics weak in 2+ exams"],
  "consistently_strong_topics": ["topics strong in 2+ exams"],
  "improving_topics":  ["topics weak early but stronger recently"],
  "declining_topics":  ["topics strong early but weaker recently"],
  "recurring_mistakes": ["top 3-5 recurring error patterns from mistake context"],
  "overall_summary": "<2-3 sentence narrative of the student's academic trajectory>",
  "key_insights": [
    "<specific, evidence-based insight 1>",
    "<specific, evidence-based insight 2>",
    "<specific, evidence-based insight 3>"
  ],
  "recommendations": [
    "<actionable recommendation 1>",
    "<actionable recommendation 2>",
    "<actionable recommendation 3>"
  ]
}}

Readiness Score guidance:
  100  = mastery, ready for exam now
  70+  = good, minor revision needed
  50+  = moderate, focused practice required
  <50  = needs significant remedial work
Consider: average score, trend direction, number of weak topics, recurring mistakes.

Rules:
  - consistently_weak_topics: appear as weak in 2+ exams
  - consistently_strong_topics: appear as strong in 2+ exams
  - If only 1 exam exists, score_trend must be "insufficient_data"
  - numerical_accuracy: average of question_type_scores.numerical entries
  - theory_accuracy: average across theory + derivation + definition entries
  - Return ONLY valid JSON.
"""


class InsightsAgent:
    """Generates holistic performance insights from exam history + mistake context."""

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def generate(
        self,
        reports: list[dict[str, Any]],
        mistake_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not reports:
            return self._empty_insights()

        exam_summaries = self._format_exam_summaries(reports)
        mistake_str = json.dumps(mistake_context, indent=2) if mistake_context else "No mistake context available yet."

        prompt = INSIGHTS_PROMPT.format(
            num_exams=len(reports),
            exam_summaries=exam_summaries,
            mistake_context=mistake_str,
        )

        response = self.model.generate_content(prompt)
        return self._parse_response(response.text)

    def _format_exam_summaries(self, reports: list[dict[str, Any]]) -> str:
        lines = []
        for i, r in enumerate(reports, 1):
            lines.append(f"Exam {i} (Date: {r.get('date', 'unknown')}):")
            lines.append(f"  Overall Score: {r.get('overall_score', 'N/A')}%")
            lines.append(f"  Topic Scores: {json.dumps(r.get('topic_scores') or {})}")
            lines.append(f"  Weak Topics: {', '.join(r.get('weak_topics') or ['None'])}")
            lines.append(f"  Strong Topics: {', '.join(r.get('strong_topics') or ['None'])}")
            lines.append(f"  Summary: {r.get('summary', '')}")
            lines.append("")
        return "\n".join(lines)

    def _parse_response(self, raw: str) -> dict[str, Any]:
        cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return self._empty_insights()

    def _empty_insights(self) -> dict[str, Any]:
        return {
            "average_score": None,
            "score_trend": "insufficient_data",
            "strongest_area": None,
            "weakest_area": None,
            "numerical_accuracy": None,
            "theory_accuracy": None,
            "readiness_score": None,
            "consistently_weak_topics": [],
            "consistently_strong_topics": [],
            "improving_topics": [],
            "declining_topics": [],
            "recurring_mistakes": [],
            "overall_summary": "Not enough data to generate insights yet. Complete more evaluations to see your performance trends.",
            "key_insights": [],
            "recommendations": ["Complete at least one exam evaluation to get personalised insights."],
        }


insights_agent = InsightsAgent()
