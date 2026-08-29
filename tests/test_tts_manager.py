from pathlib import Path

import pytest

from syllavox.constants import DEFAULT_MAX_TEXT_LENGTH
from syllavox.tts.base import (
    AudioRetention,
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    TTSBackend,
    VoiceInfo,
)
from syllavox.tts.errors import (
    BackendUnavailableError,
    InvalidSynthesisRequestError,
    TTSBackendError,
    VoiceNotFoundError,
)
from syllavox.tts.manager import TTSBackendManager
from syllavox.fakes import FakeBackend


class BackendWithoutVoiceMemory(TTSBackend):
    def backend_name(self) -> str:
        return "no-memory"

    def health(self) -> BackendHealth:
        return BackendHealth(name=self.backend_name(), healthy=True)

    def list_voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(
                voice_id="fake-voice",
                name="Fake Voice",
                language="en",
            )
        ]

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        return SynthesisResult(
            request_id=request.request_id,
            voice_id=request.voice_id or "fake-voice",
            audio_path=Path("fake.wav"),
        )


def test_manager_health_returns_backend_health() -> None:
    manager = TTSBackendManager(
        backend=FakeBackend(),
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )

    health = manager.health()

    assert health.name == "fake"
    assert health.healthy is True


def test_manager_returns_voices() -> None:
    manager = TTSBackendManager(
        backend=FakeBackend(),
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )

    voices = manager.list_voices()

    assert len(voices) == 1
    assert voices[0].voice_id == "fake-voice"


def test_manager_rejects_empty_text() -> None:
    manager = TTSBackendManager(
        backend=FakeBackend(),
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )

    with pytest.raises(InvalidSynthesisRequestError):
        manager.synthesize(
            SynthesisRequest(
                text="   ",
                request_id="abc123",
                voice_id="voice-a",
            )
        )


def test_manager_rejects_text_too_long() -> None:
    manager = TTSBackendManager(
        backend=FakeBackend(),
        max_text_length=5,
    )

    with pytest.raises(InvalidSynthesisRequestError):
        manager.synthesize(
            SynthesisRequest(
                text="too long",
                request_id="abc123",
                voice_id="voice-a",
            )
        )


def test_manager_rejects_unhealthy_backend() -> None:
    manager = TTSBackendManager(
        backend=FakeBackend(healthy=False),
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )

    with pytest.raises(BackendUnavailableError):
        manager.list_voices()


def test_manager_selects_default_voice_when_missing() -> None:
    manager = TTSBackendManager(
        backend=FakeBackend(),
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )

    result = manager.synthesize(
        SynthesisRequest(
            text="Hello",
            request_id="abc123",
            voice_id=None,
        )
    )

    assert result.voice_id == "fake-voice"


def test_manager_uses_configured_default_voice_when_request_omits_voice() -> None:
    backend = FakeBackend(
        voices=[
            VoiceInfo(
                voice_id="voice-a",
                name="Voice A",
                language="en",
            ),
            VoiceInfo(
                voice_id="voice-b",
                name="Voice B",
                language="es",
            ),
        ]
    )
    manager = TTSBackendManager(
        backend=backend,
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
        default_voice_id="voice-b",
    )

    result = manager.synthesize(
        SynthesisRequest(
            text="Hola",
            request_id="abc123",
            voice_id=None,
        )
    )

    assert result.voice_id == "voice-b"


def test_manager_falls_back_when_configured_default_voice_disappears() -> None:
    manager = TTSBackendManager(
        backend=FakeBackend(),
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
        default_voice_id="missing",
    )

    result = manager.synthesize(
        SynthesisRequest(
            text="Hello",
            request_id="abc123",
            voice_id=None,
        )
    )

    assert result.voice_id == "fake-voice"
    assert manager.default_voice_id is None


def test_manager_preserves_requested_audio_retention() -> None:
    manager = TTSBackendManager(
        backend=FakeBackend(),
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )

    result = manager.synthesize(
        SynthesisRequest(
            text="Hello",
            request_id="abc123",
            retention=AudioRetention.RETAIN,
        )
    )

    assert result.retention == AudioRetention.RETAIN


def test_manager_preserves_explicit_output_path() -> None:
    backend = FakeBackend()
    manager = TTSBackendManager(
        backend=backend,
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )
    output_path = Path("export.wav")

    manager.synthesize(
        SynthesisRequest(
            text="Hello",
            request_id="abc123",
            output_path=output_path,
        )
    )

    assert backend.last_request.output_path == output_path


def test_manager_rejects_unknown_voice() -> None:
    manager = TTSBackendManager(
        backend=FakeBackend(),
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )

    with pytest.raises(VoiceNotFoundError):
        manager.synthesize(
            SynthesisRequest(
                text="Hello",
                request_id="abc123",
                voice_id="missing",
            )
        )


def test_manager_loads_and_unloads_voice() -> None:
    backend = FakeBackend()
    manager = TTSBackendManager(backend=backend)

    manager.load_voice("fake-voice")
    assert manager.is_voice_loaded("fake-voice") is True
    assert manager.loaded_voice_ids() == ["fake-voice"]

    manager.unload_voice("fake-voice")
    assert manager.is_voice_loaded("fake-voice") is False
    assert manager.loaded_voice_ids() == []


def test_manager_shutdown_releases_all_loaded_voices() -> None:
    backend = FakeBackend()
    manager = TTSBackendManager(backend=backend)

    manager.load_voice("fake-voice")
    manager.shutdown()

    assert backend.loaded_voice_ids() == []


def test_manager_handles_backend_without_voice_memory_capability() -> None:
    manager = TTSBackendManager(backend=BackendWithoutVoiceMemory())

    with pytest.raises(TTSBackendError, match="does not support voice loading"):
        manager.load_voice("fake-voice")

    with pytest.raises(TTSBackendError, match="does not support voice unloading"):
        manager.unload_voice("fake-voice")

    assert manager.is_voice_loaded("fake-voice") is False
    assert manager.loaded_voice_ids() == []
