"""Tests for story_forge.agents.json_utils."""

import json

import pytest

from story_forge.agents.json_utils import extract_json


class TestExtractJson:
    def test_plain_json_object(self):
        result = extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_plain_json_array(self):
        result = extract_json('[{"name": "test"}]')
        assert result == [{"name": "test"}]

    def test_json_with_markdown_fencing(self):
        text = '```json\n{"scores": {"prose": 7}, "average": 7.0, "satisfied": false, "feedback": "ok"}\n```'
        result = extract_json(text)
        assert result["scores"]["prose"] == 7

    def test_json_with_bare_fencing(self):
        text = '```\n[{"name": "dim1"}]\n```'
        result = extract_json(text)
        assert result == [{"name": "dim1"}]

    def test_json_with_surrounding_text(self):
        text = 'Here is my review:\n\n{"scores": {"a": 5}, "average": 5.0, "satisfied": false, "feedback": "needs work"}'
        result = extract_json(text)
        assert result["average"] == 5.0

    def test_json_with_leading_whitespace(self):
        result = extract_json('  \n  {"key": 1}  \n  ')
        assert result == {"key": 1}

    def test_json_array_with_fencing_and_extra_text(self):
        text = 'Sure, here is the rubric:\n```json\n[{"name": "tone", "description": "Tone quality"}]\n```\nLet me know if you need changes.'
        result = extract_json(text)
        assert result[0]["name"] == "tone"

    def test_raises_on_no_json(self):
        with pytest.raises(json.JSONDecodeError):
            extract_json("This has no JSON at all.")

    def test_raises_on_empty_string(self):
        with pytest.raises(json.JSONDecodeError):
            extract_json("")

    def test_nested_json_object(self):
        text = '```json\n{"scores": {"a": 8, "b": 9}, "average": 8.5, "satisfied": true, "feedback": "great"}\n```'
        result = extract_json(text)
        assert result["satisfied"] is True
        assert result["scores"]["a"] == 8
