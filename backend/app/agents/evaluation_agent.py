"""
Answer Evaluation Agent — the core examiner intelligence.

Runs on every question-answer pair with rubric-based, multi-dimensional scoring:
  • Correctness         (0-10): factual / mathematical accuracy
  • Completeness        (0-10): all required parts, steps, sub-points present
  • Conceptual Accuracy (0-10): genuine understanding of underlying theory
  • Writing Quality     (0-10): structure, clarity, appropriate depth

Also tags question_type (numerical / theory / derivation / definition) and
extracts missing_steps so the MistakeAnalysisAgent can detect patterns.

Chain-of-thought reasoning is performed internally by the model before it
produces the structured JSON, via the reasoning instruction in the prompt.
"""
import json
import re
from typing import Any

import google.generativeai as genai

from app.agents.textbook_knowledge_agent import KnowledgeResult
from app.core.config import settings


genai.configure(api_key=settings.GOOGLE_API_KEY)

_SECTION_SEP = "\n\n" + "=" * 60 + "\n\n"

EVALUATION_PROMPT = """
You are a rigorous academic examiner performing a detailed rubric-based evaluation.
Before producing the JSON, reason through each answer carefully step-by-step,
then emit the final structured result.

━━━ RUBRIC (apply to EVERY question) ━━━
• Correctness         0-10  — Is the answer factually / mathematically correct?
• Completeness        0-10  — Are all required steps, sub-points, and derivations present?
• Conceptual Accuracy 0-10  — Does the student show genuine understanding (not just recall)?
• Writing Quality     0-10  — Is the answer clear, well-structured, with appropriate detail?

━━━ QUESTION TYPE CLASSIFICATION ━━━
Classify each question as exactly one of:
  "numerical"  — requires calculation / formula application
  "theory"     — requires explanation of concepts / laws / phenomena
  "derivation" — requires step-by-step mathematical derivation
  "definition" — requires a precise definition or statement of a law/theorem

━━━ SCORING FORMULA ━━━
score (0-1) = (correctness×0.40 + completeness×0.20 + conceptual_accuracy×0.30 + writing_quality×0.10) / 10

━━━ OUTPUT FORMAT ━━━
Return a single JSON object. No markdown fences, no prose outside the JSON.

{{
  "overall_score": <float 0-100, average of all question scores × 100>,
  "topic_scores": {{ "<TopicName>": <float 0-100>, ... }},
  "weak_topics":   ["topics whose average score is below 60%"],
  "strong_topics": ["topics whose average score is above 80%"],
  "summary": "<2-3 sentence executive summary of overall performance>",
  "answer_feedback": [
    {{
      "question": "<exact question text>",
      "student_answer": "<what the student wrote>",
      "correct_answer": "<concise model answer, drawing on textbook reference>",
      "topic": "<academic topic / chapter name>",
      "question_type": "numerical" | "theory" | "derivation" | "definition",
      "score": <float 0.0-1.0 using the formula above>,
      "feedback": "<specific, constructive 1-2 sentence feedback>",
      "rubric": {{
        "correctness":         {{ "score": <int 0-10>, "comment": "<concise reason>" }},
        "completeness":        {{ "score": <int 0-10>, "comment": "<concise reason>" }},
        "conceptual_accuracy": {{ "score": <int 0-10>, "comment": "<concise reason>" }},
        "writing_quality":     {{ "score": <int 0-10>, "comment": "<concise reason>" }}
      }},
      "missing_steps": ["<specific missing step or concept — be precise>"]
    }}
  ]
}}

Rules:
- missing_steps must be an empty list [] if the answer is fully complete.
- Comments must be specific to THIS answer, not generic.
- overall_score is 0-100 (not 0-1).
- topic_scores values are 0-100.

━━━ INPUT ━━━

EXAM PAPER:
{exam_text}

STUDENT ANSWERS:
{answer_text}

TEXTBOOK REFERENCE MATERIAL (per question):
{context}
"""


class EvaluationAgent:
    """Rubric-based evaluation agent using Gemini with chain-of-thought scoring."""

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def evaluate(
        self,
        exam_text: str,
        answer_text: str,
        knowledge_results: list[KnowledgeResult] | None = None,
    ) -> dict[str, Any]:
        context = self._format_knowledge_context(knowledge_results)
        prompt = EVALUATION_PROMPT.format(
            exam_text=exam_text,
            answer_text=answer_text,
            context=context,
        )
        response = self.model.generate_content(prompt)
        return self._parse_response(response.text)

    def _format_knowledge_context(
        self, knowledge_results: list[KnowledgeResult] | None
    ) -> str:
        if not knowledge_results:
            return "No textbook material provided."

        parts = []
        for i, result in enumerate(knowledge_results, 1):
            label = result.query[:100].replace("\n", " ")
            block = f"[Reference for Question {i}: {label}]\n{result.formatted_context()}"
            parts.append(block)

        return _SECTION_SEP.join(parts)

    def _parse_response(self, raw: str) -> dict[str, Any]:
        cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "overall_score": 0,
                "topic_scores": {},
                "weak_topics": [],
                "strong_topics": [],
                "answer_feedback": [],
                "summary": "Evaluation could not be parsed. Please retry.",
            }


evaluation_agent = EvaluationAgent()
