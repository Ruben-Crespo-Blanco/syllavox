"""Main desktop window for entering and speaking text."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from syllavox.constants import PRODUCT_NAME
from syllavox.hotkey.manager import HotkeyStatus
from syllavox.logging_config import get_logger
from syllavox.qt_bridge import QtCallbackRelay
from syllavox.request_ids import new_request_id
from syllavox.settings import SettingsManager
from syllavox.speech.controller import SpeechController
from syllavox.state import AppState, StateManager, StateSnapshot
from syllavox.tts.base import VoiceInfo
from syllavox.tts.catalog import PiperVoiceCatalog
from syllavox.tts.errors import BackendUnavailableError, TTSBackendError
from syllavox.tts.manager import TTSBackendManager
from syllavox.tts.paths import get_piper_models_dir
from syllavox.tray.voice_catalog_dialog import VoiceCatalogDialog
from syllavox.tray.voice_management_dialog import VoiceManagementDialog
from syllavox.tray.window_widgets import (
    SettingsPanel,
    SpeechEditorWidget,
    VoiceSelectorWidget,
)


DEFAULT_WINDOW_WIDTH = 640
DEFAULT_WINDOW_HEIGHT = 520
MIN_WINDOW_WIDTH = 320
MIN_WINDOW_HEIGHT = 240
MAX_WINDOW_WIDTH = 3000
MAX_WINDOW_HEIGHT = 2000


class MainWindow(QMainWindow):
    """Coordinate the desktop UI components and application services."""

    def __init__(
        self,
        state_manager: StateManager,
        settings_manager: SettingsManager,
        backend_manager: TTSBackendManager,
        speech_controller: SpeechController,
        voice_catalog: PiperVoiceCatalog | None = None,
    ) -> None:
        super().__init__()

        self._state_manager = state_manager
        self._settings_manager = settings_manager
        self._backend_manager = backend_manager
        self._speech_controller = speech_controller
        self._voice_catalog = voice_catalog or PiperVoiceCatalog(
            models_dir=get_piper_models_dir()
        )
        self._logger = get_logger(__name__)
        self._voices: list[VoiceInfo] = []

        self._state_relay = QtCallbackRelay(self._on_state_changed)
        self._state_manager.add_listener(self._state_relay.dispatch)

        self.setWindowTitle(PRODUCT_NAME)

        self._title_label = QLabel(PRODUCT_NAME)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._state_label = QLabel()
        self._hotkey_status_label = QLabel("Hotkey: not initialized")

        self._voice_selector = VoiceSelectorWidget()
        self._voice_combo = self._voice_selector.combo
        self._find_voices_button = self._voice_selector.find_button
        self._manage_voices_button = self._voice_selector.manage_button

        self._speech_editor = SpeechEditorWidget()
        self._text_edit = self._speech_editor.text_edit
        self._character_count_label = self._speech_editor.character_count_label
        self._speak_button = self._speech_editor.speak_button
        self._export_button = self._speech_editor.export_button
        self._pause_resume_button = self._speech_editor.pause_resume_button
        self._stop_button = self._speech_editor.stop_button
        self._clear_button = self._speech_editor.clear_button
        self._feedback_label = self._speech_editor.feedback_label

        self._settings_panel = SettingsPanel()
        self._start_minimized_checkbox = (
            self._settings_panel.start_minimized_checkbox
        )
        self._remember_window_checkbox = (
            self._settings_panel.remember_window_checkbox
        )
        self._max_text_length_spinbox = (
            self._settings_panel.max_text_length_spinbox
        )
        self._hotkey_action_combo = self._settings_panel.hotkey_action_combo
        self._volume_slider = self._settings_panel.volume_slider
        self._volume_value_label = self._settings_panel.volume_value_label
        self._rate_spinbox = self._settings_panel.rate_spinbox
        self._save_settings_button = QPushButton("Save settings")

        self._load_settings_into_controls()
        self._load_voices()
        self._connect_ui_signals()

        layout = QVBoxLayout()
        layout.addWidget(self._title_label)
        layout.addWidget(self._state_label)
        layout.addWidget(self._hotkey_status_label)
        layout.addWidget(self._voice_selector)
        layout.addWidget(self._speech_editor)
        layout.addWidget(self._settings_panel)
        layout.addWidget(self._save_settings_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._restore_window_size()
        self.refresh_state_display()

    def _connect_ui_signals(self) -> None:
        """Connect component events to application actions."""
        self._voice_selector.find_voices_requested.connect(
            self._open_voice_catalog
        )
        self._voice_selector.manage_voices_requested.connect(
            self._open_voice_management
        )
        self._voice_selector.voice_changed.connect(self._on_voice_changed)

        self._speak_button.clicked.connect(self._speak_text)
        self._export_button.clicked.connect(self._export_wav)
        self._pause_resume_button.clicked.connect(self._pause_or_resume)
        self._stop_button.clicked.connect(self._stop_speaking)
        self._clear_button.clicked.connect(self._clear_text)
        self._save_settings_button.clicked.connect(self._save_settings)
        self._text_edit.textChanged.connect(self._refresh_text_status)
        self._max_text_length_spinbox.valueChanged.connect(
            self._refresh_text_status
        )
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        self._rate_spinbox.valueChanged.connect(self._on_rate_changed)

    def _load_settings_into_controls(self) -> None:
        self._settings_panel.load_settings(self._settings_manager.settings)

    def _load_voices(self) -> None:
        """Populate the selector, leaving the window usable if Piper is down."""
        tts_settings = self._settings_manager.settings.get("tts", {})
        saved_voice_id = tts_settings.get("voice_id")

        try:
            voices = self._backend_manager.list_voices()
        except (BackendUnavailableError, TTSBackendError) as exc:
            self._voices = []
            self._voice_selector.set_no_voices()
            self._set_feedback(f"Voice backend unavailable: {exc}")
            self._logger.warning(
                "Could not load voices for the main window: %s",
                exc,
            )
            return
        except Exception:
            self._voices = []
            self._voice_selector.set_no_voices()
            self._set_feedback("Voice backend unavailable.")
            self._logger.exception("Unexpected error while loading voices")
            return

        self._voices = list(voices)

        if not voices:
            self._voice_selector.set_no_voices()
            self._set_feedback("No voices are available.")
            return

        selected_voice_id = self._voice_selector.set_voices(
            self._voices,
            saved_voice_id,
        )

        if (
            saved_voice_id
            and selected_voice_id != saved_voice_id
        ):
            self._set_feedback(
                "Saved voice was unavailable; using the first voice."
            )

        self._set_shared_default_voice()

    def _on_voice_changed(self, voice_id: str) -> None:
        del voice_id
        self._set_shared_default_voice()
        self._refresh_controls()

    def _set_shared_default_voice(self) -> None:
        voice_id = self._selected_voice_id()

        if voice_id is not None:
            self._backend_manager.set_default_voice_id(voice_id)

    def _open_voice_catalog(self) -> None:
        dialog = VoiceCatalogDialog(
            catalog=self._voice_catalog,
            installed_voice_ids={voice.voice_id for voice in self._voices},
            on_voice_installed=self._on_voice_installed,
            logger=self._logger,
            parent=self,
        )
        dialog.exec()

    def _open_voice_management(self) -> None:
        try:
            voices = self._backend_manager.list_voices()
        except (BackendUnavailableError, TTSBackendError) as exc:
            self._set_feedback(f"Voice backend unavailable: {exc}")
            voices = []

        dialog = VoiceManagementDialog(
            catalog=self._voice_catalog,
            backend_manager=self._backend_manager,
            state_manager=self._state_manager,
            voices=voices,
            current_voice_callback=self._selected_voice_id,
            on_voices_changed=self._on_voice_resources_changed,
            logger=self._logger,
            parent=self,
        )
        dialog.exec()

    def _on_voice_installed(self, voice_id: str) -> None:
        self._load_voices()
        self._set_feedback(f"Installed Piper voice {voice_id}.")

    def _on_voice_resources_changed(self) -> None:
        self._load_voices()
        self._write_controls_to_settings()
        self._settings_manager.save()

    def _selected_voice_id(self) -> str | None:
        return self._voice_selector.selected_voice_id()

    def _write_controls_to_settings(self) -> None:
        self._settings_panel.write_settings(
            self._settings_manager.settings,
            voice_id=self._selected_voice_id(),
        )

    def _restore_window_size(self) -> None:
        settings = self._settings_manager.settings
        window_settings = settings.setdefault("window", {})

        width = window_settings.get("width", DEFAULT_WINDOW_WIDTH)
        height = window_settings.get("height", DEFAULT_WINDOW_HEIGHT)

        try:
            width = int(width)
            height = int(height)
        except (TypeError, ValueError):
            width = DEFAULT_WINDOW_WIDTH
            height = DEFAULT_WINDOW_HEIGHT
            window_settings["width"] = width
            window_settings["height"] = height
            self._logger.warning("Invalid window geometry type; reset to defaults")

        if not (
            MIN_WINDOW_WIDTH <= width <= MAX_WINDOW_WIDTH
            and MIN_WINDOW_HEIGHT <= height <= MAX_WINDOW_HEIGHT
        ):
            width = DEFAULT_WINDOW_WIDTH
            height = DEFAULT_WINDOW_HEIGHT
            window_settings["width"] = width
            window_settings["height"] = height
            self._logger.warning("Invalid window geometry range; reset to defaults")

        self.resize(width, height)

    def refresh_state_display(self) -> None:
        state = self._state_manager.state.value
        error = self._state_manager.error_message

        if error:
            self._state_label.setText(f"State: {state} | Error: {error}")
        else:
            self._state_label.setText(f"State: {state}")

        self._refresh_controls()

    def _on_state_changed(self, snapshot: StateSnapshot) -> None:
        del snapshot
        self.refresh_state_display()

    def update_hotkey_status(self, status: HotkeyStatus) -> None:
        """Update the hotkey status shown in the main window."""
        if not status.enabled:
            text = "Hotkey: disabled"
        elif status.registered:
            text = f"Hotkey: {status.key} registered"
        else:
            reason = status.message or "registration failed"
            text = f"Hotkey: failed — {reason}"

        self._hotkey_status_label.setText(text)

    def _refresh_text_status(self) -> None:
        maximum = self._max_text_length_spinbox.value()
        self._speech_editor.update_character_count(maximum)
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        text = self._text_edit.toPlainText()
        has_text = bool(text.strip())
        within_limit = len(text.strip()) <= self._max_text_length_spinbox.value()
        has_voice = (
            self._voice_combo.isEnabled()
            and self._selected_voice_id() is not None
        )
        can_speak = (
            has_text
            and within_limit
            and has_voice
            and self._state_manager.state != AppState.STARTING
        )
        state = self._state_manager.state

        if state == AppState.SPEAKING:
            pause_text = "Pause"
            pause_enabled = True
        elif state == AppState.PAUSED:
            pause_text = "Resume"
            pause_enabled = True
        else:
            pause_text = "Pause"
            pause_enabled = False

        self._speech_editor.set_playback_controls(
            speak_enabled=can_speak,
            export_enabled=can_speak,
            pause_text=pause_text,
            pause_enabled=pause_enabled,
            stop_enabled=state in {AppState.SPEAKING, AppState.PAUSED},
            clear_enabled=bool(text),
        )

    def _on_volume_changed(self, value: int) -> None:
        volume = value / 100
        self._volume_value_label.setText(f"{value}%")

        try:
            self._speech_controller.set_volume(volume)
        except Exception as exc:
            self._logger.warning("Could not set playback volume: %s", exc)

    def _on_rate_changed(self, rate: float) -> None:
        try:
            self._speech_controller.set_playback_rate(rate)
        except Exception as exc:
            self._logger.warning("Could not set playback rate: %s", exc)

    def _pause_or_resume(self) -> None:
        try:
            if self._state_manager.state == AppState.SPEAKING:
                changed = self._speech_controller.pause()
                message = "Playback paused." if changed else "No active playback."
            elif self._state_manager.state == AppState.PAUSED:
                changed = self._speech_controller.resume()
                message = "Playback resumed." if changed else "Playback is not paused."
            else:
                message = "No active playback."
        except Exception as exc:
            self._set_feedback(f"Could not change playback: {exc}")
            self._logger.exception("UI pause/resume failed")
            self.refresh_state_display()
            return

        self._set_feedback(message)
        self.refresh_state_display()

    def _speak_text(self) -> None:
        text = self._text_edit.toPlainText()
        request_id = new_request_id("ui")

        try:
            result = self._speech_controller.speak(
                text=text,
                request_id=request_id,
                voice_id=self._selected_voice_id(),
            )
        except Exception as exc:
            self._set_feedback(f"Could not speak text: {exc}")
            self._logger.exception(
                "UI speech request failed: request_id=%s",
                request_id,
            )
            self.refresh_state_display()
            return

        self._set_feedback(f"Speaking with {result.voice_id}.")
        self.refresh_state_display()

    def _export_wav(self) -> None:
        text = self._text_edit.toPlainText()
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export WAV",
            "",
            "WAV files (*.wav)",
        )

        if not selected_path:
            return

        output_path = Path(selected_path)
        if output_path.suffix.lower() != ".wav":
            output_path = output_path.with_suffix(".wav")

        request_id = new_request_id("export")

        try:
            result = self._speech_controller.export_wav(
                text=text,
                output_path=output_path,
                request_id=request_id,
                voice_id=self._selected_voice_id(),
            )
        except Exception as exc:
            self._set_feedback(f"Could not export WAV: {exc}")
            self._logger.exception(
                "WAV export failed: request_id=%s",
                request_id,
            )
            return

        self._set_feedback(f"WAV exported to {result.audio_path}.")

    def _stop_speaking(self) -> None:
        try:
            stopped = self._speech_controller.stop()
        except Exception as exc:
            self._set_feedback(f"Could not stop playback: {exc}")
            self._logger.exception("UI playback stop failed")
            self.refresh_state_display()
            return

        self._set_feedback(
            "Playback stopped." if stopped else "No active playback."
        )
        self.refresh_state_display()

    def _clear_text(self) -> None:
        self._text_edit.clear()
        self._set_feedback("")

    def _set_feedback(self, message: str) -> None:
        self._speech_editor.set_feedback(message)

    def _save_settings(self) -> None:
        self._write_controls_to_settings()
        self._save_window_size_if_enabled()
        self._settings_manager.save()
        self._set_feedback("Settings saved.")
        self._logger.info("Main window settings saved")

    def _save_window_size_if_enabled(self) -> None:
        settings = self._settings_manager.settings
        window_settings = settings.setdefault("window", {})

        if window_settings.get("remember_position", True):
            window_settings["width"] = self.width()
            window_settings["height"] = self.height()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._write_controls_to_settings()
        self._save_window_size_if_enabled()
        self._settings_manager.save()
        self._logger.info("Window closed; settings saved")
        event.accept()


__all__ = ["MainWindow"]
