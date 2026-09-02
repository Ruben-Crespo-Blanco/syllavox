from __future__ import annotations

from types import SimpleNamespace
import wave

import pytest

import syllavox.tts.linux_espeak as linux_espeak
from syllavox.tts.base import AudioRetention, SynthesisRequest
from syllavox.tts.errors import BackendUnavailableError


VOICE_OUTPUT = (
    "Pty Language Age/Gender VoiceName File Other Languages\n"
    " 5   af             M  af              Afrikaans\n"
    " 5   en-US          M  en-us           English\n"
)


def test_linux_espeak_discovers_readable_voice_metadata(monkeypatch) -> None:
    calls: list[tuple[list[str], str | None]] = []

    def runner(command, *, input, **kwargs):
        del kwargs
        calls.append((command, input))
        return SimpleNamespace(stdout=VOICE_OUTPUT, stderr="")

    monkeypatch.setattr(linux_espeak.sys, "platform", "linux")
    provider = linux_espeak.LinuxESpeakProvider(
        command_runner=runner,
        command_exists=lambda _: "/usr/bin/espeak-ng",
    )

    voices = provider.list_voices()

    assert [voice.language_name for voice in voices] == ["Afrikaans", "English"]
    assert [voice.language_code for voice in voices] == ["af", "en-US"]
    assert [voice.name for voice in voices] == ["af", "en-us"]
    assert all(voice.voice_id.startswith("linux_espeak_ng:") for voice in voices)
    assert calls == [(["/usr/bin/espeak-ng", "--voices"], None)]


def test_linux_espeak_renders_valid_wav_and_cleans_intermediates(
    monkeypatch,
    tmp_path,
) -> None:
    commands: list[list[str]] = []

    def runner(command, *, input, **kwargs):
        del kwargs
        commands.append(command)
        if command[-1] == "--voices":
            return SimpleNamespace(stdout=VOICE_OUTPUT, stderr="")
        with wave.open(command[-1], "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(22050)
            output.writeframes(b"\x00\x00" * 32)
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(linux_espeak.sys, "platform", "linux")
    provider = linux_espeak.LinuxESpeakProvider(
        command_runner=runner,
        command_exists=lambda _: "/usr/bin/espeak-ng",
    )
    voice = provider.list_voices()[0]
    output_path = tmp_path / "speech.wav"

    result = provider.synthesize(
        SynthesisRequest(
            text="Goeie dag van Syllavox",
            request_id="request-linux",
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
    assert commands[1][:4] == [
        "/usr/bin/espeak-ng",
        "--stdin",
        "-v",
        "af",
    ]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["speech.wav"]


def test_linux_espeak_reports_missing_system_package(monkeypatch) -> None:
    monkeypatch.setattr(linux_espeak.sys, "platform", "linux")
    provider = linux_espeak.LinuxESpeakProvider(command_exists=lambda _: None)

    with pytest.raises(BackendUnavailableError, match="espeak-ng"):
        provider.list_voices()


def test_linux_espeak_is_unavailable_off_linux(monkeypatch) -> None:
    monkeypatch.setattr(linux_espeak.sys, "platform", "win32")
    provider = linux_espeak.LinuxESpeakProvider()

    with pytest.raises(BackendUnavailableError, match="only on Linux"):
        provider.list_voices()
