"""Focused coverage for session-token lifecycle behavior."""

from secrets import token_urlsafe

from src.api.routes import _hash_token


def test_session_token_hash_is_deterministic_and_not_plaintext():
    token = "a-session-token-for-test-only"
    assert _hash_token(token) == _hash_token(token)
    assert _hash_token(token) != token
    assert len(_hash_token(token)) == 64


def test_generated_session_tokens_are_high_entropy_and_unique():
    first = token_urlsafe(32)
    second = token_urlsafe(32)
    assert first != second
    assert len(first) >= 40
