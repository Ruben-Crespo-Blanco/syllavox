"""Combine a model-backed voice engine with zero-download system voices."""

from __future__ import annotations

from typing import Any

from syllavox.tts.base import (
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    TTSBackend,
    VoiceInfo,
    VoiceMemoryBackend,
)
from syllavox.tts.errors import TTSBackendError, VoiceNotFoundError


class SystemVoiceFallbackBackend(TTSBackend, VoiceMemoryBackend):
    """Expose system voices beside a primary downloadable-voice backend.

    The primary backend keeps its public identity so existing settings and
    voice-catalog behavior remain stable. Requests for system-owned voice IDs
    are routed to the fallback backend; model-memory operations remain owned by
    the primary backend.
    """

    def __init__(self, primary: TTSBackend, system_fallback: TTSBackend) -> None:
        self.primary_backend = primary
        self.system_backend = system_fallback

    def backend_name(self) -> str:
        return self.primary_backend.backend_name()

    def health(self) -> BackendHealth:
        primary_health = self._safe_health(self.primary_backend)
        system_health = self._safe_health(self.system_backend)
        healthy = primary_health.healthy or system_health.healthy
        details = (
            f"Primary: {primary_health.details or primary_health.healthy}; "
            f"system fallback: {system_health.details or system_health.healthy}"
        )
        return BackendHealth(
            name=self.backend_name(),
            healthy=healthy,
            details=details,
        )

    def list_voices(self) -> list[VoiceInfo]:
        voices: list[VoiceInfo] = []
        seen: set[str] = set()
        for backend in (self.primary_backend, self.system_backend):
            for voice in self._safe_voices(backend):
                if voice.voice_id in seen:
                    continue
                voices.append(voice)
                seen.add(voice.voice_id)
        return voices

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        if request.voice_id is None:
            raise VoiceNotFoundError("No voice was selected.")
        primary_ids = {
            voice.voice_id for voice in self._safe_voices(self.primary_backend)
        }
        if request.voice_id in primary_ids:
            return self.primary_backend.synthesize(request)
        system_ids = {
            voice.voice_id for voice in self._safe_voices(self.system_backend)
        }
        if request.voice_id in system_ids:
            return self.system_backend.synthesize(request)
        raise VoiceNotFoundError(request.voice_id)

    def load_voice(self, voice_id: str) -> Any:
        memory_backend = self._primary_memory_backend()
        self._require_primary_voice(voice_id)
        if memory_backend is None:
            raise TTSBackendError("The primary voice engine does not load voices.")
        return memory_backend.load_voice(voice_id)

    def unload_voice(self, voice_id: str) -> None:
        memory_backend = self._primary_memory_backend()
        self._require_primary_voice(voice_id)
        if memory_backend is None:
            raise TTSBackendError("The primary voice engine does not unload voices.")
        memory_backend.unload_voice(voice_id)

    def is_voice_loaded(self, voice_id: str) -> bool:
        memory_backend = self._primary_memory_backend()
        if memory_backend is None or not self.is_primary_voice(voice_id):
            return False
        return bool(memory_backend.is_voice_loaded(voice_id))

    def loaded_voice_ids(self) -> list[str]:
        memory_backend = self._primary_memory_backend()
        if memory_backend is None:
            return []
        return list(memory_backend.loaded_voice_ids())

    def is_primary_voice(self, voice_id: str) -> bool:
        return any(
            voice.voice_id == voice_id
            for voice in self._safe_voices(self.primary_backend)
        )

    def is_system_voice(self, voice_id: str) -> bool:
        return not self.is_primary_voice(voice_id) and any(
            voice.voice_id == voice_id
            for voice in self._safe_voices(self.system_backend)
        )

    def shutdown(self) -> None:
        for backend in (self.primary_backend, self.system_backend):
            shutdown = getattr(backend, "shutdown", None)
            if callable(shutdown):
                shutdown()

    def _require_primary_voice(self, voice_id: str) -> None:
        if not self.is_primary_voice(voice_id):
            raise TTSBackendError(
                "System voices are managed by the operating system."
            )

    def _primary_memory_backend(self) -> VoiceMemoryBackend | None:
        if isinstance(self.primary_backend, VoiceMemoryBackend):
            return self.primary_backend
        return None

    @staticmethod
    def _safe_health(backend: TTSBackend) -> BackendHealth:
        try:
            return backend.health()
        except Exception as exc:
            return BackendHealth(
                name=backend.backend_name(),
                healthy=False,
                details=str(exc),
            )

    @classmethod
    def _safe_voices(cls, backend: TTSBackend) -> list[VoiceInfo]:
        if not cls._safe_health(backend).healthy:
            return []
        try:
            return list(backend.list_voices())
        except Exception:
            return []


__all__ = ["SystemVoiceFallbackBackend"]
