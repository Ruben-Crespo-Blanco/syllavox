from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import syllavox.tray.window as window_module
from syllavox.constants import DEFAULT_MAX_TEXT_LENGTH
from syllavox.fakes import FakeAudioPlayer, FakeBackend
from syllavox.settings import SettingsManager
from syllavox.speech.controller import SpeechController
from syllavox.state import AppState, StateManager
from syllavox.tray.window import MainWindow
from syllavox.tts.base import VoiceInfo
from syllavox.tts.manager import TTSBackendManager


_QT_APP = QApplication.instance() or QApplication([])


class MultiVoiceBackend(FakeBackend):
    def list_voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(
                voice_id="en_US-lessac-medium",
                name="lessac",
                language="en",
                language_code="en_US",
                quality="medium",
            ),
            VoiceInfo(
                voice_id="es_ES-davefx-medium",
                name="davefx",
                language="es",
                language_code="es_ES",
                quality="medium",
            ),
        ]


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return _QT_APP


def make_window(
    tmp_path: Path,
    qt_app: QApplication,
    backend=None,
) -> tuple[MainWindow, SettingsManager, StateManager, object]:
    audio_path = tmp_path / "speech.wav"
    audio_path.write_bytes(b"fake wav")

    settings_manager = SettingsManager(settings_path=tmp_path / "settings.json")
    settings_manager.load()

    state_manager = StateManager()
    state_manager.mark_ready()

    audio_player = FakeAudioPlayer()
    backend = backend or FakeBackend(audio_path=audio_path)
    backend_manager = TTSBackendManager(
        backend=backend,
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )
    speech_controller = SpeechController(
        state_manager=state_manager,
        backend_manager=backend_manager,
        audio_player=audio_player,
        logger=logging.getLogger("tests.window"),
    )

    window = MainWindow(
        state_manager=state_manager,
        settings_manager=settings_manager,
        backend_manager=backend_manager,
        speech_controller=speech_controller,
    )

    del qt_app
    return window, settings_manager, state_manager, backend


def test_window_populates_voice_selector_and_persists_fallback(
    tmp_path: Path,
    qt_app: QApplication,
) -> None:
    window, settings_manager, _, _ = make_window(tmp_path, qt_app)
    window.close()

    settings_manager.settings["tts"]["voice_id"] = "missing-voice"
    settings_manager.save()

    # Recreate the window after changing the saved value to exercise fallback.
    window, settings_manager, _, _ = make_window(tmp_path, qt_app)

    assert window._voice_combo.currentData() == "fake-voice"
    assert window._voice_combo.currentText() == "Fake Voice (en)"

    window._save_settings()
    assert settings_manager.settings["tts"]["voice_id"] == "fake-voice"

    window.close()


def test_window_speak_and_stop_buttons_use_speech_controller(
    tmp_path: Path,
    qt_app: QApplication,
) -> None:
    window, _, state_manager, backend = make_window(tmp_path, qt_app)

    window._text_edit.setPlainText("Hello from the window")
    window._speak_button.click()

    assert state_manager.state == AppState.SPEAKING
    assert backend.synthesis_calls[0].voice_id == "fake-voice"

    window._stop_button.click()
    assert state_manager.state == AppState.STOPPED

    window.close()


def test_window_pause_resume_and_playback_preferences(
    tmp_path: Path,
    qt_app: QApplication,
) -> None:
    window, settings_manager, state_manager, _ = make_window(tmp_path, qt_app)

    window._text_edit.setPlainText("Hello from the window")
    window._speak_button.click()

    window._pause_resume_button.click()
    assert state_manager.state == AppState.PAUSED
    assert window._pause_resume_button.text() == "Resume"

    window._pause_resume_button.click()
    assert state_manager.state == AppState.SPEAKING
    assert window._pause_resume_button.text() == "Pause"

    window._volume_slider.setValue(40)
    window._rate_spinbox.setValue(1.5)

    audio_player = window._speech_controller._audio_player
    assert audio_player.volume() == 0.4
    assert audio_player.playback_rate() == 1.5

    window._save_settings()
    assert settings_manager.settings["playback"] == {
        "volume": 0.4,
        "rate": 1.5,
    }

    window._stop_button.click()
    window.close()


def test_window_exports_wav_without_starting_playback(
    tmp_path: Path,
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, _, state_manager, backend = make_window(tmp_path, qt_app)
    output_without_suffix = tmp_path / "exported-audio"

    monkeypatch.setattr(
        window_module.QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (
            str(output_without_suffix),
            "WAV files (*.wav)",
        ),
    )

    window._text_edit.setPlainText("Hello from the window")
    window._export_button.click()

    output_path = tmp_path / "exported-audio.wav"
    assert output_path.exists()
    assert state_manager.state == AppState.READY
    assert window._speech_controller._audio_player.play_calls == []
    assert backend.synthesis_calls[-1].output_path == output_path
    assert "WAV exported" in window._feedback_label.text()

    window.close()


def test_window_export_cancel_does_not_synthesize(
    tmp_path: Path,
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, _, _, backend = make_window(tmp_path, qt_app)

    monkeypatch.setattr(
        window_module.QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: ("", ""),
    )

    window._text_edit.setPlainText("Hello from the window")
    window._export_button.click()

    assert backend.synthesis_calls == []
    assert window._speech_controller._audio_player.play_calls == []

    window.close()


def test_window_groups_installed_voices_by_locale(
    tmp_path: Path,
    qt_app: QApplication,
) -> None:
    window, _, _, _ = make_window(
        tmp_path,
        qt_app,
        backend=MultiVoiceBackend(audio_path=tmp_path / "speech.wav"),
    )

    model = window._voice_combo.model()

    assert [model.item(index).text() for index in range(model.rowCount())] == [
        "English (en_US)",
        "lessac (en_US)",
        "Spanish (es_ES)",
        "davefx (es_ES)",
    ]

    window.close()


def test_window_voice_selection_updates_shared_default_for_other_paths(
    tmp_path: Path,
    qt_app: QApplication,
) -> None:
    window, _, state_manager, backend = make_window(
        tmp_path,
        qt_app,
        backend=MultiVoiceBackend(audio_path=tmp_path / "speech.wav"),
    )

    window._voice_combo.setCurrentIndex(3)
    assert window._backend_manager.default_voice_id == "es_ES-davefx-medium"

    window._text_edit.setPlainText("Hola")
    window._speak_button.click()

    assert state_manager.state == AppState.SPEAKING
    assert backend.synthesis_calls[0].voice_id == "es_ES-davefx-medium"

    window.close()


def test_window_remains_usable_when_backend_is_unavailable(
    tmp_path: Path,
    qt_app: QApplication,
) -> None:
    window, _, _, _ = make_window(
        tmp_path,
        qt_app,
        backend=FakeBackend(healthy=False),
    )

    assert window._voice_combo.isEnabled() is False
    assert window._voice_combo.currentText() == "No voices available"
    assert window._speak_button.isEnabled() is False
    assert "backend unavailable" in window._feedback_label.text().lower()

    window.close()
