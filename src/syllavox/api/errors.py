"""
API error model and helpers.

Defines:
- stable error codes
- structured error payloads
- helper functions for rejected responses

The response format is designed to remain stable across future epics.
"""

from __future__ import annotations

from enum import Enum
from logging import Logger
from typing import Any

from syllavox.audio.errors import PlaybackError
from syllavox.state import InvalidStateTransitionError
from syllavox.tts.errors import (
    BackendUnavailableError,
    InvalidSynthesisRequestError,
    SynthesisFailedError,
    TTSBackendError,
    VoiceNotFoundError,
)


class ErrorCode(str, Enum):
    """
    Stable API error codes.

    These codes are intentionally defined up front so future epics can
    reuse them without changing the response structure.
    """

    # Validation errors
    EMPTY_TEXT = "EMPTY_TEXT"
    TEXT_TOO_LONG = "TEXT_TOO_LONG"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"

    # Application state errors
    BUSY = "BUSY"

    # Backend errors
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"

    # Security errors
    FORBIDDEN_ORIGIN = "FORBIDDEN_ORIGIN"

    # Unexpected server-side failures
    INTERNAL_ERROR = "INTERNAL_ERROR"


def make_error(
    code: ErrorCode,
    message: str,
) -> dict[str, str]:
    """
    Create the standard error object.

    Example:
    {
        "code": "TEXT_TOO_LONG",
        "message": "Text exceeds the configured character limit."
    }
    """
    return {
        "code": code.value,
        "message": message,
    }


def make_rejected_response(
    code: ErrorCode,
    message: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a standard rejected API response.

    Example:
    {
        "status": "rejected",
        "requestId": "abc123",
        "error": {
            "code": "TEXT_TOO_LONG",
            "message": "Text exceeds the configured character limit."
        }
    }
    """
    return {
        "status": "rejected",
        "requestId": request_id,
        "error": make_error(code, message),
    }
def make_backend_error_response(
    message: str = "The TTS backend is unavailable.",
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Convenience helper for backend availability errors.
    """
    return make_rejected_response(
        code=ErrorCode.BACKEND_UNAVAILABLE,
        message=message,
        request_id=request_id,
    )
def make_speech_error_response(
    exc: Exception,
    request_id: str,
    logger: Logger,
) -> dict[str, Any]:
    """Translate a speech-service exception into the stable API format."""
    if isinstance(exc, BackendUnavailableError):
        logger.warning(
            "Backend unavailable for request_id=%s: %s",
            request_id,
            exc,
        )
        return make_backend_error_response(
            message=str(exc),
            request_id=request_id,
        )

    if isinstance(exc, InvalidSynthesisRequestError):
        logger.warning(
            "Invalid synthesis request request_id=%s: %s",
            request_id,
            exc,
        )
        return make_rejected_response(
            ErrorCode.INVALID_PAYLOAD,
            str(exc),
            request_id=request_id,
        )

    if isinstance(exc, VoiceNotFoundError):
        logger.warning(
            "Voice not found request_id=%s: %s",
            request_id,
            exc,
        )
        return make_rejected_response(
            ErrorCode.INVALID_PAYLOAD,
            str(exc),
            request_id=request_id,
        )

    if isinstance(exc, SynthesisFailedError):
        logger.error(
            "Synthesis failed request_id=%s: %s",
            request_id,
            exc,
        )
        return make_rejected_response(
            ErrorCode.INTERNAL_ERROR,
            "Synthesis failed.",
            request_id=request_id,
        )

    if isinstance(exc, PlaybackError):
        logger.error(
            "Playback failed request_id=%s: %s",
            request_id,
            exc,
        )
        return make_rejected_response(
            ErrorCode.INTERNAL_ERROR,
            "Playback failed.",
            request_id=request_id,
        )

    if isinstance(exc, InvalidStateTransitionError):
        logger.error(
            "State transition failed request_id=%s: %s",
            request_id,
            exc,
        )
        return make_rejected_response(
            ErrorCode.INTERNAL_ERROR,
            "Unable to enter speaking state.",
            request_id=request_id,
        )

    if isinstance(exc, TTSBackendError):
        logger.error(
            "Unexpected backend error request_id=%s: %s",
            request_id,
            exc,
        )
        return make_rejected_response(
            ErrorCode.INTERNAL_ERROR,
            "Unexpected backend error.",
            request_id=request_id,
        )

    logger.exception(
        "Unexpected speak failure request_id=%s",
        request_id,
    )
    return make_rejected_response(
        ErrorCode.INTERNAL_ERROR,
        "Unexpected internal error.",
        request_id=request_id,
    )
