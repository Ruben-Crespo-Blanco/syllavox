from __future__ import annotations

from types import SimpleNamespace
import wave

import pytest

import syllavox.tts.macos_speech as macos_speech
from syllavox.tts.base import AudioRetention, SynthesisRequest
from syllavox.tts.errors import BackendUnavailableError


def test_macos_speech_discovers_readable_voice_metadata(monkeypatch) -> None:
    calls: list[tuple[list[str], str | None]] = []

    def runner(command, *, input, **kwargs):
        del kwargs
        calls.append((command, input))
        return SimpleNamespace(
            stdout="Alex en_US # English voice\nAmelie fr_FR # French voice\n",
            stderr="",
        )

    monkeypatch.setattr(macos_speech.sys, "platform", "darwin")
    provider = macos_speech.MacOSSystemSpeechProvider(
        command_runner=runner,
        command_exists=lambda _: True,
    )

    voices = provider.list_voices()

    assert [voice.name for voice in voices] == ["Alex", "Amelie"]
    assert [voice.language_code for voice in voices] == ["en-US", "fr-FR"]
    assert [voice.language_name for voice in voices] == ["English", "French"]
    assert all(voice.voice_id.startswith("macos_system:") for voice in voices)
    assert calls[0][0] == [macos_speech.SAY_PATH, "-v", "?"]


def test_macos_speech_renders_valid_wav_and_cleans_intermediates(
    monkeypatch,
    tmp_path,
) -> None:
    commands: list[list[str]] = []

    def runner(command, *, input, **kwargs):
        del input, kwargs
        commands.append(command)
        if command[:3] == [macos_speech.SAY_PATH, "-v", "?"]:
            return SimpleNamespace(stdout="Alex en_US # English\n", stderr="")
        if command[0] == macos_speech.AFCONVERT_PATH:
            with wave.open(command[-1], "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(22050)
                output.writeframes(b"\x00\x00" * 32)
            return SimpleNamespace(stdout="", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(macos_speech.sys, "platform", "darwin")
    provider = macos_speech.MacOSSystemSpeechProvider(
        command_runner=runner,
        command_exists=lambda _: True,
    )
    voice = provider.list_voices()[0]
    output_path = tmp_path / "speech.wav"

    result = provider.synthesize(
        SynthesisRequest(
            text="Hello from Syllavox",
            request_id="request-macos",
            voice_id=voice.voice_id,
            retention=AudioRetention.RETAIN,
            output_path=output_path,
        )
    )

    assert result.audio_path == output_path
    with wave.open(str(output_path), "rb") as rendered:
        assert rendered.getnchannels() == 1
        assert rendered.getsampwidth() == 2
        assert rendered.getnframes() == 32
    assert commands[1][:4] == [macos_speech.SAY_PATH, "-v", "Alex", "-o"]
    assert commands[2][:5] == [
        macos_speech.AFCONVERT_PATH,
        "-f",
        "WAVE",
        "-d",
        "LEI16@22050",
    ]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["speech.wav"]


def test_macos_speech_is_unavailable_off_macos(monkeypatch) -> None:
    monkeypatch.setattr(macos_speech.sys, "platform", "win32")
    provider = macos_speech.MacOSSystemSpeechProvider()

    with pytest.raises(BackendUnavailableError, match="only on macOS"):
        provider.list_voices()

