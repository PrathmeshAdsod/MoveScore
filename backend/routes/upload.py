"""
Upload route — POST /upload

Accepts a multipart video file, validates it, uploads to GCS,
and returns the GCS URI + a short-lived signed preview URL.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from config import settings
from schemas.api import UploadResponse
from services import storage as gcs
from utils.errors import AgenticCinemaError, InvalidVideoFormatError, VideoTooLargeError

logger = logging.getLogger(__name__)
router = APIRouter()

ACCEPTED_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
    "video/avi",
}

# Some browsers send incorrect MIME types for video files
ACCEPTED_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi"}


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

    if content_type not in ACCEPTED_MIME_TYPES and extension not in ACCEPTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. "
            "Please upload an MP4, MOV, or WebM file.",
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

    # Normalize MIME type
    if content_type not in ACCEPTED_MIME_TYPES:
        # Infer from extension
        ext_map = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
        content_type = ext_map.get(extension, "video/mp4")

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
