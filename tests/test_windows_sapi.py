from __future__ import annotations

import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

import syllavox.tts.windows_sapi as windows_sapi
from syllavox.tts.base import SynthesisRequest
from syllavox.tts.errors import SynthesisFailedError


class _FakeToken:
    def __init__(self, token_id: str, description: str, language: str) -> None:
        self.Id = token_id
        self._description = description
        self._language = language

    def GetDescription(self) -> str:
        return self._description

    def GetAttribute(self, name: str) -> str | None:
        return self._language if name == "Language" else None


class _FakeTokenCollection:
    def __init__(self, tokens: list[_FakeToken]) -> None:
        self._tokens = tokens
        self.Count = len(tokens)

    def Item(self, index: int) -> _FakeToken:
        return self._tokens[index]


class _FakeStream:
    def __init__(self) -> None:
        self.path: Path | None = None
        self.Format = SimpleNamespace(Type=None)

    def Open(self, path: str, mode: int, do_events: bool) -> None:
        del mode, do_events
        self.path = Path(path)

    def Close(self) -> None:
        return None


class _FakeVoice:
    def __init__(self, tokens: _FakeTokenCollection, *, fail: bool = False) -> None:
        self._tokens = tokens
        self._fail = fail
        self.Voice = None
        self.AudioOutputStream: _FakeStream | None = None

    def GetVoices(self) -> _FakeTokenCollection:
        return self._tokens

    def Speak(self, text: str, flags: int) -> None:
        del flags
        if self._fail:
            raise RuntimeError("fake SAPI failure")
        assert text
        assert self.AudioOutputStream is not None
        assert self.AudioOutputStream.path is not None
        with wave.open(str(self.AudioOutputStream.path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x00\x00" * 2205)


class _FakeCom:
    def __init__(self) -> None:
        self.initialize_count = 0
        self.uninitialize_count = 0

    def CoInitialize(self) -> None:
        self.initialize_count += 1

    def CoUninitialize(self) -> None:
        self.uninitialize_count += 1


def _provider(
    *,
    fail: bool = False,
) -> tuple[windows_sapi.WindowsSapiProvider, _FakeCom]:
    tokens = _FakeTokenCollection(
        [
            _FakeToken(
                "token-en-us",
                "Example Voice - English (United States)",
                "409",
            ),
            _FakeToken(
                "token-es-mx",
                "Example Voice - Spanish (Mexico)",
                "80A",
            ),
        ]
    )
    com = _FakeCom()

    def create_object(progid: str):
        if progid == "SAPI.SpVoice":
            return _FakeVoice(tokens, fail=fail)
        if progid == "SAPI.SpFileStream":
            return _FakeStream()
        raise AssertionError(progid)

    return (
        windows_sapi.WindowsSapiProvider(
            object_factory=create_object,
            com_module=com,
        ),
        com,
    )


def test_sapi_voice_metadata_uses_readable_locale_names(monkeypatch) -> None:
    monkeypatch.setattr(windows_sapi.sys, "platform", "win32")
    provider, com = _provider()

    voices = provider.list_voices()

    assert [voice.language_code for voice in voices] == ["en-US", "es-MX"]
    assert voices[0].language_name == "English"
    assert voices[0].country_name == "United States"
    assert voices[1].language_name == "Spanish"
    assert voices[1].country_name == "Mexico"
    assert all(voice.voice_id.startswith("windows_sapi:") for voice in voices)
    assert com.initialize_count == com.uninitialize_count == 1


def test_sapi_voice_ids_are_stable_across_discovery(monkeypatch) -> None:
    monkeypatch.setattr(windows_sapi.sys, "platform", "win32")
    provider, _ = _provider()

    first = [voice.voice_id for voice in provider.list_voices()]
    second = [voice.voice_id for voice in provider.list_voices()]

    assert first == second


def test_sapi_synthesis_writes_valid_wav_and_replaces_output(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(windows_sapi.sys, "platform", "win32")
    provider, _ = _provider()
    voice_id = provider.list_voices()[0].voice_id
    output_path = tmp_path / "nested" / "speech.wav"

    result = provider.synthesize(
        SynthesisRequest(
            text="A short test.",
            request_id="request-1",
            voice_id=voice_id,
            output_path=output_path,
        )
    )

    assert result.audio_path == output_path
    assert output_path.is_file()
    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 22050
        assert wav_file.getnframes() > 0
    assert not list(output_path.parent.glob(".*.wav"))


def test_sapi_synthesis_removes_partial_output_on_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(windows_sapi.sys, "platform", "win32")
    provider, _ = _provider(fail=True)
    voice_id = provider.list_voices()[0].voice_id
    output_path = tmp_path / "failed.wav"

    with pytest.raises(SynthesisFailedError, match="Windows SAPI synthesis failed"):
        provider.synthesize(
            SynthesisRequest(
                text="A failing test.",
                request_id="request-2",
                voice_id=voice_id,
                output_path=output_path,
            )
        )

    assert not output_path.exists()
    assert not list(tmp_path.glob(".*.wav"))


def test_sapi_health_reports_non_windows_without_importing_comtypes(monkeypatch) -> None:
    monkeypatch.setattr(windows_sapi.sys, "platform", "linux")
    provider, _ = _provider()

    health = provider.health()

    assert health.healthy is False
    assert "only on Windows" in (health.details or "")
