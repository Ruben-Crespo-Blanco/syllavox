from __future__ import annotations

import threading
from pathlib import Path
from threading import Thread

from PySide6.QtCore import QCoreApplication

from syllavox.audio.qt_bridge import QtAudioBridge
from syllavox.qt_bridge import QtCallbackRelay
from syllavox.tts.base import AudioRetention


class RecordingAudioPlayer:
    def __init__(self) -> None:
        self.play_thread_id: int | None = None
        self.stop_thread_id: int | None = None
        self.pause_thread_id: int | None = None
        self.resume_thread_id: int | None = None
        self.volume_thread_id: int | None = None
        self.rate_thread_id: int | None = None
        self._is_playing = False
        self._is_paused = False
        self._current_request_id: str | None = None
        self._volume = 1.0
        self._rate = 1.0

    def play(
        self,
        audio_path: Path,
        request_id: str,
        retention: AudioRetention = AudioRetention.TEMPORARY,
    ) -> None:
        self.play_thread_id = threading.get_ident()
        self._is_playing = True
        self._is_paused = False
        self._current_request_id = request_id

    def stop(self) -> None:
        self.stop_thread_id = threading.get_ident()
        self._is_playing = False
        self._is_paused = False
        self._current_request_id = None

    def is_playing(self) -> bool:
        return self._is_playing

    def is_paused(self) -> bool:
        return self._is_paused

    def pause(self) -> None:
        self.pause_thread_id = threading.get_ident()
        self._is_playing = False
        self._is_paused = True

    def resume(self) -> None:
        self.resume_thread_id = threading.get_ident()
        self._is_playing = True
        self._is_paused = False

    def set_volume(self, volume: float) -> None:
        self.volume_thread_id = threading.get_ident()
        self._volume = volume

    def volume(self) -> float:
        return self._volume

    def set_playback_rate(self, rate: float) -> None:
        self.rate_thread_id = threading.get_ident()
        self._rate = rate

    def playback_rate(self) -> float:
        return self._rate

    def current_request_id(self) -> str | None:
        return self._current_request_id


def get_qt_application() -> QCoreApplication:
    application = QCoreApplication.instance()

    if application is None:
        application = QCoreApplication([])

    return application


def process_until_finished(
    application: QCoreApplication,
    thread: Thread,
) -> None:
    while thread.is_alive():
        application.processEvents()

    thread.join()


def test_audio_bridge_runs_worker_requests_on_qt_thread() -> None:
    application = get_qt_application()
    owner_thread_id = threading.get_ident()
    player = RecordingAudioPlayer()
    bridge = QtAudioBridge(player, command_timeout_seconds=1.0)

    worker = Thread(
        target=lambda: bridge.play(Path("test.wav"), "request-1")
    )
    worker.start()

    process_until_finished(application, worker)

    assert player.play_thread_id == owner_thread_id
    assert bridge.is_playing() is True
    assert bridge.current_request_id() == "request-1"


def test_callback_relay_runs_callback_on_qt_thread() -> None:
    application = get_qt_application()
    owner_thread_id = threading.get_ident()
    received: list[tuple[object, int]] = []
    relay = QtCallbackRelay(
        lambda payload: received.append((payload, threading.get_ident()))
    )

    worker = Thread(target=lambda: relay.dispatch("state-change"))
    worker.start()

    process_until_finished(application, worker)
    application.processEvents()

    assert received == [("state-change", owner_thread_id)]


def test_audio_bridge_forwards_playback_controls_on_qt_thread() -> None:
    application = get_qt_application()
    owner_thread_id = threading.get_ident()
    player = RecordingAudioPlayer()
    bridge = QtAudioBridge(player, command_timeout_seconds=1.0)

    def use_controls() -> None:
        bridge.pause()
        bridge.resume()
        bridge.set_volume(0.4)
        bridge.set_playback_rate(1.5)

    worker = Thread(target=use_controls)
    worker.start()
    process_until_finished(application, worker)

    assert player.pause_thread_id == owner_thread_id
    assert player.resume_thread_id == owner_thread_id
    assert player.volume_thread_id == owner_thread_id
    assert player.rate_thread_id == owner_thread_id
    assert bridge.volume() == 0.4
    assert bridge.playback_rate() == 1.5
