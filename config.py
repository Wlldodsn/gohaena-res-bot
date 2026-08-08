import sys
from datetime import date, time
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

if not (Path(__file__).parent / "config.env").exists():
    sys.exit(
        "config.env not found. Copy config.env.example to config.env and fill in "
        "your details before running."
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="config.env", env_file_encoding="utf-8")

    target_date: date
    time_slot: str
    party_size: int
    visitor_first_name: str
    visitor_last_name: str
    visitor_email: str
    visitor_phone: str

    release_timezone: str = "Pacific/Honolulu"
    release_days_before: int = 30
    release_time: time = time(0, 0, 0)
    prewarm_minutes_before: int = 10
    max_retry_attempts: int = 5
    retry_window_seconds: int = 60

    dry_run: bool = False
    headless: bool = False


settings = Settings()
