"""
Evaluation Agent — uses Google ADK to assess student answers against
textbook content retrieved via ChromaDB RAG.
"""
import json
import re
from typing import Any
import google.generativeai as genai
from app.core.config import settings
from app.services.vector_store import vector_store


genai.configure(api_key=settings.GOOGLE_API_KEY)


EVALUATION_PROMPT = """
You are an expert academic evaluator. You will receive:
1. An exam paper with questions
2. A student's answers
3. Relevant reference material from the textbook

Your task is to evaluate EACH answer and return a structured JSON response.

For each question provide:
- question: the exam question
- student_answer: what the student wrote
- correct_answer: a concise correct answer based on textbook material
- score: a float between 0.0 and 1.0 (1.0 = fully correct)
- feedback: specific, constructive feedback
- topic: the academic topic this question tests

Also provide:
- overall_score: weighted average (0–100)
- topic_scores: {{ "TopicName": score_percent, ... }}
- weak_topics: list of topics scoring below 60%
- strong_topics: list of topics scoring 80%+
- summary: 2–3 sentence executive summary

Return ONLY valid JSON, no markdown fences.

---
EXAM PAPER:
{exam_text}

STUDENT ANSWERS:
{answer_text}

REFERENCE MATERIAL FROM TEXTBOOK:
{context}
"""


class EvaluationAgent:
    """ADK-style agent that evaluates student exam answers using Gemini."""

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def evaluate(
        self,
        exam_text: str,
        answer_text: str,
        textbook_collection: str | None,
    ) -> dict[str, Any]:
        context = self._retrieve_context(exam_text, textbook_collection)
        prompt = EVALUATION_PROMPT.format(
            exam_text=exam_text,
            answer_text=answer_text,
            context=context or "No textbook material provided.",
        )

        response = self.model.generate_content(prompt)
        return self._parse_response(response.text)

    def _retrieve_context(self, query: str, collection_name: str | None) -> str:
        if not collection_name:
            return ""
        chunks = vector_store.query_textbook(collection_name, query, n_results=6)
        return "\n\n---\n\n".join(chunks)

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
