from datetime import datetime
from pydantic_settings import BaseSettings, SettingsConfigDict

import os
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Value Betting API"
    DATABASE_URL: str
    ODDS_API_KEY: str
    API_SPORTS_KEY: str
    SECRET_KEY: str = "supersecret_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200 # 30 days for convenience

    model_config = SettingsConfigDict(
        env_file=os.path.join(Path(__file__).parent.parent, ".env")
    )

settings = Settings()


def get_current_season() -> int:
    """
    Calculate the current European football season year.
    European football seasons span two calendar years (e.g., 2025/2026).
    The season is identified by the starting year:
      - If the current month is August (8) or later → season = current year
      - If the current month is before August       → season = current year - 1
    
    Example: In March 2026, the active season is 2025/2026 → returns 2025.
             In September 2026, the new season is 2026/2027 → returns 2026.
    """
    now = datetime.now()
    if now.month < 8:
        return now.year - 1
    return now.year
