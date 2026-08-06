"""
Backend-neutral TTS interfaces and shared dataclasses.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class AudioRetention(str, Enum):
    """Control how long a synthesized audio file should be kept."""

    TEMPORARY = "temporary"
    RETAIN = "retain"


@dataclass(frozen=True)
class VoiceInfo:
    """
    Backend-neutral voice description.
    """

    voice_id: str
    name: str
    language: str
    language_code: str | None = None
    language_name: str | None = None
    country_name: str | None = None
    quality: str | None = None


@dataclass(frozen=True)
class BackendHealth:
    """
    Backend health status.

    The application should remain functional even if the backend is unhealthy.
    """

    name: str
    healthy: bool
    details: str | None = None


@dataclass(frozen=True)
class SynthesisRequest:
    """
    Backend-neutral synthesis request.
    """

    text: str
    request_id: str
    voice_id: str | None = None
    retention: AudioRetention = AudioRetention.TEMPORARY
    output_path: Path | None = None


@dataclass(frozen=True)
class SynthesisResult:
    """
    Result of a successful synthesis operation.
    """

    request_id: str
    voice_id: str
    audio_path: Path
    mime_type: str = "audio/wav"
    retention: AudioRetention = AudioRetention.TEMPORARY


class VoiceMemoryBackend(ABC):
    """Optional backend capability for managing loaded voice models."""

    @abstractmethod
    def load_voice(self, voice_id: str) -> Any:
        """Load a voice into the backend's memory cache."""
        raise NotImplementedError

    @abstractmethod
    def unload_voice(self, voice_id: str) -> None:
        """Release a voice from the backend's memory cache."""
        raise NotImplementedError

    @abstractmethod
    def is_voice_loaded(self, voice_id: str) -> bool:
        """Return whether a voice is currently loaded."""
        raise NotImplementedError

    @abstractmethod
    def loaded_voice_ids(self) -> list[str]:
        """Return IDs for voices currently loaded in memory."""
        raise NotImplementedError


class TTSBackend(ABC):
    """
    Abstract backend interface.

    All TTS backends must implement this contract.
    """

    @abstractmethod
    def backend_name(self) -> str:
        """
        Return the backend identifier.

        Example:
        "piper"
        """
        raise NotImplementedError

    @abstractmethod
    def health(self) -> BackendHealth:
        """
        Return backend health information.
        """
        raise NotImplementedError

    @abstractmethod
    def list_voices(self) -> list[VoiceInfo]:
        """
        Return available voices.
        """
        raise NotImplementedError

    @abstractmethod
    def synthesize(
        self,
        request: SynthesisRequest,
    ) -> SynthesisResult:
        """
        Synthesize text into an audio file.

        Returns:
            SynthesisResult

        Raises:
            TTSBackendError subclasses
        """
        raise NotImplementedError
