"""
Ensure password hashing works with pinned bcrypt (passlib 1.7.4 breaks on bcrypt 4.1+).
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.core.auth import get_password_hash, verify_password


def test_password_hash_and_verify_roundtrip():
    hashed = get_password_hash("password123")
    assert hashed.startswith("$2")
    assert verify_password("password123", hashed)
    assert not verify_password("wrong-password", hashed)
