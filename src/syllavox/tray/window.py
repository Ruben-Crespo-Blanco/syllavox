"""Main desktop window for entering and speaking text."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from syllavox.constants import (
    DEFAULT_READ_HOTKEY,
    LINUX_ESPEAK_TTS_BACKEND,
    MACOS_SYSTEM_TTS_BACKEND,
    PRODUCT_NAME,
    SHERPA_ONNX_TTS_BACKEND,
    WINDOWS_SAPI_TTS_BACKEND,
)
from syllavox.hotkey.manager import HotkeyStatus
from syllavox.local_data import clear_local_data
from syllavox.logging_config import configure_logging, get_logger, shutdown_logging
from syllavox.qt_bridge import QtCallbackRelay
from syllavox.reading_session import ReadingSession
from syllavox.request_ids import new_request_id
from syllavox.settings import SettingsManager
from syllavox.speech.controller import SpeechController
from syllavox.state import AppState, StateManager, StateSnapshot
from syllavox.text_formatting import normalize_for_speech
from syllavox.tts.base import VoiceInfo
from syllavox.tts.catalog import (
    PiperVoiceCatalog,
    SherpaVoiceCatalog,
    SystemVoiceCatalog,
)
from syllavox.tts.backend_registry import backend_display_name
from syllavox.tts.errors import BackendUnavailableError, TTSBackendError
from syllavox.tts.fallback import SystemVoiceFallbackBackend
from syllavox.tts.manager import TTSBackendManager
from syllavox.tts.paths import get_piper_models_dir, get_sherpa_onnx_models_dir
from syllavox.tray.voice_catalog_dialog import VoiceCatalogDialog
from syllavox.tray.voice_management_dialog import VoiceManagementDialog
from syllavox.tray.window_widgets import (
    OnboardingPanel,
    SAMPLE_TEXT,
    SettingsPanel,
    SpeechEditorWidget,
    VoiceSelectorWidget,
)


DEFAULT_WINDOW_WIDTH = 720
DEFAULT_WINDOW_HEIGHT = 720
MIN_WINDOW_WIDTH = 720
MIN_WINDOW_HEIGHT = 600
MAX_WINDOW_WIDTH = 3000
MAX_WINDOW_HEIGHT = 2000
MAX_CONTENT_WIDTH = 1200


class MainWindow(QMainWindow):
    """Coordinate the desktop UI components and application services."""

    def __init__(
        self,
        state_manager: StateManager,
        settings_manager: SettingsManager,
        backend_manager: TTSBackendManager,
        speech_controller: SpeechController,
        voice_catalog: object | None = None,
    ) -> None:
        super().__init__()

        self._state_manager = state_manager
        self._settings_manager = settings_manager
        self._backend_manager = backend_manager
        self._speech_controller = speech_controller
        if voice_catalog is not None:
            self._voice_catalog = voice_catalog
        elif backend_manager.backend_name() in {
            WINDOWS_SAPI_TTS_BACKEND,
            MACOS_SYSTEM_TTS_BACKEND,
            LINUX_ESPEAK_TTS_BACKEND,
        }:
            self._voice_catalog = SystemVoiceCatalog(
                system_voice_name=backend_display_name(
                    backend_manager.backend_name()
                )
            )
        elif backend_manager.backend_name() == SHERPA_ONNX_TTS_BACKEND:
            self._voice_catalog = SherpaVoiceCatalog(
                backend=backend_manager.active_backend,
                models_dir=get_sherpa_onnx_models_dir(),
            )
        else:
            self._voice_catalog = PiperVoiceCatalog(
                models_dir=get_piper_models_dir()
            )
        self._logger = get_logger(__name__)
        self._voices: list[VoiceInfo] = []
        self._hotkey_reconfigure_callback: Callable[[str], None] | None = None
        self._startup_reconfigure_callback: Callable[[bool], None] | None = None
        self._restart_command: tuple[str, list[str]] | None = None
        self._reading_session: ReadingSession | None = None
        self._reading_request_id: str | None = None
        self._continue_reading_after_completion = False

        self._state_relay = QtCallbackRelay(self._on_state_changed)
        self._state_manager.add_listener(self._state_relay.dispatch)
        self._completion_relay = QtCallbackRelay(self._on_playback_finished)
        self._speech_controller.add_completion_listener(
            self._completion_relay.dispatch
        )

        self.setWindowTitle(PRODUCT_NAME)
        self._set_window_icon()

        self._title_label = QLabel(PRODUCT_NAME)
        self._title_label.setObjectName("pageTitle")
        self._title_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._subtitle_label = QLabel(
            "Hear any desktop text privately—one shortcut, offline, no account."
        )
        self._subtitle_label.setObjectName("pageSubtitle")
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._state_label = QLabel()
        self._state_label.setObjectName("stateLabel")
        self._state_label.setAccessibleName("Application state")
        self._hotkey_status_label = QLabel("Hotkey: not initialized")
        self._hotkey_status_label.setObjectName("hotkeyStatus")
        self._hotkey_status_label.setAccessibleName("Read shortcut status")

        self._onboarding_panel = OnboardingPanel()

        self._voice_selector = VoiceSelectorWidget()
        system_voice_mode = bool(
            getattr(self._voice_catalog, "is_system_voice_catalog", False)
        )
        self._voice_selector.set_system_voice_mode(
            system_voice_mode,
            getattr(
                self._voice_catalog,
                "system_voice_name",
                "the operating system",
            ),
        )
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
        self._navigation_mode_combo = self._speech_editor.navigation_mode_combo
        self._previous_button = self._speech_editor.previous_button
        self._replay_button = self._speech_editor.replay_button
        self._next_button = self._speech_editor.next_button

        self._settings_panel = SettingsPanel(
            active_backend=backend_manager.backend_name(),
        )
        self._start_minimized_checkbox = (
            self._settings_panel.start_minimized_checkbox
        )
        self._run_on_startup_checkbox = (
            self._settings_panel.run_on_startup_checkbox
        )
        self._remember_window_checkbox = (
            self._settings_panel.remember_window_checkbox
        )
        self._max_text_length_spinbox = (
            self._settings_panel.max_text_length_spinbox
        )
        self._hotkey_action_combo = self._settings_panel.hotkey_action_combo
        self._hotkey_edit = self._settings_panel.hotkey_edit
        self._volume_slider = self._settings_panel.volume_slider
        self._volume_value_label = self._settings_panel.volume_value_label
        self._rate_spinbox = self._settings_panel.rate_spinbox
        self._save_settings_button = QPushButton("Save settings")
        self._save_settings_button.setObjectName("primaryButton")
        self._save_settings_button.setMinimumHeight(40)
        self._clear_local_data_button = (
            self._settings_panel.clear_local_data_button
        )
        self._setup_again_button = self._settings_panel.setup_again_button
        self._local_data_cleanup_requested = False

        self._load_settings_into_controls()
        self._load_voices()
        self._restore_reading_session()
        self._refresh_onboarding()
        self._connect_ui_signals()

        header_layout = QHBoxLayout()
        header_icon = QLabel()
        header_icon.setFixedSize(56, 56)
        icon_path = self._bundled_icon_path()
        if icon_path.is_file():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                header_icon.setPixmap(
                    pixmap.scaled(
                        52,
                        52,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

        title_layout = QVBoxLayout()
        eyebrow_label = QLabel("OFFLINE TEXT TO SPEECH")
        eyebrow_label.setObjectName("eyebrowLabel")
        title_layout.addWidget(eyebrow_label)
        title_layout.addWidget(self._title_label)
        title_layout.addWidget(self._subtitle_label)
        header_layout.addWidget(header_icon)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        status_layout = QHBoxLayout()
        status_layout.addWidget(self._state_label)
        status_layout.addWidget(self._hotkey_status_label)

        save_layout = QHBoxLayout()
        save_layout.addStretch()
        save_layout.addWidget(self._save_settings_button)

        page = QWidget()
        page.setObjectName("appPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll_area = QScrollArea(page)
        scroll_area.setObjectName("contentScroll")
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._content_scroll_area = scroll_area

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_content_layout = QVBoxLayout(scroll_content)
        scroll_content_layout.setContentsMargins(0, 0, 0, 0)
        scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        content_column = QWidget()
        content_column.setObjectName("contentColumn")
        content_column.setMaximumWidth(MAX_CONTENT_WIDTH)
        content_column.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        content_layout = QVBoxLayout(content_column)
        content_layout.setContentsMargins(24, 22, 24, 24)
        content_layout.setSpacing(12)
        content_layout.addLayout(header_layout)
        content_layout.addLayout(status_layout)
        content_layout.addWidget(self._onboarding_panel)
        content_layout.addWidget(self._voice_selector)
        content_layout.addWidget(self._speech_editor)
        content_layout.addWidget(self._settings_panel)

        scroll_content_layout.addWidget(content_column)
        scroll_area.setWidget(scroll_content)
        page_layout.addWidget(scroll_area, 1)

        footer_host = QWidget()
        footer_host.setObjectName("appFooterHost")
        footer_host_layout = QHBoxLayout(footer_host)
        footer_host_layout.setContentsMargins(0, 0, 0, 0)
        footer_host_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        footer_column = QWidget()
        footer_column.setObjectName("appFooter")
        footer_column.setMaximumWidth(MAX_CONTENT_WIDTH)
        footer_column.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        save_layout.setContentsMargins(24, 0, 24, 16)
        footer_column.setLayout(save_layout)
        footer_host_layout.addWidget(footer_column)
        page_layout.addWidget(footer_host)

        self.setCentralWidget(page)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

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
        self._previous_button.clicked.connect(lambda: self._navigate_reading(-1))
        self._replay_button.clicked.connect(lambda: self._navigate_reading(0))
        self._next_button.clicked.connect(lambda: self._navigate_reading(1))
        self._navigation_mode_combo.currentIndexChanged.connect(
            self._on_navigation_mode_changed
        )
        self._onboarding_panel.try_sample_requested.connect(
            self._try_onboarding_sample
        )
        self._onboarding_panel.voice_setup_requested.connect(
            self._open_onboarding_voice_setup
        )
        self._onboarding_panel.finish_requested.connect(
            self._finish_onboarding
        )
        self._save_settings_button.clicked.connect(self._save_settings)
        self._settings_panel.hotkey_apply_requested.connect(
            self._save_settings
        )
        self._settings_panel.restart_requested.connect(
            self._restart_application
        )
        self._settings_panel.clear_local_data_requested.connect(
            self._clear_local_data
        )
        self._settings_panel.setup_again_requested.connect(
            self._run_setup_again
        )
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._max_text_length_spinbox.valueChanged.connect(
            self._refresh_text_status
        )
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        self._rate_spinbox.valueChanged.connect(self._on_rate_changed)

    def set_hotkey_reconfigure_callback(
        self,
        callback: Callable[[str], None],
    ) -> None:
        """Connect settings saves to the live global-hotkey manager."""
        self._hotkey_reconfigure_callback = callback

    def set_startup_reconfigure_callback(
        self,
        callback: Callable[[bool], None],
    ) -> None:
        """Connect the startup preference to the live platform integration."""
        self._startup_reconfigure_callback = callback

    @property
    def restart_command(self) -> tuple[str, list[str]] | None:
        """Return the deferred relaunch command requested by the settings UI."""
        return self._restart_command

    @staticmethod
    def _bundled_icon_path() -> Path:
        return Path(__file__).resolve().parent.parent / "assets" / "tray_icon.png"

    def _set_window_icon(self) -> None:
        icon_path = self._bundled_icon_path()
        if icon_path.is_file():
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                self.setWindowIcon(icon)

    def _load_settings_into_controls(self) -> None:
        self._settings_panel.load_settings(self._settings_manager.settings)

    def _restore_reading_session(self) -> None:
        """Restore local editor content and its last navigable position."""
        saved = self._settings_manager.settings.get("reading_session", {})
        text = saved.get("text", "")
        mode = saved.get("mode", "sentence")
        position = saved.get("position", 0)
        if not isinstance(text, str):
            text = ""
        try:
            position = int(position)
        except (TypeError, ValueError):
            position = 0
        self._text_edit.setPlainText(text)
        self._reading_session = ReadingSession(
            text,
            mode=str(mode),  # type: ignore[arg-type]
            position=position,
        )
        self._refresh_reading_display()

    def _save_reading_session(self) -> None:
        """Persist the local editor and position without any remote service."""
        text = self._text_edit.toPlainText()
        session = self._ensure_reading_session()
        current = session.current
        self._settings_manager.settings["reading_session"] = {
            "text": text,
            "position": current.start if current is not None else 0,
            "mode": session.mode,
        }

    def _refresh_onboarding(self) -> None:
        onboarding = self._settings_manager.settings.get("onboarding", {})
        self._onboarding_panel.setVisible(
            not bool(onboarding.get("completed", False))
        )
        self._onboarding_panel.update_status(
            has_voice=self._selected_voice_id() is not None,
            hotkey=self._hotkey_edit.hotkey(),
        )

    def _run_setup_again(self) -> None:
        """Reopen the non-modal setup guidance without discarding user content."""
        self._settings_manager.settings.setdefault("onboarding", {})[
            "completed"
        ] = False
        self._refresh_onboarding()
        self._settings_manager.save()
        self._content_scroll_area.ensureWidgetVisible(self._onboarding_panel)
        self._onboarding_panel.try_sample_button.setFocus()
        self._set_feedback(
            "Quick setup reopened. Your saved text and voice settings were kept."
        )

    def _try_onboarding_sample(self) -> None:
        if self._selected_voice_id() is None:
            self._set_feedback("Choose a voice before trying the sample.")
            return
        self._text_edit.setPlainText(SAMPLE_TEXT)
        self._reading_session = ReadingSession(SAMPLE_TEXT)
        self._refresh_reading_display()
        self._speak_current_segment(continue_reading=True)

    def _open_onboarding_voice_setup(self) -> None:
        if getattr(self._voice_catalog, "is_system_voice_catalog", False):
            self._open_voice_management()
            return
        self._open_voice_catalog()

    def _finish_onboarding(self) -> None:
        if self._selected_voice_id() is None:
            self._set_feedback("Choose a working voice before finishing setup.")
            return
        self._settings_manager.settings.setdefault("onboarding", {})[
            "completed"
        ] = True
        self._save_reading_session()
        self._settings_manager.save()
        self._refresh_onboarding()
        self._set_feedback(
            f"Setup complete. Copy text anywhere and press {self._hotkey_edit.hotkey()}."
        )

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
            self._refresh_onboarding()
            return
        except Exception:
            self._voices = []
            self._voice_selector.set_no_voices()
            self._set_feedback("Voice backend unavailable.")
            self._logger.exception("Unexpected error while loading voices")
            self._refresh_onboarding()
            return

        self._voices = list(voices)

        if not voices:
            self._voice_selector.set_no_voices()
            self._set_feedback("No voices are available.")
            self._refresh_onboarding()
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
        self._refresh_onboarding()

    def _on_voice_changed(self, voice_id: str) -> None:
        del voice_id
        self._set_shared_default_voice()
        self._refresh_onboarding()
        self._refresh_controls()

    def _set_shared_default_voice(self) -> None:
        voice_id = self._selected_voice_id()

        if voice_id is not None:
            self._backend_manager.set_default_voice_id(voice_id)

    def _open_voice_catalog(self) -> None:
        installed_catalog_ids = getattr(
            self._voice_catalog,
            "installed_catalog_ids",
            None,
        )
        if callable(installed_catalog_ids):
            installed_ids = set(installed_catalog_ids())
        else:
            installed_ids = {voice.voice_id for voice in self._voices}

        dialog = VoiceCatalogDialog(
            catalog=self._voice_catalog,
            installed_voice_ids=installed_ids,
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

        active_backend = self._backend_manager.active_backend
        if isinstance(active_backend, SystemVoiceFallbackBackend):
            voices = [
                voice
                for voice in voices
                if active_backend.is_primary_voice(voice.voice_id)
            ]

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
        self._set_feedback(f"Installed voice {voice_id}.")
        self._refresh_onboarding()

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

    def _on_playback_finished(self, request_id: str) -> None:
        """Advance an in-window reading session after natural completion."""
        if request_id != self._reading_request_id:
            return
        self._reading_request_id = None
        session = self._reading_session
        if (
            self._continue_reading_after_completion
            and session is not None
            and session.can_move_next
        ):
            session.move(1)
            self._refresh_reading_display()
            self._speak_current_segment(continue_reading=True)
            return
        self._continue_reading_after_completion = False
        self._save_reading_session()
        self._settings_manager.save()
        self._set_feedback("Reading complete.")
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

    def _on_text_changed(self) -> None:
        if self._state_manager.state in {AppState.SPEAKING, AppState.PAUSED}:
            self._continue_reading_after_completion = False
            self._reading_request_id = None
            try:
                self._speech_controller.stop()
            except Exception as exc:
                self._logger.warning("Could not stop playback after an edit: %s", exc)
        text = self._text_edit.toPlainText()
        mode = self._navigation_mode_combo.currentData() or "sentence"
        self._reading_session = ReadingSession(
            text,
            mode=str(mode),  # type: ignore[arg-type]
            position=self._text_edit.textCursor().position(),
        )
        self._refresh_text_status()

    def _ensure_reading_session(self) -> ReadingSession:
        text = self._text_edit.toPlainText()
        mode = str(self._navigation_mode_combo.currentData() or "sentence")
        if (
            self._reading_session is None
            or self._reading_session.text != text
        ):
            self._reading_session = ReadingSession(
                text,
                mode=mode,  # type: ignore[arg-type]
                position=self._text_edit.textCursor().position(),
            )
        elif self._reading_session.mode != mode:
            self._reading_session.set_mode(mode)  # type: ignore[arg-type]
        return self._reading_session

    def _refresh_reading_display(self) -> None:
        session = self._ensure_reading_session()
        current = session.current
        has_voice = self._selected_voice_id() is not None
        self._speech_editor.set_navigation_state(
            mode=session.mode,
            index=session.index,
            count=session.count,
            previous_enabled=has_voice and session.can_move_previous,
            next_enabled=has_voice and session.can_move_next,
            replay_enabled=has_voice and current is not None,
        )
        self._speech_editor.highlight_range(
            current.start if current is not None else None,
            current.end if current is not None else None,
        )

    def _on_navigation_mode_changed(self, index: int) -> None:
        del index
        session = self._ensure_reading_session()
        mode = str(self._navigation_mode_combo.currentData() or "sentence")
        if self._state_manager.state in {AppState.SPEAKING, AppState.PAUSED}:
            self._continue_reading_after_completion = False
            self._reading_request_id = None
            self._speech_controller.stop()
        session.set_mode(mode)  # type: ignore[arg-type]
        self._refresh_reading_display()
        self._save_reading_session()
        self._settings_manager.save()

    def _navigate_reading(self, offset: int) -> None:
        session = self._ensure_reading_session()
        if session.current is None:
            self._set_feedback("Enter text before using reading navigation.")
            return
        if self._state_manager.state in {AppState.SPEAKING, AppState.PAUSED}:
            self._continue_reading_after_completion = False
            self._reading_request_id = None
            try:
                self._speech_controller.stop()
            except Exception as exc:
                self._set_feedback(f"Could not change reading position: {exc}")
                return
        session.move(offset)
        self._refresh_reading_display()
        self._speak_current_segment(continue_reading=True)

    def _refresh_controls(self) -> None:
        text = self._text_edit.toPlainText()
        formatted_text = normalize_for_speech(text)
        has_text = bool(formatted_text)
        within_limit = (
            len(formatted_text) <= self._max_text_length_spinbox.value()
        )
        session = self._ensure_reading_session()
        current_segment = session.current
        current_within_limit = (
            current_segment is not None
            and len(normalize_for_speech(current_segment.text))
            <= self._max_text_length_spinbox.value()
        )
        has_voice = (
            self._voice_combo.isEnabled()
            and self._selected_voice_id() is not None
        )
        can_speak = (
            has_text
            and current_within_limit
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
            export_enabled=(
                has_text
                and within_limit
                and has_voice
                and self._state_manager.state != AppState.STARTING
            ),
            pause_text=pause_text,
            pause_enabled=pause_enabled,
            stop_enabled=state in {AppState.SPEAKING, AppState.PAUSED},
            clear_enabled=bool(text),
        )
        self._refresh_reading_display()

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
        session = self._ensure_reading_session()
        if session.current is None:
            self._set_feedback("Enter text before starting speech.")
            return
        self._speak_current_segment(continue_reading=True)

    def _speak_current_segment(self, *, continue_reading: bool) -> None:
        session = self._ensure_reading_session()
        segment = session.current
        if segment is None:
            self._set_feedback("Enter text before starting speech.")
            return
        request_id = new_request_id("ui")

        try:
            result = self._speech_controller.speak(
                text=segment.text,
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

        self._reading_request_id = result.request_id
        self._continue_reading_after_completion = continue_reading
        self._refresh_reading_display()
        self._save_reading_session()
        self._settings_manager.save()
        unit = "sentence" if session.mode == "sentence" else "paragraph"
        self._set_feedback(
            f"Reading {unit} {session.index + 1} of {session.count} "
            f"with {result.voice_id}."
        )
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
        self._continue_reading_after_completion = False
        self._reading_request_id = None
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
        if self._state_manager.state in {AppState.SPEAKING, AppState.PAUSED}:
            self._stop_speaking()
        self._text_edit.clear()
        self._reading_session = ReadingSession(
            "",
            mode=str(self._navigation_mode_combo.currentData() or "sentence"),  # type: ignore[arg-type]
        )
        self._save_reading_session()
        self._settings_manager.save()
        self._set_feedback("")

    def _set_feedback(self, message: str) -> None:
        self._speech_editor.set_feedback(message)

    def _save_settings(self) -> bool:
        current_ui_settings = self._settings_manager.settings.get("ui", {})
        current_run_on_startup = bool(
            current_ui_settings.get("run_on_startup", False)
        )
        selected_run_on_startup = self._run_on_startup_checkbox.isChecked()

        if (
            selected_run_on_startup != current_run_on_startup
            and self._startup_reconfigure_callback is not None
        ):
            try:
                self._startup_reconfigure_callback(selected_run_on_startup)
            except Exception as exc:
                self._run_on_startup_checkbox.setChecked(current_run_on_startup)
                self._set_feedback(f"Startup setting was not changed: {exc}")
                self._logger.warning(
                    "Startup registration failed; settings were not saved: %s",
                    exc,
                )
                return False

        current_hotkey = str(
            self._settings_manager.settings.get("hotkey", {}).get(
                "key",
                DEFAULT_READ_HOTKEY,
            )
        )
        selected_hotkey = self._hotkey_edit.hotkey()

        if (
            selected_hotkey != current_hotkey
            and self._hotkey_reconfigure_callback is not None
        ):
            try:
                self._hotkey_reconfigure_callback(selected_hotkey)
            except Exception as exc:
                self._hotkey_edit.set_hotkey(current_hotkey)
                self._set_feedback(f"Hotkey was not changed: {exc}")
                self._logger.warning(
                    "Hotkey reconfiguration failed; settings were not saved: %s",
                    exc,
                )
                return False

        self._write_controls_to_settings()
        self._save_reading_session()
        self._save_window_size_if_enabled()
        self._settings_manager.save()
        backend = self._settings_manager.settings.get("tts", {}).get(
            "backend",
            "piper",
        )
        restart_hint = (
            " Restart Syllavox to apply the speech-engine change."
            if backend != self._backend_manager.backend_name().replace("-", "_")
            else ""
        )
        self._set_feedback(
            f"Settings saved. Read hotkey: {self._hotkey_edit.hotkey()}."
            f"{restart_hint}"
        )
        self._logger.info("Main window settings saved")
        return True

    def _restart_application(self) -> None:
        """Save settings and relaunch Syllavox so the selected backend loads."""
        if not self._save_settings():
            return

        if self._state_manager.state in {AppState.SPEAKING, AppState.PAUSED}:
            try:
                self._speech_controller.stop()
            except Exception as exc:
                self._set_feedback(f"Could not stop playback before restart: {exc}")
                self._logger.exception("Could not stop playback before restart")
                return

        if getattr(sys, "frozen", False):
            executable = os.environ.get("APPIMAGE") or sys.executable
            arguments = list(sys.argv[1:])
        else:
            executable = sys.executable
            arguments = ["-m", "syllavox.main", *sys.argv[1:]]

        self._restart_command = (executable, arguments)
        self._set_feedback("Restarting Syllavox to apply the speech engine…")
        QApplication.instance().quit()

    def _clear_local_data(self) -> None:
        answer = QMessageBox.question(
            self,
            "Clear local data",
            (
                "Delete all Syllavox-managed settings, logs, temporary and "
                "retained audio, downloaded voice models, and language data?\n\n"
                "The application will close after cleanup. WAV files exported "
                "to other locations will not be deleted."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._local_data_cleanup_requested = True

        try:
            if self._state_manager.state in {AppState.SPEAKING, AppState.PAUSED}:
                self._speech_controller.stop()

            for voice_id in self._backend_manager.loaded_voice_ids():
                self._backend_manager.unload_voice(voice_id)
        except Exception as exc:
            self._local_data_cleanup_requested = False
            QMessageBox.critical(
                self,
                "Clear local data failed",
                f"Syllavox could not stop its active resources:\n{exc}",
            )
            return

        shutdown_logging()
        report = clear_local_data()

        if not report.succeeded:
            configure_logging()
            self._local_data_cleanup_requested = False
            QMessageBox.critical(
                self,
                "Clear local data failed",
                (
                    "Some Syllavox data could not be removed. Close any files "
                    f"using the application data directory and try again.\n\n"
                    f"{report.error}"
                ),
            )
            return

        QApplication.instance().quit()

    def _save_window_size_if_enabled(self) -> None:
        settings = self._settings_manager.settings
        window_settings = settings.setdefault("window", {})

        if window_settings.get("remember_position", True):
            window_settings["width"] = self.width()
            window_settings["height"] = self.height()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._local_data_cleanup_requested:
            event.accept()
            return

        self._write_controls_to_settings()
        self._save_reading_session()
        self._save_window_size_if_enabled()
        self._settings_manager.save()
        self._logger.info("Window closed; settings saved")
        event.accept()


__all__ = ["MainWindow"]
