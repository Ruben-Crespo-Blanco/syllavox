from pathlib import Path

import pytest

from syllavox.fakes import FakeBackend
from syllavox.tts.base import SynthesisRequest, VoiceInfo
from syllavox.tts.errors import TTSBackendError
from syllavox.tts.fallback import SystemVoiceFallbackBackend


def make_backend(
    tmp_path: Path,
    name: str,
    voice_id: str,
    *,
    healthy: bool = True,
) -> FakeBackend:
    backend = FakeBackend(
        audio_path=tmp_path / f"{name}.wav",
        healthy=healthy,
        voices=[VoiceInfo(voice_id=voice_id, name=name, language="en")],
    )
    backend.audio_path.write_bytes(b"wav")
    backend.backend_name = lambda: name  # type: ignore[method-assign]
    return backend


def test_fallback_lists_primary_then_system_voices(tmp_path: Path) -> None:
    primary = make_backend(tmp_path, "piper", "local-voice")
    system = make_backend(tmp_path, "system", "system-voice")
    backend = SystemVoiceFallbackBackend(primary, system)

    assert backend.backend_name() == "piper"
    assert [voice.voice_id for voice in backend.list_voices()] == [
        "local-voice",
        "system-voice",
    ]
    assert backend.health().healthy is True


def test_fallback_routes_synthesis_by_voice_owner(tmp_path: Path) -> None:
    primary = make_backend(tmp_path, "piper", "local-voice")
    system = make_backend(tmp_path, "system", "system-voice")
    backend = SystemVoiceFallbackBackend(primary, system)

    backend.synthesize(
        SynthesisRequest("Hello", "one", voice_id="system-voice")
    )
    backend.synthesize(
        SynthesisRequest("Hello", "two", voice_id="local-voice")
    )

    assert [call.request_id for call in system.synthesis_calls] == ["one"]
    assert [call.request_id for call in primary.synthesis_calls] == ["two"]


def test_fallback_remains_healthy_when_primary_is_unavailable(tmp_path: Path) -> None:
    primary = make_backend(
        tmp_path,
        "piper",
        "local-voice",
        healthy=False,
    )
    system = make_backend(tmp_path, "system", "system-voice")
    backend = SystemVoiceFallbackBackend(primary, system)

    assert backend.health().healthy is True
    assert [voice.voice_id for voice in backend.list_voices()] == ["system-voice"]


def test_fallback_rejects_model_management_for_system_voice(tmp_path: Path) -> None:
    primary = make_backend(tmp_path, "piper", "local-voice")
    system = make_backend(tmp_path, "system", "system-voice")
    backend = SystemVoiceFallbackBackend(primary, system)

    with pytest.raises(TTSBackendError, match="operating system"):
        backend.load_voice("system-voice")
