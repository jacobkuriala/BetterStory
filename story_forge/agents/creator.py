"""Creator agent — generates rubrics and writes/revises stories."""

import json
import os
from pathlib import Path

import anthropic

from story_forge.config import CREATOR_MODEL, API_RETRY_LIMIT
from story_forge.agents.json_utils import extract_json

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "creator.md"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _call_api(client: anthropic.Anthropic, system: str, user_message: str) -> str:
    """Make an API call with one retry on failure."""
    last_error = None
    for attempt in range(1 + API_RETRY_LIMIT):
        try:
            response = client.messages.create(
                model=CREATOR_MODEL,
                max_tokens=16384,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except anthropic.APIError as e:
            last_error = e
            if attempt < API_RETRY_LIMIT:
                print(f"  [Creator API error: {e}. Retrying...]")
    raise last_error


def generate_rubric(client: anthropic.Anthropic, brief: str) -> list[dict]:
    """Ask the Creator to produce a scoring rubric based on the brief.

    Returns a list of dicts like [{"name": "...", "description": "..."}, ...].
    """
    system = (
        "You are an expert creative-writing evaluator. "
        "Given a story brief, produce a scoring rubric as a JSON array. "
        "Each element must have a 'name' (snake_case, short) and a 'description' "
        "(one sentence explaining what this dimension measures). "
        "Include 4–6 dimensions that are specifically relevant to this brief. "
        "Return ONLY the JSON array — no markdown fencing, no commentary."
    )
    user_message = f"Story brief:\n\n{brief}"

    text = _call_api(client, system, user_message)

    # Try to parse; retry once if malformed
    try:
        rubric = extract_json(text)
    except json.JSONDecodeError:
        print("  [Rubric JSON parse failed. Asking Creator to retry...]")
        user_message += (
            "\n\nYour previous response was not valid JSON. "
            "Please return ONLY a JSON array."
        )
        text = _call_api(client, system, user_message)
        rubric = extract_json(text)

    return rubric


def create_story(
    client: anthropic.Anthropic,
    brief: str,
    feedback: str | None = None,
) -> str:
    """Write or revise a story.

    On the first call, feedback is None and the Creator writes from the brief.
    On subsequent calls, feedback contains the Reviewer's narrative critique.
    """
    system = _load_system_prompt()

    if feedback is None:
        user_message = f"Write a story based on this brief:\n\n{brief}"
    else:
        user_message = (
            f"Original brief:\n\n{brief}\n\n"
            f"---\n\n"
            f"Editorial feedback on your previous draft:\n\n{feedback}\n\n"
            f"---\n\n"
            f"Please write a revised story that seriously addresses this feedback."
        )

    return _call_api(client, system, user_message)
