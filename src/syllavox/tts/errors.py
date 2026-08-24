"""
TTS backend exception hierarchy.

These exceptions are backend-agnostic and are intended to be translated into
stable API error responses at higher layers.
"""

from __future__ import annotations


class TTSBackendError(Exception):
    """
    Base exception for all TTS backend failures.
    """

    pass


class BackendUnavailableError(TTSBackendError):
    """
    Raised when the configured backend is unavailable or unhealthy.

    Examples:
    - Piper executable missing
    - model directory missing
    - no valid voices available
    """

    pass


class VoiceNotFoundError(TTSBackendError):
    """
    Raised when a requested voice ID does not exist.
    """

    def __init__(self, voice_id: str) -> None:
        self.voice_id = voice_id

        super().__init__(f"Voice not found: {voice_id}")


class VoiceCatalogError(TTSBackendError):
    """Raised when the remote Piper voice catalog cannot be read or used."""

    pass


class SynthesisFailedError(TTSBackendError):
    """
    Raised when synthesis fails unexpectedly.

    Examples:
    - backend process failure
    - invalid model
    - output WAV generation failure
    """

    pass


class LanguageCompatibilityError(SynthesisFailedError):
    """Raised when a voice's language phonemizer is unsupported by Piper."""

    pass


class InvalidSynthesisRequestError(TTSBackendError):
    """
    Raised when a synthesis request is invalid before synthesis begins.

    Examples:
    - empty text
    - text too long
    - unsupported request parameters
    """

    pass
