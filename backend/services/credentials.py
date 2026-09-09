"""Resolve provider credentials without persisting or logging secret values."""

from __future__ import annotations

from functools import lru_cache

from google.cloud import secretmanager

from config import settings


@lru_cache(maxsize=1)
def get_gemini_api_key() -> str:
    """Return the configured key or fetch an exact Secret Manager resource via ADC."""
    if settings.gemini_api_key:
        return settings.gemini_api_key.strip()

    secret_resource = settings.gemini_secret_resource.strip()
    if not secret_resource and settings.gemini_secret_id:
        if not settings.google_cloud_project_id:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT_ID is required when GEMINI_SECRET_ID is set"
            )
        secret_resource = (
            f"projects/{settings.google_cloud_project_id}/secrets/"
            f"{settings.gemini_secret_id}/versions/{settings.gemini_secret_version}"
        )

    if not secret_resource:
        raise RuntimeError(
            "Gemini credentials are not configured: set GEMINI_API_KEY, "
            "GEMINI_SECRET_RESOURCE, or GEMINI_SECRET_ID"
        )

    response = secretmanager.SecretManagerServiceClient().access_secret_version(
        request={"name": secret_resource}
    )
    api_key = response.payload.data.decode("utf-8").strip()
    if not api_key:
        raise RuntimeError("The configured Gemini secret version is empty")
    return api_key
