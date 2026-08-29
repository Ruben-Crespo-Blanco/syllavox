"""
Backend orchestration and active backend management.

The rest of the application should depend on TTSBackendManager rather than
directly depending on a specific backend implementatio.
"""

from __future__ import annotations

from syllavox.constants import DEFAULT_MAX_TEXT_LENGTH
from syllavox.tts.base import (
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    TTSBackend,
    VoiceMemoryBackend,
    VoiceInfo,
)
from syllavox.tts.errors import (
    BackendUnavailableError,
    InvalidSynthesisRequestError,
    TTSBackendError,
    VoiceNotFoundError,
)


class TTSBackendManager:
    """
    High-level backend orchestration layer.

    Responsibilities:
    - hold active backend
    - expose health()
    - expose list_voices()
    - resolve default voice
    - validate synthesis requests
    - invoke backend synthesis
    """

    def __init__(
        self,
        backend: TTSBackend,
        max_text_length: int = DEFAULT_MAX_TEXT_LENGTH,
        default_voice_id: str | None = None,
    ) -> None:
        self._backend = backend
        self._max_text_length = max_text_length
        self._default_voice_id = default_voice_id

    @property
    def default_voice_id(self) -> str | None:
        """Return the shared voice used when a request omits a voice ID."""
        return self._default_voice_id

    @property
    def active_backend(self) -> TTSBackend:
        """Return the active backend for capability-aware UI composition."""
        return self._backend

    def set_default_voice_id(self, voice_id: str | None) -> None:
        """Set the shared default voice for UI, hotkey, and API requests."""
        self._default_voice_id = voice_id

    def load_voice(self, voice_id: str) -> None:
        """Load a voice into the active backend's memory cache."""
        self._ensure_backend_healthy()
        self._ensure_voice_exists(voice_id)

        memory_backend = self._voice_memory_backend()
        if memory_backend is None:
            raise TTSBackendError(
                f"Backend {self.backend_name()} does not support voice loading."
            )

        memory_backend.load_voice(voice_id)

    def unload_voice(self, voice_id: str) -> None:
        """Unload a voice from memory while keeping its files on disk."""
        memory_backend = self._voice_memory_backend()
        if memory_backend is None:
            raise TTSBackendError(
                f"Backend {self.backend_name()} does not support voice unloading."
            )

        memory_backend.unload_voice(voice_id)

    def is_voice_loaded(self, voice_id: str) -> bool:
        """Return whether a voice is currently loaded in memory."""
        memory_backend = self._voice_memory_backend()
        if memory_backend is None:
            return False

        return bool(memory_backend.is_voice_loaded(voice_id))

    def loaded_voice_ids(self) -> list[str]:
        """Return loaded voice IDs when supported by the active backend."""
        memory_backend = self._voice_memory_backend()
        if memory_backend is None:
            return []

        return list(memory_backend.loaded_voice_ids())

    def shutdown(self) -> None:
        """Release all model resources owned by the active backend."""
        backend_shutdown = getattr(self._backend, "shutdown", None)
        if callable(backend_shutdown):
            backend_shutdown()
            return

        memory_backend = self._voice_memory_backend()
        if memory_backend is None:
            return

        for voice_id in list(memory_backend.loaded_voice_ids()):
            memory_backend.unload_voice(voice_id)

    def backend_name(self) -> str:
        """
        Return the active backend name.
        """
        return self._backend.backend_name()

    def health(self) -> BackendHealth:
        """
        Return backend health information.

        Never raises.
        """
        try:
            return self._backend.health()

        except Exception as exc:
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details=f"Health check failed: {exc}",
            )

    def list_voices(self) -> list[VoiceInfo]:
        """
        Return available voices.

        Raises:
            BackendUnavailableError
        """
        self._ensure_backend_healthy()

        return self._backend.list_voices()

    def get_default_voice(self) -> VoiceInfo:
        """
        Return the default voice.

        The configured shared voice is preferred when it is available.
        Otherwise, the first discovered voice is used as a safe fallback.
        """
        voices = self.list_voices()

        if not voices:
            raise BackendUnavailableError(
                "No voices are available."
            )

        if self._default_voice_id is not None:
            configured_voice = next(
                (
                    voice
                    for voice in voices
                    if voice.voice_id == self._default_voice_id
                ),
                None,
            )

            if configured_voice is not None:
                return configured_voice

            self._default_voice_id = None

        return voices[0]

    def synthesize(
        self,
        request: SynthesisRequest,
    ) -> SynthesisResult:
        """
        Validate and perform synthesis.

        Raises:
            InvalidSynthesisRequestError
            BackendUnavailableError
            VoiceNotFoundError
            TTSBackendError
        """
        self._validate_request(request)
        self._ensure_backend_healthy()

        voice_id = request.voice_id

        if voice_id is None:
            voice_id = self.get_default_voice().voice_id

            request = SynthesisRequest(
                text=request.text,
                request_id=request.request_id,
                voice_id=voice_id,
                retention=request.retention,
                output_path=request.output_path,
            )

        self._ensure_voice_exists(voice_id)

        return self._backend.synthesize(request)

    def _validate_request(
        self,
        request: SynthesisRequest,
    ) -> None:
        """
        Validate a synthesis request before backend execution.
        """
        text = request.text.strip()

        if not text:
            raise InvalidSynthesisRequestError(
                "Text cannot be empty."
            )

        if len(text) > self._max_text_length:
            raise InvalidSynthesisRequestError(
                f"Text exceeds the maximum length of "
                f"{self._max_text_length} characters."
            )

    def _ensure_backend_healthy(self) -> None:
        """
        Raise if the backend is unavailable.
        """
        health = self.health()

        if not health.healthy:
            raise BackendUnavailableError(
                health.details or "Backend is unavailable."
            )

    def _ensure_voice_exists(
        self,
        voice_id: str,
    ) -> None:
        """
        Validate that the requested voice exists.
        """
        available_voice_ids = {
            voice.voice_id
            for voice in self.list_voices()
        }

        if voice_id not in available_voice_ids:
            raise VoiceNotFoundError(voice_id)

    def _voice_memory_backend(self) -> VoiceMemoryBackend | None:
        """Return the active backend's explicit voice-memory capability."""
        if isinstance(self._backend, VoiceMemoryBackend):
            return self._backend

        return None
