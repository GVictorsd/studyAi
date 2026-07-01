"""
Mistake Analysis Agent — detects and tracks error patterns over time.

Runs in the background after every exam evaluation.  It reads the rubric-level
answer feedback from the new report, merges it with the student's accumulated
mistake context, and produces an updated context that downstream agents (Insights,
StudyPlan) use to give targeted, pattern-aware advice.

Tracked patterns include:
  • Skipping derivation steps
  • Calculation / sign errors
  • Incomplete definitions
  • Conceptual gaps
  • Poor answer structure in long questions
  • Missing units
  • Weak performance in specific question types (numerical vs theory etc.)
"""
import json
import re
from typing import Any

import google.generativeai as genai

from app.core.config import settings


genai.configure(api_key=settings.GOOGLE_API_KEY)


MISTAKE_ANALYSIS_PROMPT = """
You are an expert academic tutor building a long-term mistake profile for a student.

━━━ NEW EXAM DATA ━━━
{new_exam_data}

━━━ EXISTING ACCUMULATED CONTEXT ({existing_exam_count} previous exams) ━━━
{existing_context}

Analyse the new exam data, identify error patterns, and merge them with the
existing context to produce an updated cumulative mistake profile.

Return a JSON object with this exact shape (no markdown fences):
{{
  "total_exams_analyzed": <int>,
  "recurring_issues": [
    {{
      "pattern": "<descriptive name, e.g. 'Skips derivation steps'>",
      "frequency": <int — how many exams this pattern appeared in>,
      "affected_topics": ["topic1", "topic2"],
      "example": "<one concrete example from the student's answers>"
    }}
  ],
  "topic_weakness_frequency": {{ "<topic>": <int count of exams where weak>, ... }},
  "error_type_counts": {{
    "skips_derivation_steps": <int>,
    "calculation_errors": <int>,
    "incomplete_definitions": <int>,
    "conceptual_gaps": <int>,
    "poor_answer_structure": <int>,
    "missing_units": <int>,
    "sign_errors": <int>
  }},
  "question_type_scores": {{
    "numerical":  [<float scores 0-100 across all analysed exams>],
    "theory":     [<float scores>],
    "derivation": [<float scores>],
    "definition": [<float scores>]
  }}
}}

Rules:
- Merge counts from existing context with counts from the new exam.
- recurring_issues: include any pattern seen in 2+ exams AND notable single-exam patterns from this exam.
- question_type_scores: append the new exam's per-type averages to existing lists.
- Be specific in pattern names and examples.
- Return ONLY valid JSON.
"""


def _extract_question_type_scores(answer_feedback: list[dict]) -> dict[str, float | None]:
    """Compute average score (0-100) per question_type from an exam's feedback list."""
    buckets: dict[str, list[float]] = {}
    for fb in answer_feedback:
        qt = fb.get("question_type") or "theory"
        score = fb.get("score", 0)
        buckets.setdefault(qt, []).append(score * 100)
    return {qt: round(sum(v) / len(v), 1) for qt, v in buckets.items()}


def _format_new_exam(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"Overall Score: {report.get('overall_score', 'N/A')}%")
    lines.append(f"Weak Topics: {', '.join(report.get('weak_topics') or ['None'])}")

    for i, fb in enumerate(report.get("answer_feedback") or [], 1):
        lines.append(f"\nQ{i}: {fb.get('question', '')[:120]}")
        lines.append(f"  Type: {fb.get('question_type', 'unknown')}")
        lines.append(f"  Score: {fb.get('score', 0):.2f}")
        rubric = fb.get("rubric") or {}
        for metric, data in rubric.items():
            s = data.get("score", "?") if isinstance(data, dict) else "?"
            c = data.get("comment", "") if isinstance(data, dict) else ""
            lines.append(f"  {metric.replace('_', ' ').title()}: {s}/10 — {c}")
        missing = fb.get("missing_steps") or []
        if missing:
            lines.append(f"  Missing Steps: {'; '.join(missing)}")

    return "\n".join(lines)


class MistakeAnalysisAgent:
    """Updates the student's cumulative mistake context after every exam."""

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def update_context(
        self,
        new_report: dict[str, Any],
        existing_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        new_exam_str = _format_new_exam(new_report)
        existing_count = (existing_context or {}).get("total_exams_analyzed", 0)
        existing_str = json.dumps(existing_context, indent=2) if existing_context else "None — this is the first exam."

        prompt = MISTAKE_ANALYSIS_PROMPT.format(
            new_exam_data=new_exam_str,
            existing_exam_count=existing_count,
            existing_context=existing_str,
        )

        response = self.model.generate_content(prompt)
        result = self._parse_response(response.text)

        if not result.get("total_exams_analyzed"):
            result["total_exams_analyzed"] = existing_count + 1

        return result

    def _parse_response(self, raw: str) -> dict[str, Any]:
        cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return self._empty_context()

    def _empty_context(self) -> dict[str, Any]:
        return {
            "total_exams_analyzed": 1,
            "recurring_issues": [],
            "topic_weakness_frequency": {},
            "error_type_counts": {
                "skips_derivation_steps": 0,
                "calculation_errors": 0,
                "incomplete_definitions": 0,
                "conceptual_gaps": 0,
                "poor_answer_structure": 0,
                "missing_units": 0,
                "sign_errors": 0,
            },
            "question_type_scores": {
                "numerical": [],
                "theory": [],
                "derivation": [],
                "definition": [],
            },
        }


mistake_analysis_agent = MistakeAnalysisAgent()
