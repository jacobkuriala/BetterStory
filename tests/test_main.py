"""Tests for story_forge.main."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
import anthropic

from story_forge.main import run, _print_scores_table, _save_output, _get_user_inputs


# --- _print_scores_table ---

class TestPrintScoresTable:
    def test_prints_all_dimensions(self, capsys):
        scores = {"prose": 7, "pacing": 8, "depth": 6}
        _print_scores_table(scores, 7.0)

        output = capsys.readouterr().out
        assert "prose" in output
        assert "pacing" in output
        assert "depth" in output
        assert "7.0" in output

    def test_formats_average(self, capsys):
        _print_scores_table({"dim": 5}, 5.0)
        output = capsys.readouterr().out
        assert "Average" in output
        assert "5.0" in output


# --- _save_output ---

class TestSaveOutput:
    def test_creates_file_with_content(self, tmp_path):
        brief = "Write a mystery"
        story = "It was a dark and stormy night."
        history = [
            {
                "iteration": 1,
                "story": story,
                "scores": {"prose": 7},
                "average": 7.0,
                "satisfied": False,
                "feedback": "Needs work.",
            }
        ]

        filepath = _save_output(brief, story, history, output_dir=tmp_path)
        path = Path(filepath)

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Write a mystery" in content
        assert "dark and stormy night" in content
        assert "Iteration 1" in content
        assert "Needs work." in content

    def test_file_naming(self, tmp_path):
        filepath = _save_output("brief", "story", [], output_dir=tmp_path)
        path = Path(filepath)
        assert path.name.startswith("story_")
        assert path.suffix == ".md"


# --- _get_user_inputs ---

class TestGetUserInputs:
    def test_collects_brief_and_steering(self, monkeypatch):
        inputs = iter(["A horror story", "set in space", "", "y"])
        monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

        brief, steerable = _get_user_inputs()

        assert "horror story" in brief
        assert "set in space" in brief
        assert steerable is True

    def test_steering_disabled(self, monkeypatch):
        inputs = iter(["A romance", "", "n"])
        monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

        brief, steerable = _get_user_inputs()

        assert "romance" in brief
        assert steerable is False

    def test_empty_brief_exits(self, monkeypatch):
        inputs = iter([""])
        monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

        with pytest.raises(SystemExit):
            _get_user_inputs()


# --- run (integration-style with mocked API) ---

def _mock_response(text: str) -> MagicMock:
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


class TestRun:
    @pytest.fixture
    def mock_client(self):
        return MagicMock(spec=anthropic.Anthropic)

    @pytest.fixture
    def rubric(self):
        return [
            {"name": "prose", "description": "Prose quality."},
            {"name": "pacing", "description": "Story pacing."},
        ]

    @pytest.fixture
    def passing_review(self):
        return {
            "scores": {"prose": 9, "pacing": 9},
            "average": 9.0,
            "satisfied": True,
            "feedback": "Excellent work.",
        }

    @pytest.fixture
    def failing_review(self):
        return {
            "scores": {"prose": 6, "pacing": 5},
            "average": 5.5,
            "satisfied": False,
            "feedback": "Needs more tension in act two.",
        }

    def test_exits_on_first_pass(self, mock_client, rubric, passing_review, capsys, tmp_path):
        mock_client.messages.create.side_effect = [
            _mock_response(json.dumps(rubric)),         # rubric generation
            _mock_response("A great story."),            # first draft
            _mock_response(json.dumps(passing_review)),  # review passes
        ]

        run(client=mock_client, brief="Write something", steerable=False, output_dir=tmp_path)

        output = capsys.readouterr().out
        assert "Iteration 1/15" in output
        assert "Quality threshold reached" in output
        assert "A great story." in output

    def test_loops_on_failing_review(self, mock_client, rubric, failing_review, passing_review, capsys, tmp_path):
        mock_client.messages.create.side_effect = [
            _mock_response(json.dumps(rubric)),           # rubric
            _mock_response("Draft 1"),                     # first draft
            _mock_response(json.dumps(failing_review)),    # fail
            _mock_response("Draft 2"),                     # revision
            _mock_response(json.dumps(passing_review)),    # pass
        ]

        run(client=mock_client, brief="Write something", steerable=False, output_dir=tmp_path)

        output = capsys.readouterr().out
        assert "Iteration 1/15" in output
        assert "Iteration 2/15" in output
        assert "Quality threshold reached at iteration 2" in output

    def test_steering_appends_input(self, mock_client, rubric, failing_review, passing_review, monkeypatch, tmp_path):
        mock_client.messages.create.side_effect = [
            _mock_response(json.dumps(rubric)),
            _mock_response("Draft 1"),
            _mock_response(json.dumps(failing_review)),
            _mock_response("Draft 2"),
            _mock_response(json.dumps(passing_review)),
        ]

        monkeypatch.setattr("builtins.input", lambda *a, **kw: "Make it darker")

        run(client=mock_client, brief="A story", steerable=True, output_dir=tmp_path)

        # The second Creator call should have the steering input
        creator_calls = [
            c for c in mock_client.messages.create.call_args_list
            if "revised" in str(c).lower() or "Write a story" in str(c) or "feedback" in str(c).lower()
        ]
        # Check the revision call includes the steering text
        all_call_args = str(mock_client.messages.create.call_args_list)
        assert "Make it darker" in all_call_args

    def test_saves_output_file(self, mock_client, rubric, passing_review, tmp_path):
        mock_client.messages.create.side_effect = [
            _mock_response(json.dumps(rubric)),
            _mock_response("Final story."),
            _mock_response(json.dumps(passing_review)),
        ]

        run(client=mock_client, brief="Test brief", steerable=False, output_dir=tmp_path)

        md_files = list(tmp_path.glob("story_*.md"))
        assert len(md_files) == 1

    def test_max_iterations_respected(self, mock_client, rubric, failing_review, capsys, tmp_path):
        responses = [_mock_response(json.dumps(rubric))]
        for _ in range(15):
            responses.append(_mock_response("Draft"))
            responses.append(_mock_response(json.dumps(failing_review)))

        mock_client.messages.create.side_effect = responses

        run(client=mock_client, brief="A story", steerable=False, output_dir=tmp_path)

        output = capsys.readouterr().out
        assert "Maximum iterations (15) reached" in output
