"""Qt-thread bridge for playback operations."""

from __future__ import annotations

from concurrent.futures import Future, TimeoutError
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal

from syllavox.audio.errors import PlaybackError
from syllavox.audio.player import AudioPlayerPort
from syllavox.tts.base import AudioRetention


DEFAULT_COMMAND_TIMEOUT_SECONDS = 5.0


class QtAudioBridge(QObject):
    """
    Expose playback operations safely from non-Qt threads.

    Calls made on the owning Qt thread execute directly. Calls made from a
    different thread are queued and wait for a bounded result, preserving the
    synchronous ``AudioPlayerPort`` contract used by ``SpeechController``.
    """

    _play_requested = Signal(object, str, object, object)
    _stop_requested = Signal(object)
    _is_playing_requested = Signal(object)
    _is_paused_requested = Signal(object)
    _current_request_id_requested = Signal(object)
    _pause_requested = Signal(object)
    _resume_requested = Signal(object)
    _set_volume_requested = Signal(float, object)
    _volume_requested = Signal(object)
    _set_playback_rate_requested = Signal(float, object)
    _playback_rate_requested = Signal(object)

    def __init__(
        self,
        player: AudioPlayerPort,
        command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__()
        self._player = player
        self._command_timeout_seconds = command_timeout_seconds

        self._play_requested.connect(
            self._play_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._stop_requested.connect(
            self._stop_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._is_playing_requested.connect(
            self._is_playing_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._is_paused_requested.connect(
            self._is_paused_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._current_request_id_requested.connect(
            self._current_request_id_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._pause_requested.connect(
            self._pause_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._resume_requested.connect(
            self._resume_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._set_volume_requested.connect(
            self._set_volume_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._volume_requested.connect(
            self._volume_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._set_playback_rate_requested.connect(
            self._set_playback_rate_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._playback_rate_requested.connect(
            self._playback_rate_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )

    def play(
        self,
        audio_path: Path,
        request_id: str,
        retention: AudioRetention = AudioRetention.TEMPORARY,
    ) -> None:
        if self._on_qt_thread():
            self._player.play(audio_path, request_id, retention)
            return

        future: Future[None] = Future()
        self._play_requested.emit(audio_path, request_id, retention, future)
        self._wait_for_result(future, "start playback")

    def stop(self) -> None:
        if self._on_qt_thread():
            self._player.stop()
            return

        future: Future[None] = Future()
        self._stop_requested.emit(future)
        self._wait_for_result(future, "stop playback")

    def is_playing(self) -> bool:
        if self._on_qt_thread():
            return self._player.is_playing()

        future: Future[bool] = Future()
        self._is_playing_requested.emit(future)
        return bool(self._wait_for_result(future, "query playback state"))

    def current_request_id(self) -> str | None:
        if self._on_qt_thread():
            return self._player.current_request_id()

        future: Future[str | None] = Future()
        self._current_request_id_requested.emit(future)
        return self._wait_for_result(future, "query current request")

    def is_paused(self) -> bool:
        if self._on_qt_thread():
            return self._player.is_paused()

        future: Future[bool] = Future()
        self._is_paused_requested.emit(future)
        return bool(self._wait_for_result(future, "query paused state"))

    def pause(self) -> None:
        if self._on_qt_thread():
            self._player.pause()
            return

        future: Future[None] = Future()
        self._pause_requested.emit(future)
        self._wait_for_result(future, "pause playback")

    def resume(self) -> None:
        if self._on_qt_thread():
            self._player.resume()
            return

        future: Future[None] = Future()
        self._resume_requested.emit(future)
        self._wait_for_result(future, "resume playback")

    def set_volume(self, volume: float) -> None:
        if self._on_qt_thread():
            self._player.set_volume(volume)
            return

        future: Future[None] = Future()
        self._set_volume_requested.emit(volume, future)
        self._wait_for_result(future, "set playback volume")

    def volume(self) -> float:
        if self._on_qt_thread():
            return self._player.volume()

        future: Future[float] = Future()
        self._volume_requested.emit(future)
        return float(self._wait_for_result(future, "query playback volume"))

    def set_playback_rate(self, rate: float) -> None:
        if self._on_qt_thread():
            self._player.set_playback_rate(rate)
            return

        future: Future[None] = Future()
        self._set_playback_rate_requested.emit(rate, future)
        self._wait_for_result(future, "set playback rate")

    def playback_rate(self) -> float:
        if self._on_qt_thread():
            return self._player.playback_rate()

        future: Future[float] = Future()
        self._playback_rate_requested.emit(future)
        return float(
            self._wait_for_result(future, "query playback rate")
        )

    def _on_qt_thread(self) -> bool:
        return QThread.currentThread() == self.thread()

    def _wait_for_result(self, future: Future, operation: str):
        try:
            return future.result(timeout=self._command_timeout_seconds)

        except TimeoutError as exc:
            raise PlaybackError(
                f"Timed out waiting for Qt to {operation}."
            ) from exc

    def _complete(self, future: Future, operation) -> None:
        try:
            future.set_result(operation())
        except Exception as exc:
            future.set_exception(exc)

    def _play_on_qt_thread(
        self,
        audio_path: Path,
        request_id: str,
        retention: AudioRetention,
        future: Future,
    ) -> None:
        self._complete(
            future,
            lambda: self._player.play(audio_path, request_id, retention),
        )

    def _stop_on_qt_thread(self, future: Future) -> None:
        self._complete(future, self._player.stop)

    def _is_playing_on_qt_thread(self, future: Future) -> None:
        self._complete(future, self._player.is_playing)

    def _current_request_id_on_qt_thread(self, future: Future) -> None:
        self._complete(future, self._player.current_request_id)

    def _is_paused_on_qt_thread(self, future: Future) -> None:
        self._complete(future, self._player.is_paused)

    def _pause_on_qt_thread(self, future: Future) -> None:
        self._complete(future, self._player.pause)

    def _resume_on_qt_thread(self, future: Future) -> None:
        self._complete(future, self._player.resume)

    def _set_volume_on_qt_thread(self, volume: float, future: Future) -> None:
        self._complete(future, lambda: self._player.set_volume(volume))

    def _volume_on_qt_thread(self, future: Future) -> None:
        self._complete(future, self._player.volume)

    def _set_playback_rate_on_qt_thread(
        self,
        rate: float,
        future: Future,
    ) -> None:
        self._complete(future, lambda: self._player.set_playback_rate(rate))

    def _playback_rate_on_qt_thread(self, future: Future) -> None:
        self._complete(future, self._player.playback_rate)
