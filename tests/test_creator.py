"""Tests for story_forge.agents.creator."""

import json
from unittest.mock import MagicMock, patch

import pytest
import anthropic

from story_forge.agents.creator import generate_rubric, create_story


def _mock_response(text: str) -> MagicMock:
    """Create a mock Anthropic response."""
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


@pytest.fixture
def mock_client():
    return MagicMock(spec=anthropic.Anthropic)


# --- generate_rubric ---

class TestGenerateRubric:
    def test_returns_parsed_rubric(self, mock_client):
        rubric_data = [
            {"name": "prose_quality", "description": "Quality of the prose."},
            {"name": "character_depth", "description": "Depth of characters."},
        ]
        mock_client.messages.create.return_value = _mock_response(json.dumps(rubric_data))

        result = generate_rubric(mock_client, "Write a mystery story.")

        assert result == rubric_data
        mock_client.messages.create.assert_called_once()

    def test_retries_on_invalid_json_then_succeeds(self, mock_client):
        rubric_data = [{"name": "tone", "description": "Consistent tone."}]
        mock_client.messages.create.side_effect = [
            _mock_response("Not valid JSON"),
            _mock_response(json.dumps(rubric_data)),
        ]

        result = generate_rubric(mock_client, "Write a poem.")

        assert result == rubric_data
        assert mock_client.messages.create.call_count == 2

    def test_raises_on_persistent_invalid_json(self, mock_client):
        mock_client.messages.create.return_value = _mock_response("Still not JSON")

        with pytest.raises(json.JSONDecodeError):
            generate_rubric(mock_client, "Write a story.")

    def test_retries_on_api_error_then_succeeds(self, mock_client):
        rubric_data = [{"name": "pacing", "description": "Story pacing."}]
        mock_client.messages.create.side_effect = [
            anthropic.APIError(
                message="Server error",
                request=MagicMock(),
                body=None,
            ),
            _mock_response(json.dumps(rubric_data)),
        ]

        result = generate_rubric(mock_client, "Write a thriller.")

        assert result == rubric_data

    def test_raises_on_persistent_api_error(self, mock_client):
        error = anthropic.APIError(
            message="Server error",
            request=MagicMock(),
            body=None,
        )
        mock_client.messages.create.side_effect = [error, error]

        with pytest.raises(anthropic.APIError):
            generate_rubric(mock_client, "Write a story.")


# --- create_story ---

class TestCreateStory:
    def test_first_draft_no_feedback(self, mock_client):
        mock_client.messages.create.return_value = _mock_response("Once upon a time...")

        result = create_story(mock_client, "A fairy tale")

        assert result == "Once upon a time..."
        call_args = mock_client.messages.create.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "fairy tale" in user_msg.lower()
        assert "feedback" not in user_msg.lower()

    def test_revision_with_feedback(self, mock_client):
        mock_client.messages.create.return_value = _mock_response("Revised story...")

        result = create_story(mock_client, "A fairy tale", feedback="Needs more conflict.")

        assert result == "Revised story..."
        call_args = mock_client.messages.create.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "Needs more conflict" in user_msg
        assert "fairy tale" in user_msg.lower()

    def test_retries_on_api_error(self, mock_client):
        mock_client.messages.create.side_effect = [
            anthropic.APIError(
                message="Timeout",
                request=MagicMock(),
                body=None,
            ),
            _mock_response("Story after retry"),
        ]

        result = create_story(mock_client, "A sci-fi story")

        assert result == "Story after retry"
