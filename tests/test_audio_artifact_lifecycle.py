from __future__ import annotations

import logging
from pathlib import Path

import pytest
from PySide6.QtMultimedia import QMediaPlayer

from syllavox.audio.errors import PlaybackStartError
from syllavox.audio.player import AudioPlayer
from syllavox.tts.base import AudioRetention


class FakeMediaPlayer:
    def __init__(self) -> None:
        self.state = QMediaPlayer.PlaybackState.StoppedState
        self.error_value = QMediaPlayer.Error.NoError
        self.stop_calls = 0

    def playbackState(self) -> QMediaPlayer.PlaybackState:
        return self.state

    def stop(self) -> None:
        self.stop_calls += 1
        self.state = QMediaPlayer.PlaybackState.StoppedState

    def setSource(self, _url) -> None:
        return None

    def play(self) -> None:
        self.state = QMediaPlayer.PlaybackState.PlayingState

    def pause(self) -> None:
        self.state = QMediaPlayer.PlaybackState.PausedState

    def error(self) -> QMediaPlayer.Error:
        return self.error_value

    def errorString(self) -> str:
        return "fake playback error"


def make_uninitialized_player() -> tuple[AudioPlayer, FakeMediaPlayer]:
    media_player = FakeMediaPlayer()
    player = AudioPlayer.__new__(AudioPlayer)
    player._logger = logging.getLogger("tests.audio_artifact_lifecycle")
    player._on_finished = None
    player._current_request_id = None
    player._current_audio_path = None
    player._current_audio_retention = AudioRetention.TEMPORARY
    player._pending_cleanup_paths = set()
    player._stop_requested = False
    player._volume = 1.0
    player._playback_rate = 1.0
    player._player = media_player
    return player, media_player


def set_current_artifact(
    player: AudioPlayer,
    media_player: FakeMediaPlayer,
    audio_path: Path,
    retention: AudioRetention,
) -> None:
    player._current_request_id = "request-1"
    player._current_audio_path = audio_path
    player._current_audio_retention = retention
    media_player.state = QMediaPlayer.PlaybackState.PlayingState


def test_stop_removes_temporary_audio_artifact(tmp_path: Path) -> None:
    audio_path = tmp_path / "temporary.wav"
    audio_path.write_bytes(b"fake wav")
    player, media_player = make_uninitialized_player()
    set_current_artifact(
        player,
        media_player,
        audio_path,
        AudioRetention.TEMPORARY,
    )

    player.stop()

    assert not audio_path.exists()
    assert media_player.stop_calls == 1


def test_natural_completion_removes_temporary_audio_artifact(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "temporary.wav"
    audio_path.write_bytes(b"fake wav")
    player, media_player = make_uninitialized_player()
    set_current_artifact(
        player,
        media_player,
        audio_path,
        AudioRetention.TEMPORARY,
    )
    media_player.state = QMediaPlayer.PlaybackState.StoppedState

    player._on_playback_state_changed(
        QMediaPlayer.PlaybackState.StoppedState
    )

    assert not audio_path.exists()
    assert player.current_request_id() is None


def test_retained_audio_artifact_survives_stop(tmp_path: Path) -> None:
    audio_path = tmp_path / "retained.wav"
    audio_path.write_bytes(b"fake wav")
    player, media_player = make_uninitialized_player()
    set_current_artifact(
        player,
        media_player,
        audio_path,
        AudioRetention.RETAIN,
    )

    player.stop()

    assert audio_path.exists()


def test_pause_and_resume_keep_temporary_audio_artifact(tmp_path: Path) -> None:
    audio_path = tmp_path / "temporary.wav"
    audio_path.write_bytes(b"fake wav")
    player, media_player = make_uninitialized_player()
    set_current_artifact(
        player,
        media_player,
        audio_path,
        AudioRetention.TEMPORARY,
    )

    player.pause()
    assert player.is_paused() is True
    assert audio_path.exists()

    player.resume()
    assert player.is_playing() is True
    assert audio_path.exists()


def test_playback_start_failure_removes_temporary_audio_artifact(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "failed.wav"
    audio_path.write_bytes(b"fake wav")
    player, media_player = make_uninitialized_player()
    media_player.error_value = QMediaPlayer.Error.ResourceError

    with pytest.raises(PlaybackStartError):
        player.play(audio_path, "request-1")

    assert not audio_path.exists()
    assert player.current_request_id() is None


def test_playback_error_removes_temporary_audio_artifact(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "error.wav"
    audio_path.write_bytes(b"fake wav")
    player, media_player = make_uninitialized_player()
    set_current_artifact(
        player,
        media_player,
        audio_path,
        AudioRetention.TEMPORARY,
    )

    player._on_error_occurred(
        QMediaPlayer.Error.ResourceError,
        "fake playback error",
    )

    assert not audio_path.exists()


def test_locked_audio_artifact_cleanup_is_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio_path = tmp_path / "locked.wav"
    audio_path.write_bytes(b"fake wav")
    player, _ = make_uninitialized_player()

    def fail_unlink(_path: Path, missing_ok: bool = False) -> None:
        raise PermissionError("file is locked")

    monkeypatch.setattr(Path, "unlink", fail_unlink)

    player._cleanup_audio_path(audio_path)

    assert audio_path in player._pending_cleanup_paths

    monkeypatch.undo()
    player._retry_pending_cleanup()

    assert not audio_path.exists()
    assert player._pending_cleanup_paths == set()
