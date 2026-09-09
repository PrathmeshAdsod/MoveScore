"""
Upload route — POST /upload

Accepts a multipart video file, validates it, uploads to GCS,
and returns the GCS URI + a short-lived signed preview URL.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from config import settings
from schemas.api import UploadResponse
from services import storage as gcs
from utils.errors import AgenticCinemaError

logger = logging.getLogger(__name__)
router = APIRouter()

ACCEPTED_MIME_TYPES = {
    "video/mp4",
}

# Some browsers send incorrect MIME types for video files
ACCEPTED_EXTENSIONS = {".mp4"}


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a dance video file to GCS temporary storage.
    Returns GCS URI and a signed preview URL.
    """
    # Validate content type
    content_type = (file.content_type or "").lower()
    filename = file.filename or "video"
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ACCEPTED_EXTENSIONS or content_type not in ACCEPTED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. "
            "Please upload an MP4 file.",
        )

    # Read file into memory
    video_bytes = await file.read()

    # Validate size
    size_bytes = len(video_bytes)
    max_bytes = settings.max_video_size_bytes
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is {size_bytes / 1024 / 1024:.1f} MB. "
            f"Maximum allowed is {settings.max_video_size_mb} MB.",
        )

    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Mandatory video duration validation (max 60 seconds)
    import tempfile
    from pathlib import Path

    from services.ffmpeg_service import validate_video_duration

    with tempfile.NamedTemporaryFile(
        suffix=extension or ".mp4", delete=False
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)
        tmp_file.write(video_bytes)

    try:
        duration = validate_video_duration(tmp_path, max_duration_sec=60.0)
        logger.info("Uploaded video duration validated: %.2fs", duration)
    except AgenticCinemaError as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        logger.error("Duration validation failed: %s", exc)
        raise HTTPException(
            status_code=400, detail=f"Could not validate video duration: {exc}"
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    # Upload to GCS
    blob_name = gcs.make_blob_name("uploads", extension.lstrip(".") or "mp4")
    try:
        gcs_uri = gcs.upload_bytes(video_bytes, blob_name, content_type)
        preview_url = gcs.generate_signed_url(gcs_uri, ttl_hours=2)
    except AgenticCinemaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.error("Upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to upload video.")

    logger.info(
        "Video uploaded: %s (%d bytes, type=%s)", gcs_uri, size_bytes, content_type
    )

    return UploadResponse(
        gcs_uri=gcs_uri,
        preview_signed_url=preview_url,
        filename=filename,
        size_bytes=size_bytes,
    )
