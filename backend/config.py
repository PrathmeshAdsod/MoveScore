"""
MoveScore — Backend Configuration
Reads all settings from environment variables.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Google Cloud
    google_cloud_project_id: str = ""
    gcs_temp_bucket: str = "movescore-temp"
    gcp_region: str = "us-central1"
    service_account_email: str = ""
    agent_engine_resource_name: str = ""
    local_dev_mode: bool = False

    # Gemini
    gemini_api_key: str = ""
    gemini_secret_resource: str = ""
    gemini_secret_id: str = ""
    gemini_secret_version: str = "1"
    gemini_model: str = "gemini-3.8-flash"

    # Lyria
    lyria_model: str = "lyria-3.5"

    # App
    port: int = 8080
    frontend_url: str = "http://localhost:3000"
    max_video_size_mb: int = 100
    signed_url_ttl_hours: int = 1
    cloud_run_timeout_seconds: int = 600

    @property
    def max_video_size_bytes(self) -> int:
        return self.max_video_size_mb * 1024 * 1024


settings = Settings()
