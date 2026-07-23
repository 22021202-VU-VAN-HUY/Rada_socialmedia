from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    backend_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///data/talent_radar.sqlite3"
    source_registry_path: Path = Path("config/source_registry.example.yaml")

    crawl_lookback_hours: int = 24
    crawl_max_posts_per_source: int = 200
    crawl_max_comments_per_post: int = 100
    crawl_output_directory: Path = Path("data/exports")
    coccoc_window_handle: int | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
