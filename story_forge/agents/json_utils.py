"""Utilities for extracting JSON from LLM responses."""

import json
import re


def extract_json(text: str):
    """Parse JSON from text, stripping markdown code fences if present.

    Handles responses wrapped in ```json ... ``` or ``` ... ```.
    Returns the parsed Python object (dict or list).
    Raises json.JSONDecodeError if no valid JSON can be extracted.
    """
    # First, try parsing the raw text directly
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Try to extract from markdown code fences
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, stripped, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())

    # Try to find a JSON object or array in the text
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = stripped.find(start_char)
        if start == -1:
            continue
        end = stripped.rfind(end_char)
        if end == -1 or end <= start:
            continue
        candidate = stripped[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("No valid JSON found in response", text, 0)
