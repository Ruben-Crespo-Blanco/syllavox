from pathlib import Path

from syllavox.tts.base import (
    AudioRetention,
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    VoiceInfo,
)


def test_voice_info_creation() -> None:
    voice = VoiceInfo(
        voice_id="en_US-lessac-medium",
        name="en_US lessac medium",
        language="en",
    )

    assert voice.voice_id == "en_US-lessac-medium"
    assert voice.name == "en_US lessac medium"
    assert voice.language == "en"


def test_backend_health_creation() -> None:
    health = BackendHealth(
        name="piper",
        healthy=True,
        details="1 voice(s) available.",
    )

    assert health.name == "piper"
    assert health.healthy is True
    assert health.details == "1 voice(s) available."


def test_synthesis_request_creation() -> None:
    request = SynthesisRequest(
        text="Hello",
        request_id="abc123",
        voice_id="en_US-lessac-medium",
    )

    assert request.text == "Hello"
    assert request.request_id == "abc123"
    assert request.voice_id == "en_US-lessac-medium"
    assert request.retention == AudioRetention.TEMPORARY
    assert request.output_path is None


def test_synthesis_request_can_select_an_output_path(tmp_path: Path) -> None:
    output_path = tmp_path / "export.wav"

    request = SynthesisRequest(
        text="Hello",
        request_id="abc123",
        output_path=output_path,
    )

    assert request.output_path == output_path


def test_synthesis_result_creation(tmp_path: Path) -> None:
    audio_path = tmp_path / "out.wav"

    result = SynthesisResult(
        request_id="abc123",
        voice_id="en_US-lessac-medium",
        audio_path=audio_path,
    )

    assert result.request_id == "abc123"
    assert result.voice_id == "en_US-lessac-medium"
    assert result.audio_path == audio_path
    assert result.mime_type == "audio/wav"
    assert result.retention == AudioRetention.TEMPORARY


def test_synthesis_result_can_request_retention(tmp_path: Path) -> None:
    result = SynthesisResult(
        request_id="abc123",
        voice_id="en_US-lessac-medium",
        audio_path=tmp_path / "out.wav",
        retention=AudioRetention.RETAIN,
    )

    assert result.retention == AudioRetention.RETAIN
