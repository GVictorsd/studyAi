"""
Study Planner Agent — generates a personalised, adaptive improvement plan.

Reads accumulated mistake context (from MistakeAnalysisAgent) and the
evaluation report to produce a structured weekly plan that directly targets
the student's recurring error patterns with spaced-repetition scheduling,
daily goals, and targeted practice exercises.
"""
import json
import re
from typing import Any

import google.generativeai as genai

from app.agents.textbook_knowledge_agent import KnowledgeResult
from app.core.config import settings


genai.configure(api_key=settings.GOOGLE_API_KEY)


STUDY_PLAN_PROMPT = """
You are an expert academic coach creating a personalised study plan.

━━━ EVALUATION REPORT ━━━
Overall Score: {overall_score}%
Weak Topics:   {weak_topics}
Strong Topics: {strong_topics}
Summary: {summary}

━━━ ACCUMULATED MISTAKE PATTERNS ━━━
{mistake_context}

━━━ TEXTBOOK REFERENCES FOR WEAK TOPICS ━━━
{textbook_references}

Create a detailed, adaptive study plan that:
1. Directly addresses the recurring mistake patterns listed above
2. Uses spaced repetition for topics the student consistently struggles with
3. Includes targeted practice for the specific error types (derivation, calculation, definitions)
4. Balances remedial work with maintaining existing strengths

Return a JSON object with this exact shape (no markdown fences):
{{
  "duration_weeks": <int>,
  "weekly_goals": [
    {{
      "week": 1,
      "focus_topics": ["topic1", "topic2"],
      "daily_tasks": [
        {{
          "day": "Monday",
          "tasks": [
            "Read Chapter X — focus on derivation of [formula]",
            "Solve 10 numerical problems on [topic]",
            "Write out 5 definitions in full, check against textbook"
          ]
        }}
      ],
      "milestone": "<measurable goal by end of week>"
    }}
  ],
  "resources": [
    {{
      "topic": "<topic name>",
      "chapter_reference": "<chapter/section if known, else null>",
      "suggestions": ["Practice resource 1", "Practice resource 2"]
    }}
  ],
  "tips": [
    "<targeted tip addressing a specific recurring mistake>",
    "<motivational / general study tip>"
  ]
}}

Rules:
- If there are recurring derivation-step errors, include at least one daily task per week that explicitly practices step-by-step derivations.
- If calculation errors are frequent, include timed numerical drills.
- Vary the week themes: early weeks = remediation, later weeks = consolidation + mock practice.
- Return ONLY valid JSON.
"""


class StudyPlanAgent:
    """Generates a personalised, mistake-aware weekly study plan."""

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def generate(
        self,
        report: dict[str, Any],
        textbook_references: dict[str, KnowledgeResult] | None = None,
        mistake_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ref_section = self._format_references(
            textbook_references,
            report.get("weak_topics") or [],
        )
        mistake_str = self._format_mistake_context(mistake_context)

        prompt = STUDY_PLAN_PROMPT.format(
            overall_score=report.get("overall_score", 0),
            weak_topics=", ".join(report.get("weak_topics") or ["None"]),
            strong_topics=", ".join(report.get("strong_topics") or ["None"]),
            summary=report.get("summary", ""),
            mistake_context=mistake_str,
            textbook_references=ref_section,
        )

        response = self.model.generate_content(prompt)
        return self._parse_response(response.text)

    def _format_mistake_context(self, ctx: dict[str, Any] | None) -> str:
        if not ctx:
            return "No accumulated mistake context available yet."

        lines = [f"Exams Analysed: {ctx.get('total_exams_analyzed', 1)}"]

        error_counts = ctx.get("error_type_counts") or {}
        if any(v > 0 for v in error_counts.values()):
            lines.append("Error Type Counts:")
            for k, v in error_counts.items():
                if v > 0:
                    lines.append(f"  {k.replace('_', ' ').title()}: {v}")

        issues = ctx.get("recurring_issues") or []
        if issues:
            lines.append("Recurring Issues:")
            for issue in issues[:5]:
                lines.append(f"  • {issue.get('pattern', '')} (seen {issue.get('frequency', 1)}x) — {issue.get('example', '')}")

        qt_scores = ctx.get("question_type_scores") or {}
        for qt, scores in qt_scores.items():
            if scores:
                avg = round(sum(scores) / len(scores), 1)
                lines.append(f"Avg {qt.title()} Score: {avg}%")

        return "\n".join(lines)

    def _format_references(
        self,
        references: dict[str, KnowledgeResult] | None,
        weak_topics: list[str],
    ) -> str:
        if not references or not weak_topics:
            return "No textbook references available."

        lines = []
        for topic in weak_topics:
            result = references.get(topic)
            if result and result.chunks:
                chunk = result.chunks[0]
                if chunk.chapter or chunk.section:
                    loc = f"{chunk.chapter} \u203a {chunk.section}"
                    lines.append(f"- {topic}: See '{loc}'")
                else:
                    lines.append(f"- {topic}: Textbook material available")
            else:
                lines.append(f"- {topic}: No specific textbook reference found")

        return "\n".join(lines)

    def _parse_response(self, raw: str) -> dict[str, Any]:
        cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "duration_weeks": 4,
                "weekly_goals": [],
                "resources": [],
                "tips": ["Study consistently and review weak topics daily."],
            }


study_plan_agent = StudyPlanAgent()
