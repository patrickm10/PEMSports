from abc import ABC, abstractmethod
from typing import List, Optional

class BaseInsightRepository(ABC):
    """
    Abstract base class for the player performance insights repository.
    Provides a portable interface for CRUD operations on situational player data.
    """
    @abstractmethod
    async def get_insight(self, player_id: str, week: int, year: int) -> Optional[str]:
        """Retrieve a specific user-saved insight for a player in a given week/year."""
        pass

    @abstractmethod
    async def save_insight(self, player_id: str, week: int, year: int, text: str) -> None:
        """Save or update a user insight for a specific player situational performance."""
        pass
