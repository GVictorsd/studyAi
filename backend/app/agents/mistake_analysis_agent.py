"""
Mistake Analysis Agent — detects and tracks error patterns over time.

Rebuilt with Google ADK as an LlmAgent.

Runs after every exam evaluation. It reads the rubric-level answer feedback
from the new report, merges it with the student's accumulated mistake context,
and produces an updated context that downstream agents (Insights, StudyPlan)
use to give targeted, pattern-aware advice.

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

from google.adk.agents import LlmAgent

from app.agents.adk_runner import run_agent_task

_MODEL = "gemini-2.5-flash-lite-preview-06-17"

# ─────────────────────────────────────────────────────────────────────────────
# ADK agent definition
# ─────────────────────────────────────────────────────────────────────────────

_INSTRUCTION = """You are an expert academic tutor building a long-term mistake profile for a student.

You will receive a new exam evaluation report and the student's existing accumulated
mistake context. Your job is to:
  1. Analyse the new exam data to identify error patterns.
  2. Merge them with the existing context to produce an updated cumulative profile.

Return a JSON object with this exact shape (no markdown fences, no surrounding text):

{
  "total_exams_analyzed": <int>,
  "recurring_issues": [
    {
      "pattern": "<descriptive name, e.g. 'Skips derivation steps'>",
      "frequency": <int — how many exams this pattern appeared in>,
      "affected_topics": ["topic1", "topic2"],
      "example": "<one concrete example from the student's answers>"
    }
  ],
  "topic_weakness_frequency": { "<topic>": <int count of exams where weak>, ... },
  "error_type_counts": {
    "skips_derivation_steps": <int>,
    "calculation_errors": <int>,
    "incomplete_definitions": <int>,
    "conceptual_gaps": <int>,
    "poor_answer_structure": <int>,
    "missing_units": <int>,
    "sign_errors": <int>
  },
  "question_type_scores": {
    "numerical":  [<float scores 0-100 across all analysed exams>],
    "theory":     [<float scores>],
    "derivation": [<float scores>],
    "definition": [<float scores>]
  }
}

Rules:
- Merge counts from existing context with counts from the new exam.
- recurring_issues: include any pattern seen in 2+ exams AND notable single-exam patterns.
- question_type_scores: append the new exam's per-type averages to existing lists.
- Be specific in pattern names and examples.
- Return ONLY valid JSON."""


mistake_analysis_adk_agent = LlmAgent(
    name="mistake_analysis_agent",
    model=_MODEL,
    description=(
        "Analyses student exam errors, detects recurring patterns, and "
        "maintains a cumulative mistake profile across all exams."
    ),
    instruction=_INSTRUCTION,
)


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def update_context(
    new_report: dict[str, Any],
    existing_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Run the ADK mistake analysis agent to merge a new exam report into the
    student's cumulative mistake profile.

    Args:
        new_report:       The evaluation dict from EvaluationAgent.
        existing_context: The student's current mistake context, or None for
                          first-exam analysis.

    Returns:
        Updated cumulative mistake context dict.
    """
    new_exam_str = _format_new_exam(new_report)
    existing_count = (existing_context or {}).get("total_exams_analyzed", 0)
    existing_str = (
        json.dumps(existing_context, indent=2)
        if existing_context
        else "None — this is the first exam."
    )

    message = f"""Analyse the following new exam data and update the student's cumulative mistake profile.

━━━ NEW EXAM DATA ━━━
{new_exam_str}

━━━ EXISTING ACCUMULATED CONTEXT ({existing_count} previous exam(s)) ━━━
{existing_str}

Produce the updated cumulative mistake profile JSON as specified in your instructions."""

    raw = await run_agent_task(mistake_analysis_adk_agent, message)
    result = _parse_response(raw)

    if not result.get("total_exams_analyzed"):
        result["total_exams_analyzed"] = existing_count + 1

    return result


def _parse_response(raw: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return _empty_context()


def _empty_context() -> dict[str, Any]:
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
