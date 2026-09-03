from __future__ import annotations

import logging
from pathlib import Path

import syllavox.app as app_module
from syllavox.constants import DEFAULT_TTS_BACKEND, WINDOWS_SAPI_TTS_BACKEND
from syllavox.fakes import FakeAudioPlayer, FakeBackend
from syllavox.settings import SettingsManager
from syllavox.state import StateManager
from syllavox.tts.base import VoiceInfo
from syllavox.tts.fallback import SystemVoiceFallbackBackend


class EmptyPiperBackend(FakeBackend):
    def backend_name(self) -> str:
        return DEFAULT_TTS_BACKEND

    def list_voices(self) -> list[VoiceInfo]:
        return []


class FakeSystemBackend(FakeBackend):
    def backend_name(self) -> str:
        return WINDOWS_SAPI_TTS_BACKEND


def test_default_speech_service_adds_available_system_voice_fallback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SYLLAVOX_DATA_DIR", str(tmp_path / "app-data"))
    settings = SettingsManager(tmp_path / "settings.json")
    settings.load()
    primary = EmptyPiperBackend(audio_path=tmp_path / "piper.wav")
    system = FakeSystemBackend(
        audio_path=tmp_path / "system.wav",
        voices=[
            VoiceInfo(
                voice_id="system-voice",
                name="System Voice",
                language="en",
            )
        ],
    )
    monkeypatch.setattr(
        app_module,
        "available_system_backend_id",
        lambda: WINDOWS_SAPI_TTS_BACKEND,
    )
    monkeypatch.setattr(
        app_module,
        "create_backend",
        lambda backend_id: (
            system if backend_id == WINDOWS_SAPI_TTS_BACKEND else primary
        ),
    )

    manager, _ = app_module._create_speech_services(
        settings,
        StateManager(),
        FakeAudioPlayer(),
        logging.getLogger("tests.app.fallback"),
    )

    assert isinstance(manager.active_backend, SystemVoiceFallbackBackend)
    assert [voice.voice_id for voice in manager.list_voices()] == [
        "system-voice"
    ]
