# from __future__ import annotations removed
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, Field




# Decoupled models to prevent Pydantic validation crashes


class BaseRankingRecord(BaseModel):
    year: int
    player_id: str
    player_name: str
    team: str
    position: str
    fpts: float
    fpts_ppr: float
    fpts_per_game: float
    fpts_ppr_per_game: float
    rank: Optional[int] = None
    
    # Analytical Metrics
    targets: Optional[float] = None
    rec: Optional[float] = None
    yds: Optional[float] = None
    td: Optional[float] = None
    
    model_config = {"extra": "allow"}

class SeasonalRankingRecord(BaseRankingRecord):
    """Canonical response shape for a season-level player ranking."""
    games_played: Optional[int] = None

class WeeklyRankingRecord(BaseRankingRecord):
    """Canonical response shape for a weekly-level player ranking with enrichment."""
    week: int
    opponent: Optional[str] = None
    stadium_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    indoor_outdoor: Optional[str] = None
    surface_type: Optional[str] = None
    elevation: Optional[float] = None
    game_result: Optional[str] = None
    temp: Optional[float] = None
    humidity: Optional[float] = None
    wind: Optional[float] = None


class PaginationParams(BaseModel):
    limit: int = Field(default=200, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class HealthResponse(BaseModel):
    status: str
    data_files_found: int
    positions_available: List[str]




# model_rebuild() calls removed to prevent Pydantic ForwardRef issues
