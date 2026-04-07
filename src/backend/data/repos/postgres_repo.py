from __future__ import annotations
from typing import Optional
from src.backend.data.interfaces import BaseInsightRepository
from src.backend.data.postgres import get_db_connection

class PostgresInsightRepository(BaseInsightRepository):
    """
    PostgreSQL-backed implementation of player performance insights.
    Optimized for production environments with high concurrency.
    """
    async def get_insight(self, player_id: str, week: int, year: int) -> Optional[str]:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT insight_text FROM player_insights 
                    WHERE player_id = %s AND week = %s AND year = %s
                    """,
                    (player_id, week, year)
                )
                res = await cur.fetchone()
                return res[0] if res else None

    async def save_insight(self, player_id: str, week: int, year: int, text: str) -> None:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO player_insights (player_id, week, year, insight_text) 
                    VALUES (%s, %s, %s, %s) 
                    ON CONFLICT (player_id, week, year) 
                    DO UPDATE SET insight_text = EXCLUDED.insight_text
                    """,
                    (player_id, week, year, text)
                )
            await conn.commit()
