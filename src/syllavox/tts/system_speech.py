"""Backend-neutral adapters for operating-system speech providers.

System voices are different from model-backed voices: they are discovered and
managed by the operating system, so Syllavox should not try to load or delete
their files.  This module keeps that distinction behind the same TTSBackend
contract used by Piper and Sherpa-ONNX.
"""

from __future__ import annotations

from typing import Protocol

from syllavox.tts.base import (
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    TTSBackend,
    VoiceInfo,
)


class SystemSpeechProvider(Protocol):
    """Provider boundary for a platform's installed speech voices."""

    def backend_name(self) -> str:
        """Return the stable backend identifier."""

    def health(self) -> BackendHealth:
        """Return provider availability without raising."""

    def list_voices(self) -> list[VoiceInfo]:
        """Return voices installed and visible to the operating system."""

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Render a request to a WAV file."""

    def shutdown(self) -> None:
        """Release provider-owned resources."""


class SystemSpeechBackend(TTSBackend):
    """Adapt a system speech provider to Syllavox's TTS backend contract."""

    def __init__(self, provider: SystemSpeechProvider) -> None:
        self._provider = provider

    @property
    def provider(self) -> SystemSpeechProvider:
        """Return the underlying provider for diagnostics and UI composition."""
        return self._provider

    def backend_name(self) -> str:
        return self._provider.backend_name()

    def health(self) -> BackendHealth:
        return self._provider.health()

    def list_voices(self) -> list[VoiceInfo]:
        return self._provider.list_voices()

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        return self._provider.synthesize(request)

    def shutdown(self) -> None:
        self._provider.shutdown()


__all__ = ["SystemSpeechBackend", "SystemSpeechProvider"]
