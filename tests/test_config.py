"""Tests for story_forge.config."""

from story_forge.config import (
    MAX_ITERATIONS,
    SCORE_THRESHOLD,
    CREATOR_MODEL,
    REVIEWER_MODEL,
    API_RETRY_LIMIT,
)


def test_max_iterations_is_positive_integer():
    assert isinstance(MAX_ITERATIONS, int)
    assert MAX_ITERATIONS > 0


def test_score_threshold_is_positive_float():
    assert isinstance(SCORE_THRESHOLD, (int, float))
    assert 0 < SCORE_THRESHOLD <= 10


def test_models_are_nonempty_strings():
    assert isinstance(CREATOR_MODEL, str) and CREATOR_MODEL
    assert isinstance(REVIEWER_MODEL, str) and REVIEWER_MODEL


def test_retry_limit_is_non_negative():
    assert isinstance(API_RETRY_LIMIT, int)
    assert API_RETRY_LIMIT >= 0
