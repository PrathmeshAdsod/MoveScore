"""
GCS Storage Service

Handles all Google Cloud Storage operations:
- upload files (from bytes or local path)
- generate signed URLs for temporary access
- delete files
- lifecycle rules are configured at the bucket level (see GCP_SETUP_AND_DEPLOY.md)
"""

from __future__ import annotations

import datetime
import logging
import uuid
from pathlib import Path

from google.cloud import storage

from config import settings
from utils.errors import StorageError

logger = logging.getLogger(__name__)


def _get_client() -> storage.Client:
    """
    Returns a GCS client using Application Default Credentials.
    In Cloud Run: uses the attached service account automatically.
    Locally: uses gcloud auth application-default login or GOOGLE_APPLICATION_CREDENTIALS.
    """
    return storage.Client(project=settings.google_cloud_project_id)


def _bucket(client: storage.Client) -> storage.Bucket:
    return client.bucket(settings.gcs_temp_bucket)


def upload_bytes(
    data: bytes,
    destination_blob_name: str,
    content_type: str,
) -> str:
    """
    Upload raw bytes to GCS.
    Returns the gs:// URI.
    """
    try:
        client = _get_client()
        blob = _bucket(client).blob(destination_blob_name)
        blob.upload_from_string(data, content_type=content_type)
        gcs_uri = f"gs://{settings.gcs_temp_bucket}/{destination_blob_name}"
        logger.info("Uploaded %d bytes to %s", len(data), gcs_uri)
        return gcs_uri
    except Exception as exc:
        raise StorageError(str(exc)) from exc


def upload_file(local_path: Path, destination_blob_name: str, content_type: str) -> str:
    """
    Upload a local file to GCS.
    Returns the gs:// URI.
    """
    try:
        client = _get_client()
        blob = _bucket(client).blob(destination_blob_name)
        blob.upload_from_filename(str(local_path), content_type=content_type)
        gcs_uri = f"gs://{settings.gcs_temp_bucket}/{destination_blob_name}"
        logger.info("Uploaded file %s to %s", local_path, gcs_uri)
        return gcs_uri
    except Exception as exc:
        raise StorageError(str(exc)) from exc


def download_to_file(gcs_uri: str, local_path: Path) -> None:
    """Download a GCS object to a local file path."""
    try:
        client = _get_client()
        blob_name = _blob_name_from_uri(gcs_uri)
        blob = _bucket(client).blob(blob_name)
        blob.download_to_filename(str(local_path))
        logger.info("Downloaded %s to %s", gcs_uri, local_path)
    except Exception as exc:
        raise StorageError(str(exc)) from exc


def generate_signed_url(gcs_uri: str, ttl_hours: int | None = None) -> str:
    """
    Generate a time-limited V4 signed URL for a GCS object.

    On Cloud Run: Uses Application Default Credentials (ADC) attached to the
    Cloud Run service account, passing service_account_email and access_token
    so GCS calls the IAM Credentials API (signBlob).
    Requires roles/iam.serviceAccountTokenCreator on the service account.

    Locally: Uses private key signer if present, or impersonated service account email.
    """
    ttl = ttl_hours or settings.signed_url_ttl_hours
    try:
        client = _get_client()
        blob_name = _blob_name_from_uri(gcs_uri)
        blob = _bucket(client).blob(blob_name)

        credentials = client._credentials

        # If credentials already have a private key signer (e.g. key file or emulator)
        if hasattr(credentials, "signer") and credentials.signer is not None:
            return blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(hours=ttl),
                method="GET",
            )

        # ADC without private key (Cloud Run attached service account):
        from google.auth.transport.requests import Request

        if not credentials.valid:
            credentials.refresh(Request())

        sa_email = (
            getattr(credentials, "service_account_email", None) or settings.service_account_email
        )

        if not sa_email:
            try:
                from google.auth.compute_engine import _metadata

                info = _metadata.get_service_account_info(Request())
                sa_email = info.get("email") if isinstance(info, dict) else None
            except Exception:
                pass

        if not sa_email:
            raise StorageError(
                "Cannot sign URL with ADC: service account email could not be detected. "
                "Ensure RUNTIME_SA/SERVICE_ACCOUNT_EMAIL is set or running on Cloud Run with attached SA."
            )

        return blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=ttl),
            method="GET",
            service_account_email=sa_email,
            access_token=credentials.token,
        )
    except Exception as exc:
        raise StorageError(f"Failed to generate signed URL: {exc}") from exc


def delete_blob(gcs_uri: str) -> None:
    """Delete a GCS object. Silently ignores 404 (already deleted)."""
    try:
        client = _get_client()
        blob_name = _blob_name_from_uri(gcs_uri)
        blob = _bucket(client).blob(blob_name)
        blob.delete()
        logger.info("Deleted %s", gcs_uri)
    except Exception as exc:
        # Log but don't raise — deletion failure is non-critical
        logger.warning("Could not delete %s: %s", gcs_uri, exc)


def make_blob_name(prefix: str, extension: str) -> str:
    """Generate a unique blob name with a given prefix and extension."""
    unique_id = uuid.uuid4().hex
    return f"{prefix}/{unique_id}.{extension.lstrip('.')}"


def _blob_name_from_uri(gcs_uri: str) -> str:
    """Extract the blob name from a gs://bucket/path URI."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Not a valid GCS URI: {gcs_uri}")
    # gs://bucket-name/path/to/blob  →  path/to/blob
    parts = gcs_uri[len("gs://") :].split("/", 1)
    if len(parts) < 2:
        raise ValueError(f"Could not parse blob name from URI: {gcs_uri}")
    return parts[1]
