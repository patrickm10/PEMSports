import json
import os
from typing import Optional, Dict
from src.backend.data.interfaces import BaseInsightRepository

class LocalInsightRepository(BaseInsightRepository):
    """
    A file-backed repository implementation for local portability.
    Stores insights as JSON in data_local/ to ensure git-ignored storage.
    """
    def __init__(self, file_path: str = "data_local/insights.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def _load(self) -> Dict:
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    async def get_insight(self, player_id: str, week: int, year: int) -> Optional[str]:
        data = self._load()
        key = f"{player_id}_{year}_{week}"
        return data.get(key)

    async def save_insight(self, player_id: str, week: int, year: int, text: str) -> None:
        data = self._load()
        key = f"{player_id}_{year}_{week}"
        data[key] = text
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)
