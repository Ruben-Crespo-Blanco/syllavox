"""
Audio playback controller.

Implements local WAV playback using QMediaPlayer.

This module owns playback state but does not own:
- TTS synthesis
- API routing
- application state transitions

Those are wired together at higher layers.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from syllavox.audio.errors import (
    AudioFileNotFoundError,
    PlaybackStartError,
)
from syllavox.audio.artifacts import AudioArtifactCleaner
from syllavox.logging_config import get_logger
from syllavox.tts.base import AudioRetention


PlaybackFinishedCallback = Callable[[str], None]

DEFAULT_PLAYBACK_VOLUME = 1.0
MIN_PLAYBACK_VOLUME = 0.0
MAX_PLAYBACK_VOLUME = 1.0
DEFAULT_PLAYBACK_RATE = 1.0
MIN_PLAYBACK_RATE = 0.5
MAX_PLAYBACK_RATE = 2.0


def normalize_playback_value(
    value: object,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    """Normalize a persisted playback value into its valid range."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default

    return min(maximum, max(minimum, parsed))


class AudioPlayerPort(Protocol):
    """Thread-agnostic playback operations used by speech orchestration."""

    def play(
        self,
        audio_path: Path,
        request_id: str,
        retention: AudioRetention = AudioRetention.TEMPORARY,
    ) -> None:
        ...

    def stop(self) -> None:
        ...

    def is_playing(self) -> bool:
        ...

    def is_paused(self) -> bool:
        ...

    def pause(self) -> None:
        ...

    def resume(self) -> None:
        ...

    def set_volume(self, volume: float) -> None:
        ...

    def volume(self) -> float:
        ...

    def set_playback_rate(self, rate: float) -> None:
        ...

    def playback_rate(self) -> float:
        ...

    def current_request_id(self) -> str | None:
        ...


class AudioPlayer:
    """
    Local audio playback controller.

    Responsibilities:
    - play WAV files
    - stop active playback
    - track current request ID
    - notify when playback naturally finishes
    """

    def __init__(
        self,
        on_finished: PlaybackFinishedCallback | None = None,
        ) -> None:
        self._logger = get_logger(__name__)
        self._on_finished = on_finished

        self._current_request_id: str | None = None
        self._current_audio_path: Path | None = None
        self._current_audio_retention = AudioRetention.TEMPORARY
        self._pending_cleanup_paths: set[Path] = set()
        self._artifact_cleaner = AudioArtifactCleaner(self._logger)
        self._stop_requested = False
        self._volume = DEFAULT_PLAYBACK_VOLUME
        self._playback_rate = DEFAULT_PLAYBACK_RATE

        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(self._volume)
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        self._player.setPlaybackRate(self._playback_rate)

        self._player.playbackStateChanged.connect(
            self._on_playback_state_changed
        )
        self._player.errorOccurred.connect(
            self._on_error_occurred
        )

    def play(
        self,
        audio_path: Path,
        request_id: str,
        retention: AudioRetention = AudioRetention.TEMPORARY,
    ) -> None:
        """
        Play a WAV file.

        If audio is already playing, it is interrupted.
        """
        if not audio_path.exists() or not audio_path.is_file():
            raise AudioFileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        self._retry_pending_cleanup()

        if self.is_playing() or self._current_audio_path is not None:
            self.stop()

        self._stop_requested = False
        self._current_request_id = request_id
        self._current_audio_path = audio_path
        self._current_audio_retention = retention

        url = QUrl.fromLocalFile(str(audio_path))

        try:
            self._player.setSource(url)
            self._player.play()

            if self._player.error() != QMediaPlayer.Error.NoError:
                raise PlaybackStartError(
                    f"Failed to start playback: {self._player.errorString()}"
                )

        except Exception:
            self._current_request_id = None
            self._stop_requested = False
            self._release_current_artifact()
            raise

        self._logger.info(
            "Playback started: request_id=%s audio_path=%s",
            request_id,
            audio_path,
        )

    def stop(self) -> None:
        """
        Stop active playback.

        Safe to call when idle.
        """
        self._retry_pending_cleanup()

        if not self.is_playing() and self._current_audio_path is None:
            self._current_request_id = None
            self._stop_requested = False
            self._release_current_artifact()
            return

        self._stop_requested = True
        stopped_request_id = self._current_request_id

        try:
            self._player.stop()

        finally:
            self._logger.info(
                "Playback stopped: request_id=%s",
                stopped_request_id,
            )

            self._current_request_id = None
            self._stop_requested = False
            self._release_current_artifact()

    def pause(self) -> None:
        """Pause active playback without releasing its temporary artifact."""
        if self._current_request_id is None:
            return

        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()

    def resume(self) -> None:
        """Resume paused playback without restarting the current file."""
        if self._current_request_id is None:
            return

        if self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()

    def is_playing(self) -> bool:
        return (
            self._player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        )

    def current_request_id(self) -> str | None:
        return self._current_request_id

    def set_finished_callback(
        self,
        callback: PlaybackFinishedCallback | None,
    ) -> None:
        """Set the callback invoked after natural playback completion."""
        self._on_finished = callback

    def _on_playback_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        """
        Detect natural playback completion.

        QMediaPlayer enters StoppedState both when playback naturally ends and
        when stop() is called, so _stop_requested distinguishes them.
        """
        if state != QMediaPlayer.PlaybackState.StoppedState:
            return

        if self._current_request_id is None:
            return

        finished_request_id = self._current_request_id

        if self._stop_requested:
            self._stop_requested = False
            return

        self._logger.info(
            "Playback finished: request_id=%s",
            finished_request_id,
        )

        self._current_request_id = None
        self._release_current_artifact()

        if self._on_finished is not None:
            self._on_finished(finished_request_id)

    def _on_error_occurred(
        self,
        error: QMediaPlayer.Error,
        error_string: str,
    ) -> None:
        if error == QMediaPlayer.Error.NoError:
            return

        self._logger.error(
            "Playback error: request_id=%s error=%s message=%s",
            self._current_request_id,
            error,
            error_string,
        )
        self._release_current_artifact()

    def is_paused(self) -> bool:
        return (
            self._player.playbackState()
            == QMediaPlayer.PlaybackState.PausedState
        )

    def set_volume(self, volume: float) -> None:
        if not MIN_PLAYBACK_VOLUME <= volume <= MAX_PLAYBACK_VOLUME:
            raise ValueError("Playback volume must be between 0.0 and 1.0.")

        self._volume = float(volume)
        self._audio_output.setVolume(self._volume)

    def volume(self) -> float:
        return self._volume

    def set_playback_rate(self, rate: float) -> None:
        if not MIN_PLAYBACK_RATE <= rate <= MAX_PLAYBACK_RATE:
            raise ValueError("Playback rate must be between 0.5 and 2.0.")

        self._playback_rate = float(rate)
        self._player.setPlaybackRate(self._playback_rate)

    def playback_rate(self) -> float:
        return self._playback_rate

    def _release_current_artifact(self) -> None:
        """Release the current audio artifact and clean it up when temporary."""
        audio_path = self._current_audio_path
        retention = self._current_audio_retention

        self._current_audio_path = None
        self._current_audio_retention = AudioRetention.TEMPORARY

        if audio_path is None or retention != AudioRetention.TEMPORARY:
            return

        self._unload_media_source()
        self._cleanup_audio_path(audio_path)

    def _unload_media_source(self) -> None:
        """Release QMediaPlayer's file handle before deleting its source."""
        try:
            self._player.setSource(QUrl())
        except Exception as exc:
            self._logger.warning(
                "Could not unload the completed audio source before cleanup: %s",
                exc,
            )

    def _cleanup_audio_path(self, audio_path: Path) -> None:
        """Delete a temporary audio file or defer cleanup if it is locked."""
        self._get_artifact_cleaner().cleanup(
            audio_path,
            self._pending_cleanup_paths,
        )

    def _retry_pending_cleanup(self) -> None:
        """Retry temporary-file cleanup during later playback lifecycle events."""
        self._get_artifact_cleaner().retry_pending(
            self._pending_cleanup_paths,
        )

    def _get_artifact_cleaner(self) -> AudioArtifactCleaner:
        """Return the cleaner, including for lightweight test instances."""
        cleaner = getattr(self, "_artifact_cleaner", None)
        if cleaner is None:
            cleaner = AudioArtifactCleaner(self._logger)
            self._artifact_cleaner = cleaner
        return cleaner
