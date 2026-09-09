"""
Service layer for user interactions via the PostgreSQL connection pool.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from backend.core.auth import get_password_hash, hash_refresh_token
from backend.core.config import config
from backend.data.postgres import get_db_connection, is_db_connected


def _normalize_email(email: str) -> str:
    """Canonicalize email for lookups and storage (case-insensitive auth)."""
    return email.strip().lower()


def _row_user(row) -> Dict[str, Any]:
    return {
        "id": str(row[0]),
        "email": row[1],
        "password_hash": row[2],
        "created_at": row[3],
        "plan": row[4] if len(row) > 4 and row[4] else "free",
    }


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user details and hashed password by email."""
    if not is_db_connected():
        return None

    email_norm = _normalize_email(email)
    sql = (
        "SELECT id, email, password_hash, created_at, plan "
        "FROM users WHERE LOWER(email) = %s"
    )

    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (email_norm,))
            row = await cur.fetchone()

    if not row:
        return None
    return _row_user(row)


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    if not is_db_connected():
        return None

    sql = (
        "SELECT id, email, password_hash, created_at, plan "
        "FROM users WHERE id = %s"
    )
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
            row = await cur.fetchone()
    if not row:
        return None
    return _row_user(row)


async def create_user(
    email: str, plaintext_password: str, *, plan: str = "free"
) -> Optional[Dict[str, Any]]:
    """Create a new user by securely hashing their password prior to storage."""
    if not is_db_connected():
        return None

    email_norm = _normalize_email(email)
    hashed_pwd = get_password_hash(plaintext_password)

    sql = """
        INSERT INTO users (email, password_hash, plan)
        VALUES (%s, %s, %s)
        RETURNING id, email, created_at, plan
    """

    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (email_norm, hashed_pwd, plan))
            row = await cur.fetchone()
        await conn.commit()

    if not row:
        return None
    return {
        "id": str(row[0]),
        "email": row[1],
        "created_at": row[2],
        "plan": row[3] if len(row) > 3 and row[3] else plan,
    }


async def user_has_feature(user_id: str, feature: str) -> bool:
    if not is_db_connected():
        return False
    sql = "SELECT 1 FROM entitlements WHERE user_id = %s AND feature = %s"
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, feature))
            row = await cur.fetchone()
    return row is not None


async def store_refresh_token(user_id: str, raw_token: str) -> None:
    if not is_db_connected():
        return
    token_hash = hash_refresh_token(raw_token)
    expires = datetime.now(timezone.utc) + timedelta(days=config.refresh_token_expire_days)
    sql = """
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
        VALUES (%s, %s, %s)
    """
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, token_hash, expires))
        await conn.commit()


async def rotate_refresh_token(raw_token: str) -> Optional[Dict[str, Any]]:
    """Validate refresh token, revoke it, return user. Detects reuse."""
    if not is_db_connected():
        return None
    token_hash = hash_refresh_token(raw_token)
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, expires_at, revoked_at
                FROM refresh_tokens WHERE token_hash = %s
                """,
                (token_hash,),
            )
            row = await cur.fetchone()
            if not row:
                return None
            token_id, user_id, expires_at, revoked_at = row
            if revoked_at is not None:
                await cur.execute(
                    "UPDATE refresh_tokens SET revoked_at = NOW() "
                    "WHERE user_id = %s AND revoked_at IS NULL",
                    (user_id,),
                )
                await conn.commit()
                return None
            if expires_at is not None and expires_at < datetime.now(timezone.utc):
                await cur.execute(
                    "UPDATE refresh_tokens SET revoked_at = NOW() WHERE id = %s",
                    (token_id,),
                )
                await conn.commit()
                return None
            await cur.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW() WHERE id = %s",
                (token_id,),
            )
        await conn.commit()
    user = await get_user_by_id(str(user_id))
    return user


async def revoke_refresh_token(raw_token: str) -> None:
    if not is_db_connected() or not raw_token:
        return
    token_hash = hash_refresh_token(raw_token)
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW() "
                "WHERE token_hash = %s AND revoked_at IS NULL",
                (token_hash,),
            )
        await conn.commit()


async def get_stats_generation() -> int:
    if not is_db_connected():
        from backend.data.ranking_store import local_generation

        return local_generation()
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT generation FROM stats_generation WHERE id = 1")
            row = await cur.fetchone()
    return int(row[0]) if row else 0
