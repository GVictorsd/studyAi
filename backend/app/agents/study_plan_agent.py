"""
Study Planner Agent — generates a personalised, adaptive improvement plan.

Rebuilt with Google ADK as an LlmAgent.

Has ``textbook_knowledge_adk_agent`` mounted as an AgentTool so it can
autonomously retrieve chapter references for weak topics without the
orchestrator having to pre-fetch and format them.

Reads accumulated mistake context (from MistakeAnalysisAgent) and the
evaluation report to produce a structured weekly plan that directly targets
the student's recurring error patterns with spaced-repetition scheduling,
daily goals, and targeted practice exercises.
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

# ─────────────────────────────────────────────────────────────────────────────
# ADK agent definition
# ─────────────────────────────────────────────────────────────────────────────

_INSTRUCTION = """You are an expert academic coach creating a personalised, adaptive study plan.

━━━ TOOL USE ━━━
You have access to the textbook_knowledge_agent sub-agent.
For each weak topic, you SHOULD call the sub-agent to retrieve relevant
textbook chapters so your plan can reference specific sections.

To call the sub-agent, send a message like:
  "Retrieve context for query: <weak topic name> from collection: <collection_name>"

If no collection_name is provided in the input, skip tool calls and work
from the general knowledge you have.

━━━ PLAN REQUIREMENTS ━━━
Create a detailed study plan that:
1. Directly addresses the recurring mistake patterns listed.
2. Uses spaced repetition for topics the student consistently struggles with.
3. Includes targeted practice for specific error types (derivation, calculation, definitions).
4. Balances remedial work with maintaining existing strengths.
5. Cites textbook chapters/sections you retrieved where possible.

━━━ OUTPUT FORMAT ━━━
Return a JSON object with this exact shape (no markdown fences, no surrounding text):

{
  "duration_weeks": <int>,
  "weekly_goals": [
    {
      "week": 1,
      "focus_topics": ["topic1", "topic2"],
      "daily_tasks": [
        {
          "day": "Monday",
          "tasks": [
            "Read Chapter X — focus on derivation of [formula]",
            "Solve 10 numerical problems on [topic]",
            "Write out 5 definitions in full, check against textbook"
          ]
        }
      ],
      "milestone": "<measurable goal by end of week>"
    }
  ],
  "resources": [
    {
      "topic": "<topic name>",
      "chapter_reference": "<chapter/section if retrieved, else null>",
      "suggestions": ["Practice resource 1", "Practice resource 2"]
    }
  ],
  "tips": [
    "<targeted tip addressing a specific recurring mistake>",
    "<motivational / general study tip>"
  ]
}

Rules:
- If there are recurring derivation-step errors, include at least one daily task per week
  that explicitly practices step-by-step derivations.
- If calculation errors are frequent, include timed numerical drills.
- Vary week themes: early weeks = remediation, later weeks = consolidation + mock practice.
- Return ONLY valid JSON."""


study_plan_adk_agent = LlmAgent(
    name="study_plan_agent",
    model=_MODEL,
    description=(
        "Generates a personalised, mistake-aware weekly study plan. "
        "Can autonomously retrieve textbook chapter references for weak topics "
        "via the textbook knowledge sub-agent."
    ),
    instruction=_INSTRUCTION,
    tools=[AgentTool(agent=textbook_knowledge_adk_agent)],
)


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _format_mistake_context(ctx: dict[str, Any] | None) -> str:
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
            lines.append(
                f"  • {issue.get('pattern', '')} "
                f"(seen {issue.get('frequency', 1)}x) — {issue.get('example', '')}"
            )

    qt_scores = ctx.get("question_type_scores") or {}
    for qt, scores in qt_scores.items():
        if scores:
            avg = round(sum(scores) / len(scores), 1)
            lines.append(f"Avg {qt.title()} Score: {avg}%")

    return "\n".join(lines)


def _format_pre_fetched_refs(
    references: dict[str, KnowledgeResult] | None,
    weak_topics: list[str],
) -> str:
    """Format any pre-fetched textbook references passed in by the orchestrator."""
    if not references or not weak_topics:
        return "None pre-fetched — agent will retrieve autonomously via tool."

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


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def generate(
    report: dict[str, Any],
    textbook_references: dict[str, KnowledgeResult] | None = None,
    mistake_context: dict[str, Any] | None = None,
    textbook_collection_name: str | None = None,
) -> dict[str, Any]:
    """
    Run the ADK study plan agent to generate a personalised study plan.

    The agent will:
    - Use pre-fetched ``textbook_references`` if provided.
    - Additionally call the textbook_knowledge_adk_agent autonomously via
      AgentTool to retrieve chapter references for any weak topic that does
      not already have a pre-fetched reference.

    Args:
        report:                   The evaluation dict from EvaluationAgent.
        textbook_references:      Optional pre-fetched per-topic RAG results.
        mistake_context:          The student's cumulative mistake context.
        textbook_collection_name: Collection name so the agent can call the
                                  textbook sub-agent autonomously.

    Returns:
        Parsed study plan dict.
    """
    weak_topics = report.get("weak_topics") or []
    strong_topics = report.get("strong_topics") or []
    mistake_str = _format_mistake_context(mistake_context)
    pre_fetched_str = _format_pre_fetched_refs(textbook_references, weak_topics)

    collection_hint = (
        f"\nTextbook collection available for autonomous retrieval: {textbook_collection_name}"
        if textbook_collection_name
        else "\nNo textbook collection linked — skip tool calls."
    )

    message = f"""Generate a personalised study plan for the student described below.

━━━ EVALUATION REPORT ━━━
Overall Score:  {report.get('overall_score', 0)}%
Weak Topics:    {', '.join(weak_topics) or 'None'}
Strong Topics:  {', '.join(strong_topics) or 'None'}
Summary: {report.get('summary', '')}

━━━ ACCUMULATED MISTAKE PATTERNS ━━━
{mistake_str}

━━━ PRE-FETCHED TEXTBOOK REFERENCES FOR WEAK TOPICS ━━━
{pre_fetched_str}
{collection_hint}

For any weak topic without a pre-fetched reference above, use the
textbook_knowledge_agent tool to retrieve relevant chapter material, then
incorporate those chapter references into the plan.

Return the study plan JSON as described in your instructions."""

    raw = await run_agent_task(study_plan_adk_agent, message)
    return _parse_response(raw)


def _parse_response(raw: str) -> dict[str, Any]:
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
