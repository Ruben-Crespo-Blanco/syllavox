from __future__ import annotations

import logging
import os
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from syllavox.fakes import FakeBackend
from syllavox.state import StateManager
from syllavox.tray.voice_management_dialog import VoiceManagementDialog
from syllavox.tts.base import VoiceInfo
from syllavox.tts.catalog import PiperVoiceCatalog
from syllavox.tts.fallback import SystemVoiceFallbackBackend
from syllavox.tts.manager import TTSBackendManager


_QT_APP = QApplication.instance() or QApplication([])


def _wait_for(predicate) -> None:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        _QT_APP.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    _QT_APP.processEvents()
    assert predicate()


def _make_dialog(tmp_path: Path):
    voice = VoiceInfo(
        voice_id="en_US-lessac-medium",
        name="lessac",
        language="en",
        language_code="en_US",
        language_name="English",
        country_name="United States",
        quality="medium",
    )
    (tmp_path / f"{voice.voice_id}.onnx").write_bytes(b"model")
    (tmp_path / f"{voice.voice_id}.onnx.json").write_bytes(b"config")

    backend_manager = TTSBackendManager(
        backend=FakeBackend(voices=[voice]),
    )
    state_manager = StateManager()
    state_manager.mark_ready()
    dialog = VoiceManagementDialog(
        catalog=PiperVoiceCatalog(tmp_path),
        backend_manager=backend_manager,
        state_manager=state_manager,
        voices=[voice],
        current_voice_callback=lambda: voice.voice_id,
        on_voices_changed=lambda: None,
        logger=logging.getLogger("tests.voice_management_dialog"),
    )
    return dialog, backend_manager, voice


def test_dialog_loads_and_unloads_voice_through_background_operation(
    tmp_path: Path,
) -> None:
    dialog, backend_manager, voice = _make_dialog(tmp_path)

    dialog._load_button.click()
    _wait_for(lambda: backend_manager.is_voice_loaded(voice.voice_id))
    assert dialog._unload_button.isEnabled() is True

    dialog._unload_button.click()
    _wait_for(lambda: not backend_manager.is_voice_loaded(voice.voice_id))
    assert dialog._load_button.isEnabled() is True
    assert dialog._status_label.text() == "Voice resources updated."

    dialog.close()


def test_dialog_deletes_voice_files_through_background_operation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dialog, backend_manager, voice = _make_dialog(tmp_path)
    backend_manager.load_voice(voice.voice_id)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    dialog._delete_button.click()
    model_path = tmp_path / f"{voice.voice_id}.onnx"
    config_path = tmp_path / f"{voice.voice_id}.onnx.json"
    _wait_for(
        lambda: (
            not model_path.exists()
            and not config_path.exists()
            and dialog._worker is None
        )
    )

    assert not backend_manager.is_voice_loaded(voice.voice_id)
    assert dialog._status_label.text() == "Voice resources updated."

    dialog.close()


def test_dialog_never_allows_deleting_a_system_owned_voice(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_voice = VoiceInfo(
        voice_id="local-voice",
        name="Local",
        language="en",
    )
    system_voice = VoiceInfo(
        voice_id="system-voice",
        name="System",
        language="en",
    )
    primary = FakeBackend(voices=[local_voice])
    system = FakeBackend(voices=[system_voice])
    backend = SystemVoiceFallbackBackend(primary, system)
    backend_manager = TTSBackendManager(backend=backend)
    state_manager = StateManager()
    state_manager.mark_ready()
    dialog = VoiceManagementDialog(
        catalog=PiperVoiceCatalog(tmp_path),
        backend_manager=backend_manager,
        state_manager=state_manager,
        voices=[system_voice],
        current_voice_callback=lambda: system_voice.voice_id,
        on_voices_changed=lambda: None,
        logger=logging.getLogger("tests.voice_management_dialog.system"),
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: pytest.fail("system voice should not prompt for deletion"),
    )

    assert dialog._delete_button.isEnabled() is False
    dialog._delete_selected()
    assert "managed by the operating system" in dialog._status_label.text()
    dialog.close()
