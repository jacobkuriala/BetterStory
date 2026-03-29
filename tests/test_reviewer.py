"""Tests for story_forge.agents.reviewer."""

import json
from unittest.mock import MagicMock

import pytest
import anthropic

from story_forge.agents.reviewer import review_story, _validate_review, _format_rubric


def _mock_response(text: str) -> MagicMock:
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


@pytest.fixture
def mock_client():
    return MagicMock(spec=anthropic.Anthropic)


@pytest.fixture
def sample_rubric():
    return [
        {"name": "prose_quality", "description": "Quality of prose."},
        {"name": "character_depth", "description": "Depth of characters."},
        {"name": "pacing", "description": "Story pacing."},
    ]


@pytest.fixture
def valid_review():
    return {
        "scores": {"prose_quality": 7, "character_depth": 6, "pacing": 8},
        "average": 7.0,
        "satisfied": False,
        "feedback": "Good pacing but characters need more development.",
    }


# --- _format_rubric ---

class TestFormatRubric:
    def test_formats_all_dimensions(self, sample_rubric):
        result = _format_rubric(sample_rubric)
        assert "prose_quality" in result
        assert "character_depth" in result
        assert "pacing" in result

    def test_includes_descriptions(self, sample_rubric):
        result = _format_rubric(sample_rubric)
        assert "Quality of prose." in result


# --- _validate_review ---

class TestValidateReview:
    def test_valid_review_passes(self, valid_review):
        _validate_review(valid_review, ["prose_quality", "character_depth", "pacing"])

    def test_missing_scores_raises(self):
        with pytest.raises(ValueError, match="scores"):
            _validate_review(
                {"average": 5.0, "satisfied": False, "feedback": "ok"},
                ["dim1"],
            )

    def test_missing_average_raises(self, valid_review):
        del valid_review["average"]
        with pytest.raises(ValueError, match="average"):
            _validate_review(valid_review, ["prose_quality"])

    def test_missing_satisfied_raises(self, valid_review):
        del valid_review["satisfied"]
        with pytest.raises(ValueError, match="satisfied"):
            _validate_review(valid_review, ["prose_quality"])

    def test_missing_feedback_raises(self, valid_review):
        del valid_review["feedback"]
        with pytest.raises(ValueError, match="feedback"):
            _validate_review(valid_review, ["prose_quality"])

    def test_wrong_type_scores_raises(self):
        with pytest.raises(ValueError, match="scores"):
            _validate_review(
                {"scores": "not a dict", "average": 5.0, "satisfied": False, "feedback": "ok"},
                ["dim1"],
            )


# --- review_story ---

class TestReviewStory:
    def test_returns_valid_review(self, mock_client, sample_rubric, valid_review):
        mock_client.messages.create.return_value = _mock_response(json.dumps(valid_review))

        result = review_story(mock_client, "A mystery", sample_rubric, "The story text...")

        assert result["average"] == 7.0
        assert result["satisfied"] is False
        assert "prose_quality" in result["scores"]

    def test_retries_on_invalid_json_then_succeeds(self, mock_client, sample_rubric, valid_review):
        mock_client.messages.create.side_effect = [
            _mock_response("Not JSON"),
            _mock_response(json.dumps(valid_review)),
        ]

        result = review_story(mock_client, "A mystery", sample_rubric, "Story...")

        assert result["average"] == 7.0
        assert mock_client.messages.create.call_count == 2

    def test_raises_on_persistent_invalid_json(self, mock_client, sample_rubric):
        mock_client.messages.create.return_value = _mock_response("Bad JSON")

        with pytest.raises(json.JSONDecodeError):
            review_story(mock_client, "A mystery", sample_rubric, "Story...")

    def test_retries_on_api_error(self, mock_client, sample_rubric, valid_review):
        mock_client.messages.create.side_effect = [
            anthropic.APIError(
                message="Error",
                request=MagicMock(),
                body=None,
            ),
            _mock_response(json.dumps(valid_review)),
        ]

        result = review_story(mock_client, "Brief", sample_rubric, "Story...")

        assert result["satisfied"] is False

    def test_raises_on_invalid_structure(self, mock_client, sample_rubric):
        bad_review = {"scores": {}, "average": 5.0, "satisfied": "not bool", "feedback": "ok"}
        mock_client.messages.create.return_value = _mock_response(json.dumps(bad_review))

        with pytest.raises(ValueError, match="satisfied"):
            review_story(mock_client, "Brief", sample_rubric, "Story...")
