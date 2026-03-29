"""Reviewer agent — scores stories and provides feedback."""

import json
from pathlib import Path

import anthropic

from story_forge.config import REVIEWER_MODEL, API_RETRY_LIMIT
from story_forge.agents.json_utils import extract_json

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "reviewer.md"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _call_api(client: anthropic.Anthropic, system: str, user_message: str) -> str:
    """Make an API call with one retry on failure."""
    last_error = None
    for attempt in range(1 + API_RETRY_LIMIT):
        try:
            response = client.messages.create(
                model=REVIEWER_MODEL,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except anthropic.APIError as e:
            last_error = e
            if attempt < API_RETRY_LIMIT:
                print(f"  [Reviewer API error: {e}. Retrying...]")
    raise last_error


def _format_rubric(rubric: list[dict]) -> str:
    """Format the rubric as readable text for the Reviewer prompt."""
    lines = []
    for dim in rubric:
        lines.append(f"- **{dim['name']}**: {dim['description']}")
    return "\n".join(lines)


def review_story(
    client: anthropic.Anthropic,
    brief: str,
    rubric: list[dict],
    story: str,
) -> dict:
    """Review a story and return scores + feedback.

    Returns a dict with keys: scores, average, satisfied, feedback.
    """
    system = _load_system_prompt()

    rubric_text = _format_rubric(rubric)
    dimension_names = [dim["name"] for dim in rubric]

    user_message = (
        f"## Original Brief\n\n{brief}\n\n"
        f"## Scoring Rubric\n\n{rubric_text}\n\n"
        f"## Story to Review\n\n{story}\n\n"
        f"---\n\n"
        f"Score this story on each rubric dimension (1–10). "
        f"The dimension names are: {', '.join(dimension_names)}. "
        f"Return your response as the specified JSON object."
    )

    text = _call_api(client, system, user_message)

    # Try to parse; retry once if malformed
    try:
        result = extract_json(text)
    except json.JSONDecodeError:
        print("  [Reviewer JSON parse failed. Asking Reviewer to retry...]")
        retry_message = (
            user_message
            + "\n\nYour previous response was not valid JSON. "
            "Please return ONLY the JSON object as specified."
        )
        text = _call_api(client, system, retry_message)
        result = extract_json(text)

    _validate_review(result, dimension_names)
    return result


def _validate_review(result: dict, dimension_names: list[str]) -> None:
    """Ensure the review has the expected structure."""
    if not isinstance(result.get("scores"), dict):
        raise ValueError("Review missing 'scores' dict")
    if not isinstance(result.get("average"), (int, float)):
        raise ValueError("Review missing numeric 'average'")
    if not isinstance(result.get("satisfied"), bool):
        raise ValueError("Review missing boolean 'satisfied'")
    if not isinstance(result.get("feedback"), str):
        raise ValueError("Review missing string 'feedback'")
