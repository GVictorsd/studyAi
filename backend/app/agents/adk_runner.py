"""
Shared ADK runner utility.

Provides a single helper — ``run_agent_task`` — that:
  1. Creates a throw-away InMemoryRunner + one-shot session for an LlmAgent.
  2. Streams all events until the agent is done.
  3. Collects and returns the concatenated final-response text.

Every agent in this package calls this helper instead of managing runners
themselves, keeping the runner life-cycle in one place.
"""
import uuid
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google import genai as google_genai
from google.genai import types

from app.core.config import settings

_APP_NAME = "studyai"

# Configure the google-genai client once for the whole process.
# ADK 2.x picks this up automatically from the environment / genai client.
_genai_client = google_genai.Client(api_key=settings.GOOGLE_API_KEY)


async def run_agent_task(agent: LlmAgent, message: str, user_id: str = "system") -> str:
    """
    Run *agent* with a single-turn *message* and return the final response text.

    Creates a fresh InMemoryRunner and session per call so that every
    invocation is fully isolated (no bleed-through between evaluations).

    Args:
        agent:   The ADK LlmAgent to invoke.
        message: The full user-turn text to send.
        user_id: Logical user identifier (default "system" for background tasks).

    Returns:
        The agent's final text reply (all parts concatenated).
    """
    runner = InMemoryRunner(agent=agent, app_name=_APP_NAME)

    session = runner.session_service.create_session(
        app_name=_APP_NAME,
        user_id=user_id,
        session_id=str(uuid.uuid4()),
    )

    user_content = types.Content(
        role="user",
        parts=[types.Part(text=message)],
    )

    final_text_parts: list[str] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text_parts.append(part.text)

    return "".join(final_text_parts)
