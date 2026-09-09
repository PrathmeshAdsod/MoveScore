"""
Error types for the Agentic Cinema backend.
All domain errors subclass AgenticCinemaError for consistent handling.
"""

from __future__ import annotations


class AgenticCinemaError(Exception):
    """Base error for all application-level failures."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class VideoTooLargeError(AgenticCinemaError):
    def __init__(self, size_mb: float, max_mb: int) -> None:
        super().__init__(
            f"Video file is {size_mb:.1f} MB, maximum allowed is {max_mb} MB.",
            status_code=413,
        )


class InvalidVideoFormatError(AgenticCinemaError):
    def __init__(self, content_type: str) -> None:
        super().__init__(
            f"Unsupported video format: {content_type}. "
            "Please upload an MP4, MOV, or WebM file.",
            status_code=415,
        )


class ChoreographyAnalysisError(AgenticCinemaError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            f"Choreography analysis failed: {detail}",
            status_code=502,
        )


class MusicPlanError(AgenticCinemaError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            f"Music planning failed: {detail}",
            status_code=502,
        )


class MusicGenerationError(AgenticCinemaError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            f"Music generation failed: {detail}",
            status_code=502,
        )


class MediaCombineError(AgenticCinemaError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            f"Media combine (FFmpeg) failed: {detail}",
            status_code=500,
        )


class StorageError(AgenticCinemaError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            f"Cloud Storage operation failed: {detail}",
            status_code=500,
        )
