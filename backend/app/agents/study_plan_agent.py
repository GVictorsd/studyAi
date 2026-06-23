"""
Study Plan Agent — generates a personalised weekly study plan
based on the evaluation report's weak topics.
"""
import json
import re
from typing import Any
import google.generativeai as genai
from app.core.config import settings


genai.configure(api_key=settings.GOOGLE_API_KEY)


STUDY_PLAN_PROMPT = """
You are an expert academic coach. Based on the evaluation report below, create a
detailed, personalised study plan to help the student improve.

Evaluation Summary:
- Overall Score: {overall_score}%
- Weak Topics: {weak_topics}
- Strong Topics: {strong_topics}
- Detailed Summary: {summary}

Return a structured JSON study plan with this shape:
{{
  "duration_weeks": <int>,
  "weekly_goals": [
    {{
      "week": 1,
      "focus_topics": ["topic1", "topic2"],
      "daily_tasks": [
        {{
          "day": "Monday",
          "tasks": ["Read chapter X on topic1", "Solve 10 practice questions on topic1"]
        }}
      ],
      "milestone": "Describe expected progress by end of week"
    }}
  ],
  "resources": [
    {{
      "topic": "topic name",
      "suggestions": ["resource 1", "resource 2"]
    }}
  ],
  "tips": ["motivational / study tip 1", "tip 2"]
}}

Return ONLY valid JSON, no markdown fences.
"""


class StudyPlanAgent:
    """ADK-style agent that generates a personalised study plan."""

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def generate(self, report: dict[str, Any]) -> dict[str, Any]:
        prompt = STUDY_PLAN_PROMPT.format(
            overall_score=report.get("overall_score", 0),
            weak_topics=", ".join(report.get("weak_topics") or ["None"]),
            strong_topics=", ".join(report.get("strong_topics") or ["None"]),
            summary=report.get("summary", ""),
        )

        response = self.model.generate_content(prompt)
        return self._parse_response(response.text)

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
