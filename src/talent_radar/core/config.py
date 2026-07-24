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
    collection_timezone: str = "Asia/Ho_Chi_Minh"
    crawl_output_directory: Path = Path("data/exports")
    coccoc_window_handle: int | None = None
    coccoc_executable_path: Path = Path(
        r"C:\Program Files\CocCoc\Browser\Application\browser.exe"
    )
    coccoc_user_data_directory: Path = (
        Path.home() / "AppData/Local/CocCoc/Browser/User Data"
    )
    coccoc_control_user_data_directory: Path = Path("data/coccoc_huy_user_data")
    coccoc_profile_directory: str = "Default"
    coccoc_profile_account_name: str = "Vũ Văn Huy"
    coccoc_remote_debugging_port: int = 9223
    browser_headless: bool = False

    auth_session_hours: int = 168
    background_worker_enabled: bool = True
    background_poll_seconds: int = 15

    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_redirect_uri: str = (
        "http://localhost:8000/connections/facebook/callback"
    )
    facebook_graph_api_version: str = "v20.0"
    facebook_scopes: str = "public_profile"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
