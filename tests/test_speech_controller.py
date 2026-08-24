from __future__ import annotations

import logging
from pathlib import Path

import pytest

from syllavox.audio.errors import AudioFileNotFoundError
from syllavox.constants import DEFAULT_MAX_TEXT_LENGTH
from syllavox.fakes import FakeAudioPlayer, FakeBackend
from syllavox.speech.controller import SpeechController
from syllavox.state import AppState, StateManager
from syllavox.tts.manager import TTSBackendManager


def make_controller(
    tmp_path: Path,
) -> tuple[SpeechController, StateManager, FakeAudioPlayer, FakeBackend]:
    audio_path = tmp_path / "speech.wav"
    audio_path.write_bytes(b"fake wav")

    state_manager = StateManager()
    state_manager.mark_ready()

    backend = FakeBackend(audio_path=audio_path)
    backend_manager = TTSBackendManager(
        backend=backend,
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )
    audio_player = FakeAudioPlayer()
    controller = SpeechController(
        state_manager=state_manager,
        backend_manager=backend_manager,
        audio_player=audio_player,
        logger=logging.getLogger("tests.speech_controller"),
    )

    return controller, state_manager, audio_player, backend


def test_natural_completion_returns_application_to_ready(
    tmp_path: Path,
) -> None:
    controller, state_manager, audio_player, _ = make_controller(tmp_path)
    audio_player.set_finished_callback(controller.handle_playback_finished)

    controller.speak("Hello", "request-1")
    audio_player.simulate_finished("request-1")

    assert state_manager.state == AppState.READY
    assert controller.active_request_id is None


def test_speech_controller_strips_only_outer_whitespace(
    tmp_path: Path,
) -> None:
    controller, _, _, backend = make_controller(tmp_path)

    controller.speak("  First  line\nSecond\tline  ", "request-formatting")

    assert backend.synthesis_calls[-1].text == "First line\nSecond line"


def test_speech_controller_removes_common_markup_and_invisible_characters(
    tmp_path: Path,
) -> None:
    controller, _, _, backend = make_controller(tmp_path)

    controller.speak(
        "  **Hello** <em>world</em>\u200b &amp; friends  ",
        "request-markup",
    )

    assert backend.synthesis_calls[-1].text == "Hello world & friends"


def test_stale_completion_does_not_change_newer_request_state(
    tmp_path: Path,
) -> None:
    controller, state_manager, _, _ = make_controller(tmp_path)

    controller.speak("First", "request-1")
    controller.speak("Second", "request-2")

    controller.handle_playback_finished("request-1")

    assert state_manager.state == AppState.SPEAKING
    assert controller.active_request_id == "request-2"

    controller.handle_playback_finished("request-2")

    assert state_manager.state == AppState.READY
    assert controller.active_request_id is None


def test_stop_handles_request_before_playback_state_reports_playing(
    tmp_path: Path,
) -> None:
    controller, state_manager, audio_player, _ = make_controller(tmp_path)

    controller.speak("Hello", "request-1")
    audio_player._is_playing = False

    stopped = controller.stop()

    assert stopped is True
    assert audio_player.stop_calls == 1
    assert state_manager.state == AppState.STOPPED
    assert controller.active_request_id is None


def test_pause_and_resume_preserve_the_active_request(
    tmp_path: Path,
) -> None:
    controller, state_manager, audio_player, _ = make_controller(tmp_path)

    controller.speak("Hello", "request-1")

    assert controller.pause() is True
    assert state_manager.state == AppState.PAUSED
    assert audio_player.pause_calls == 1
    assert audio_player.current_request_id() == "request-1"

    assert controller.resume() is True
    assert state_manager.state == AppState.SPEAKING
    assert audio_player.resume_calls == 1
    assert controller.active_request_id == "request-1"


def test_stop_can_stop_paused_playback(
    tmp_path: Path,
) -> None:
    controller, state_manager, audio_player, _ = make_controller(tmp_path)

    controller.speak("Hello", "request-1")
    controller.pause()

    assert controller.stop() is True
    assert state_manager.state == AppState.STOPPED
    assert audio_player.stop_calls == 1
    assert controller.active_request_id is None


def test_pause_and_resume_are_idle_safe(tmp_path: Path) -> None:
    controller, _, _, _ = make_controller(tmp_path)

    assert controller.pause() is False
    assert controller.resume() is False


def test_export_wav_does_not_start_playback_or_change_state(
    tmp_path: Path,
) -> None:
    controller, state_manager, audio_player, _ = make_controller(tmp_path)
    output_path = tmp_path / "export.wav"

    result = controller.export_wav(
        text="Hello",
        output_path=output_path,
        request_id="export-1",
    )

    assert result.audio_path == output_path
    assert result.retention.value == "retain"
    assert output_path.exists()
    assert state_manager.state == AppState.READY
    assert audio_player.play_calls == []
    assert controller.active_request_id is None


def test_playback_failure_clears_active_request(
    tmp_path: Path,
) -> None:
    missing_audio_path = tmp_path / "missing.wav"
    state_manager = StateManager()
    state_manager.mark_ready()
    backend_manager = TTSBackendManager(
        backend=FakeBackend(audio_path=missing_audio_path),
        max_text_length=DEFAULT_MAX_TEXT_LENGTH,
    )
    audio_player = FakeAudioPlayer()
    controller = SpeechController(
        state_manager=state_manager,
        backend_manager=backend_manager,
        audio_player=audio_player,
        logger=logging.getLogger("tests.speech_controller"),
    )

    with pytest.raises(AudioFileNotFoundError):
        controller.speak("Hello", "request-1")

    assert state_manager.state == AppState.ERROR
    assert controller.active_request_id is None
