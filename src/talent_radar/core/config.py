from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    backend_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///data/talent_radar.sqlite3"
    source_registry_path: Path = Path("config/source_registry.example.yaml")
    query_pack_path: Path = Path("config/query_pack_vsf.yaml")

    crawl_lookback_hours: int = 24
    crawl_max_posts_per_source: int = 200
    crawl_comment_mode: str = "risk_based"
    crawl_max_comments_per_post: int = 100

    ai_provider: str = "rule"
    ai_model: str = "gemini-2.5-flash"
    ai_max_items_per_run: int = 300
    ai_min_filter_score: float = 0.35
    ai_daily_budget_usd: float = 0.25
    google_ai_api_key: str | None = None
    openai_api_key: str | None = None

    report_output_formats: str = "markdown,csv"

    facebook_graph_api_version: str = "v20.0"
    facebook_app_id: str | None = None
    facebook_app_secret: str | None = None
    facebook_page_access_token: str | None = None

    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None
    tiktok_access_token: str | None = None

    threads_access_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
