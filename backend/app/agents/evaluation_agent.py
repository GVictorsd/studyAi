"""
Evaluation Agent — the core examiner intelligence, rebuilt with Google ADK.

Architecture
────────────
``evaluation_adk_agent`` is an ADK LlmAgent that:
  • Performs rubric-based, multi-dimensional scoring (correctness,
    completeness, conceptual accuracy, writing quality).
  • Has ``textbook_knowledge_adk_agent`` mounted as an AgentTool so it can
    autonomously call the textbook retrieval sub-agent whenever it needs to
    ground a correct_answer or verify a student's claim.
  • Returns a single structured JSON object — no markdown fences.

Rubric dimensions (applied to every question)
  Correctness         0-10  — factual / mathematical accuracy
  Completeness        0-10  — all required steps, sub-points, derivations
  Conceptual Accuracy 0-10  — genuine understanding vs rote recall
  Writing Quality     0-10  — clarity, structure, appropriate depth

Question types: numerical | theory | derivation | definition

The public ``evaluate()`` coroutine is the only entry-point used by the
orchestrator; it formats the prompt, drives the runner, and parses JSON.
"""
import json
import re
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from app.agents.adk_runner import run_agent_task
from app.agents.textbook_knowledge_agent import (
    KnowledgeResult,
    textbook_knowledge_adk_agent,
)

_MODEL = "gemini-2.5-flash-lite-preview-06-17"

_SECTION_SEP = "\n\n" + "=" * 60 + "\n\n"

# ─────────────────────────────────────────────────────────────────────────────
# ADK agent definition
# ─────────────────────────────────────────────────────────────────────────────

_INSTRUCTION = """You are a rigorous academic examiner performing detailed rubric-based evaluation.

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

━━━ TOOL USE ━━━
You have access to a textbook_knowledge_agent sub-agent.
When you need to verify a correct answer or ground your feedback in textbook
material, call the textbook_knowledge_agent with a message like:
  "Retrieve context for query: <topic or question> from collection: <collection_name>"

Only call the sub-agent for questions where textbook grounding would
meaningfully improve your correct_answer or feedback quality.

━━━ OUTPUT FORMAT ━━━
After reasoning through each answer, return a single JSON object.
No markdown fences, no prose outside the JSON.

{
  "overall_score": <float 0-100, average of all question scores × 100>,
  "topic_scores": { "<TopicName>": <float 0-100>, ... },
  "weak_topics":   ["topics whose average score is below 60%"],
  "strong_topics": ["topics whose average score is above 80%"],
  "summary": "<2-3 sentence executive summary of overall performance>",
  "answer_feedback": [
    {
      "question": "<exact question text>",
      "student_answer": "<what the student wrote>",
      "correct_answer": "<concise model answer, drawing on textbook reference if retrieved>",
      "topic": "<academic topic / chapter name>",
      "question_type": "numerical" | "theory" | "derivation" | "definition",
      "score": <float 0.0-1.0 using the formula above>,
      "feedback": "<specific, constructive 1-2 sentence feedback>",
      "rubric": {
        "correctness":         { "score": <int 0-10>, "comment": "<concise reason>" },
        "completeness":        { "score": <int 0-10>, "comment": "<concise reason>" },
        "conceptual_accuracy": { "score": <int 0-10>, "comment": "<concise reason>" },
        "writing_quality":     { "score": <int 0-10>, "comment": "<concise reason>" }
      },
      "missing_steps": ["<specific missing step or concept — be precise>"]
    }
  ]
}

Rules:
- missing_steps must be an empty list [] if the answer is fully complete.
- Comments must be specific to THIS answer, not generic.
- overall_score is 0-100 (not 0-1).
- topic_scores values are 0-100.
- Return ONLY the JSON object — no surrounding text."""


evaluation_adk_agent = LlmAgent(
    name="evaluation_agent",
    model=_MODEL,
    description=(
        "Rubric-based academic exam evaluator. Scores student answers "
        "across four dimensions and produces structured JSON feedback. "
        "Can consult the textbook knowledge sub-agent for grounding."
    ),
    instruction=_INSTRUCTION,
    tools=[AgentTool(agent=textbook_knowledge_adk_agent)],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: format knowledge context for the prompt
# ─────────────────────────────────────────────────────────────────────────────

def _format_knowledge_context(knowledge_results: list[KnowledgeResult] | None) -> str:
    if not knowledge_results:
        return "No textbook material pre-loaded. Use the textbook_knowledge_agent tool if needed."

    parts = []
    for i, result in enumerate(knowledge_results, 1):
        label = result.query[:100].replace("\n", " ")
        block = f"[Pre-fetched Reference for Question {i}: {label}]\n{result.formatted_context()}"
        parts.append(block)

    return _SECTION_SEP.join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def evaluate(
    exam_text: str,
    answer_text: str,
    knowledge_results: list[KnowledgeResult] | None = None,
    textbook_collection_name: str | None = None,
) -> dict[str, Any]:
    """
    Run the ADK evaluation agent against one exam + answer sheet.

    Pre-fetched ``knowledge_results`` are injected directly into the prompt.
    The agent may also call ``textbook_knowledge_adk_agent`` autonomously via
    AgentTool for any question it wants additional grounding on.

    Args:
        exam_text:                The full exam paper text.
        answer_text:              The student's answer sheet text.
        knowledge_results:        Optional per-question RAG results pre-fetched
                                  by the orchestrator.
        textbook_collection_name: Collection name hint so the agent can call
                                  the textbook sub-agent autonomously.

    Returns:
        Parsed evaluation dict with overall_score, topic_scores, weak_topics,
        strong_topics, summary, and answer_feedback list.
    """
    pre_fetched_context = _format_knowledge_context(knowledge_results)

    collection_hint = (
        f"\nTextbook collection available for autonomous retrieval: {textbook_collection_name}"
        if textbook_collection_name
        else "\nNo textbook collection linked to this exam."
    )

    message = f"""Please evaluate the following exam submission.

━━━ EXAM PAPER ━━━
{exam_text}

━━━ STUDENT ANSWERS ━━━
{answer_text}

━━━ PRE-FETCHED TEXTBOOK REFERENCE MATERIAL (per question) ━━━
{pre_fetched_context}
{collection_hint}

Evaluate every question using the rubric in your instructions and return
the structured JSON result."""

    raw = await run_agent_task(evaluation_adk_agent, message)
    return _parse_response(raw)


def _parse_response(raw: str) -> dict[str, Any]:
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
