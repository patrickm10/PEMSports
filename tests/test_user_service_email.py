"""Email normalization for case-insensitive auth."""

from backend.services.user_service import _normalize_email


def test_normalize_email_lowercases_and_trims():
    assert _normalize_email("  User@Example.COM  ") == "user@example.com"
