"""Reusable widgets used by the main Syllavox window.

The main window coordinates application services and user actions.  These
widgets own the presentation details for the voice selector, speech editor,
and settings panel so a future UI redesign can replace each area separately.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QStandardItem,
    QStandardItemModel,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from syllavox.audio.player import (
    DEFAULT_PLAYBACK_RATE,
    DEFAULT_PLAYBACK_VOLUME,
    MAX_PLAYBACK_RATE,
    MIN_PLAYBACK_RATE,
    normalize_playback_value,
)
from syllavox.constants import (
    DEFAULT_MAX_TEXT_LENGTH,
    DEFAULT_READ_HOTKEY,
    DEFAULT_TTS_BACKEND,
    LINUX_ESPEAK_TTS_BACKEND,
    MAX_CONFIGURABLE_TEXT_LENGTH,
    MACOS_SYSTEM_TTS_BACKEND,
    SHERPA_ONNX_TTS_BACKEND,
    WINDOWS_SAPI_TTS_BACKEND,
)
from syllavox.hotkey.errors import HotkeyRegistrationError
from syllavox.hotkey.parser import hotkey_hint, parse_hotkey
from syllavox.startup import is_startup_supported, startup_platform_name
from syllavox.text_formatting import normalize_for_speech
from syllavox.tts.base import VoiceInfo
from syllavox.tts.backend_registry import (
    backend_descriptors,
    backend_display_name,
    normalize_backend_id,
)
from syllavox.tts.catalog import format_language_label


_SPECIAL_KEY_NAMES = {
    Qt.Key.Key_Backspace.value: "Backspace",
    Qt.Key.Key_Tab.value: "Tab",
    Qt.Key.Key_Return.value: "Enter",
    Qt.Key.Key_Enter.value: "Enter",
    Qt.Key.Key_Escape.value: "Escape",
    Qt.Key.Key_Space.value: "Space",
    Qt.Key.Key_PageUp.value: "PageUp",
    Qt.Key.Key_PageDown.value: "PageDown",
    Qt.Key.Key_End.value: "End",
    Qt.Key.Key_Home.value: "Home",
    Qt.Key.Key_Left.value: "Left",
    Qt.Key.Key_Up.value: "Up",
    Qt.Key.Key_Right.value: "Right",
    Qt.Key.Key_Down.value: "Down",
    Qt.Key.Key_Insert.value: "Insert",
    Qt.Key.Key_Delete.value: "Delete",
}

SAMPLE_TEXT = (
    "Welcome to Syllavox. Select or copy text, then use your read shortcut "
    "to hear it locally."
)


class OnboardingPanel(QGroupBox):
    """Guide a new user to a successful first reading without a modal wizard."""

    try_sample_requested = Signal()
    voice_setup_requested = Signal()
    finish_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Quick setup", parent)
        self.setObjectName("onboardingCard")
        self.setAccessibleName("Syllavox quick setup")

        intro = QLabel(
            "Hear your first text in three steps: choose an available voice, "
            "try the sample, then test the read shortcut shown below."
        )
        intro.setWordWrap(True)

        self.status_label = QLabel()
        self.status_label.setObjectName("onboardingStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName("Quick setup status")

        self.voice_setup_button = QPushButton("Choose an offline voice…")
        self.try_sample_button = QPushButton("Try the sample")
        self.finish_button = QPushButton("Finish setup")
        self.try_sample_button.setObjectName("accentButton")
        self.finish_button.setObjectName("primaryButton")

        self.voice_setup_button.setAccessibleDescription(
            "Open the local voice catalog. Voice files download only after you confirm."
        )
        self.try_sample_button.setAccessibleDescription(
            "Place a short example in the editor and read it using the selected voice."
        )
        self.finish_button.setAccessibleDescription(
            "Hide quick setup after voice playback and shortcut configuration are clear."
        )

        self.voice_setup_button.clicked.connect(self.voice_setup_requested)
        self.try_sample_button.clicked.connect(self.try_sample_requested)
        self.finish_button.clicked.connect(self.finish_requested)

        actions = QHBoxLayout()
        actions.addWidget(self.voice_setup_button)
        actions.addWidget(self.try_sample_button)
        actions.addStretch()
        actions.addWidget(self.finish_button)

        layout = QVBoxLayout()
        layout.addWidget(intro)
        layout.addWidget(self.status_label)
        layout.addLayout(actions)
        self.setLayout(layout)

    def update_status(self, *, has_voice: bool, hotkey: str) -> None:
        """Describe the next useful setup action and enable valid controls."""
        self.try_sample_button.setEnabled(has_voice)
        self.finish_button.setEnabled(has_voice)
        if has_voice:
            self.status_label.setText(
                f"A voice is ready. Try the sample, then copy text anywhere and press {hotkey}."
            )
        else:
            self.status_label.setText(
                "No voice is ready yet. Choose an offline voice to download; on supported "
                "systems, an already-installed system voice appears automatically."
            )


class HotkeyEdit(QLineEdit):
    """Capture a global shortcut using the application's parser grammar."""

    hotkey_changed = Signal(str)
    validation_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("hotkeyEditor")
        self.setReadOnly(True)
        self.setPlaceholderText("Press a shortcut…")
        self.setToolTip("Click here, then press a modifier plus one key.")
        self.set_hotkey(DEFAULT_READ_HOTKEY)

    def hotkey(self) -> str:
        """Return the currently displayed canonical shortcut."""
        return self.text()

    def set_hotkey(self, hotkey: str) -> bool:
        """Set and validate a canonical shortcut string."""
        try:
            binding = parse_hotkey(hotkey)
        except HotkeyRegistrationError as exc:
            self.validation_changed.emit(str(exc))
            return False

        self.setText(binding.display_name)
        self.validation_changed.emit("")
        return True

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.isAutoRepeat():
            return

        key_name = self._key_name(event.key())
        if key_name is None:
            self.validation_changed.emit(
                "That key is not supported. Use a letter, number, function, "
                "or named navigation key."
            )
            return

        shortcut = self._shortcut_text(event, key_name)
        if shortcut is None:
            self.validation_changed.emit(
                "Global shortcuts must include Ctrl, Alt, Shift, or Win."
            )
            return

        if self.set_hotkey(shortcut):
            self.hotkey_changed.emit(self.hotkey())

    @staticmethod
    def _key_name(key: int) -> str | None:
        if Qt.Key.Key_A.value <= key <= Qt.Key.Key_Z.value:
            return chr(key)

        if Qt.Key.Key_0.value <= key <= Qt.Key.Key_9.value:
            return chr(key)

        if Qt.Key.Key_F1.value <= key <= Qt.Key.Key_F24.value:
            return f"F{key - Qt.Key.Key_F1.value + 1}"

        return _SPECIAL_KEY_NAMES.get(key)

    @staticmethod
    def _shortcut_text(event: QKeyEvent, key_name: str) -> str | None:
        modifiers = event.modifiers()
        modifier_names: list[str] = []

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            modifier_names.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            modifier_names.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifier_names.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            modifier_names.append("Win")

        if not modifier_names:
            return None

        return "+".join([*modifier_names, key_name])


class VoiceSelectorWidget(QWidget):
    """Display installed voices grouped by language and expose selection events."""

    voice_changed = Signal(str)
    find_voices_requested = Signal()
    manage_voices_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")

        self.combo = QComboBox()
        self.combo.setObjectName("voiceSelector")
        self.combo.setAccessibleName("Reading voice")
        self.combo.setAccessibleDescription(
            "Select the voice shared by the window, shortcut, browser extension, and local API."
        )
        self.find_button = QPushButton("Find voices…")
        self.manage_button = QPushButton("Manage voices…")
        self.find_button.setAccessibleDescription(
            "Browse voices that can be downloaded and stored on this computer."
        )
        self.manage_button.setAccessibleDescription(
            "Inspect and manage voices available to Syllavox."
        )
        self._last_voice_index = -1

        self.combo.currentIndexChanged.connect(self._on_index_changed)
        self.find_button.clicked.connect(self.find_voices_requested)
        self.manage_button.clicked.connect(self.manage_voices_requested)

        selector_layout = QHBoxLayout()
        selector_layout.setContentsMargins(0, 0, 0, 0)
        selector_layout.setSpacing(10)
        selector_layout.addWidget(self.combo)
        selector_layout.addWidget(self.find_button)
        selector_layout.addWidget(self.manage_button)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(0)
        form.addRow("Voice:", selector_layout)
        self.setLayout(form)

        self.combo.setMinimumHeight(38)
        self.combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        for button in (self.find_button, self.manage_button):
            button.setMinimumHeight(38)
            button.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Fixed,
            )

    def set_no_voices(self) -> None:
        """Show the disabled empty state."""
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem("No voices available")
        self.combo.setEnabled(False)
        self.combo.blockSignals(False)
        self._last_voice_index = -1

    def set_system_voice_mode(
        self,
        enabled: bool,
        system_voice_name: str = "the operating system",
    ) -> None:
        """Adapt catalog actions for voices owned by the operating system."""
        self.find_button.setVisible(not enabled)
        self.manage_button.setText(
            "System voices…" if enabled else "Manage voices…"
        )
        self.manage_button.setToolTip(
            f"Choose from voices installed in {system_voice_name}."
            if enabled
            else "Load, unload, or remove downloaded voice models."
        )

    def set_voices(
        self,
        voices: list[VoiceInfo],
        saved_voice_id: object = None,
    ) -> str | None:
        """Populate the selector and return the selected voice ID."""
        if not voices:
            self.set_no_voices()
            return None

        model = QStandardItemModel(self.combo)
        groups: dict[str, QStandardItem] = {}

        for voice in sorted(
            voices,
            key=lambda item: (
                self._voice_language_label(item).lower(),
                item.name.lower(),
                item.voice_id,
            ),
        ):
            language_label = self._voice_language_label(voice)
            group = groups.get(language_label)

            if group is None:
                group = QStandardItem(language_label)
                group.setFlags(Qt.ItemFlag.ItemIsEnabled)
                model.appendRow(group)
                groups[language_label] = group

            voice_item = QStandardItem(self._voice_display_name(voice))
            voice_item.setData(voice.voice_id, Qt.ItemDataRole.UserRole)
            voice_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )
            model.appendRow(voice_item)

        selected_index = self._find_selected_index(model, saved_voice_id)
        if selected_index < 0:
            selected_index = self._find_first_voice_index(model)

        if selected_index < 0:
            self.set_no_voices()
            return None

        self.combo.blockSignals(True)
        self.combo.setModel(model)
        self.combo.setEnabled(True)
        self.combo.setCurrentIndex(selected_index)
        self.combo.blockSignals(False)
        self._last_voice_index = selected_index

        return self.selected_voice_id()

    def selected_voice_id(self) -> str | None:
        """Return the currently selected voice ID, if any."""
        voice_id = self.combo.currentData()
        return voice_id if isinstance(voice_id, str) else None

    def _on_index_changed(self, index: int) -> None:
        current_item = self.combo.model().item(index)

        if current_item is None or not current_item.data(Qt.ItemDataRole.UserRole):
            if self._last_voice_index >= 0:
                self.combo.blockSignals(True)
                self.combo.setCurrentIndex(self._last_voice_index)
                self.combo.blockSignals(False)
            return

        self._last_voice_index = index
        voice_id = self.selected_voice_id()
        if voice_id is not None:
            self.voice_changed.emit(voice_id)

    @staticmethod
    def _find_selected_index(
        model: QStandardItemModel,
        saved_voice_id: object,
    ) -> int:
        for index in range(model.rowCount()):
            candidate_voice_id = model.item(index).data(Qt.ItemDataRole.UserRole)
            if candidate_voice_id and candidate_voice_id == saved_voice_id:
                return index
        return -1

    @staticmethod
    def _find_first_voice_index(model: QStandardItemModel) -> int:
        for index in range(model.rowCount()):
            if model.item(index).data(Qt.ItemDataRole.UserRole):
                return index
        return -1

    @staticmethod
    def _voice_language_label(voice: VoiceInfo) -> str:
        return format_language_label(
            voice.language_code or voice.language,
            language_name=voice.language_name,
            country_name=voice.country_name,
        )

    @staticmethod
    def _voice_display_name(voice: VoiceInfo) -> str:
        if voice.language_code:
            return f"{voice.name} ({voice.language_code})"
        if voice.language:
            return f"{voice.name} ({voice.language})"
        return voice.name


class SpeechEditorWidget(QWidget):
    """Text entry area and controls used by the main speech workflow."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.text_edit = QPlainTextEdit()
        self.setObjectName("card")
        self.text_edit.setObjectName("speechText")
        self.text_edit.setPlaceholderText("Enter text to read aloud…")
        self.text_edit.setAccessibleName("Text to read aloud")
        self.text_edit.setAccessibleDescription(
            "Enter or paste text. The highlighted unit is the current reading position."
        )
        self.character_count_label = QLabel()
        self.character_count_label.setObjectName("characterCount")
        self.character_count_label.setAccessibleName("Speech character count")

        self.speak_button = QPushButton("Speak")
        self.export_button = QPushButton("Export WAV...")
        self.pause_resume_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.clear_button = QPushButton("Clear")
        self.feedback_label = QLabel()
        self.feedback_label.setObjectName("feedbackLabel")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAccessibleName("Speech status message")

        self.navigation_mode_combo = QComboBox()
        self.navigation_mode_combo.setObjectName("navigationMode")
        self.navigation_mode_combo.addItem("Sentence", "sentence")
        self.navigation_mode_combo.addItem("Paragraph", "paragraph")
        self.navigation_mode_combo.setAccessibleName("Reading navigation unit")
        self.previous_button = QPushButton("Previous")
        self.replay_button = QPushButton("Replay")
        self.next_button = QPushButton("Next")
        self.navigation_status_label = QLabel("No reading position")
        self.navigation_status_label.setObjectName("navigationStatus")
        self.navigation_status_label.setAccessibleName("Reading position")

        self.speak_button.setObjectName("accentButton")
        self.export_button.setObjectName("primaryButton")
        self.speak_button.setShortcut("Ctrl+Return")
        self.speak_button.setAccessibleDescription(
            "Start reading at the highlighted sentence or paragraph. Shortcut Ctrl+Enter."
        )
        self.pause_resume_button.setAccessibleDescription(
            "Pause or resume the current spoken unit."
        )
        self.stop_button.setAccessibleDescription(
            "Stop playback and preserve the current reading position."
        )
        self.previous_button.setAccessibleDescription(
            "Move to and read the previous sentence or paragraph."
        )
        self.replay_button.setAccessibleDescription(
            "Read the current sentence or paragraph again."
        )
        self.next_button.setAccessibleDescription(
            "Move to and read the next sentence or paragraph."
        )
        self.text_edit.setMinimumHeight(210)
        self.text_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        for button in (
            self.speak_button,
            self.export_button,
            self.pause_resume_button,
            self.stop_button,
            self.clear_button,
        ):
            button.setMinimumHeight(40)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            button_layout.addWidget(button)

        navigation_layout = QHBoxLayout()
        navigation_layout.setContentsMargins(0, 0, 0, 0)
        navigation_layout.setSpacing(8)
        navigation_layout.addWidget(QLabel("Navigate by:"))
        navigation_layout.addWidget(self.navigation_mode_combo)
        navigation_layout.addWidget(self.previous_button)
        navigation_layout.addWidget(self.replay_button)
        navigation_layout.addWidget(self.next_button)
        navigation_layout.addStretch()
        navigation_layout.addWidget(self.navigation_status_label)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.character_count_label)
        layout.addLayout(button_layout)
        layout.addLayout(navigation_layout)
        layout.addWidget(self.feedback_label)
        self.setLayout(layout)

        for button in (
            self.previous_button,
            self.replay_button,
            self.next_button,
        ):
            button.setMinimumHeight(36)

    def set_navigation_state(
        self,
        *,
        mode: str,
        index: int,
        count: int,
        previous_enabled: bool,
        next_enabled: bool,
        replay_enabled: bool,
    ) -> None:
        """Apply session position and navigation availability."""
        mode_index = self.navigation_mode_combo.findData(mode)
        if mode_index >= 0 and mode_index != self.navigation_mode_combo.currentIndex():
            self.navigation_mode_combo.blockSignals(True)
            self.navigation_mode_combo.setCurrentIndex(mode_index)
            self.navigation_mode_combo.blockSignals(False)
        unit = "sentence" if mode == "sentence" else "paragraph"
        self.navigation_status_label.setText(
            f"{unit.capitalize()} {index + 1} of {count}"
            if count
            else "No reading position"
        )
        self.previous_button.setEnabled(previous_enabled)
        self.next_button.setEnabled(next_enabled)
        self.replay_button.setEnabled(replay_enabled)
        self.previous_button.setAccessibleName(f"Previous {unit}")
        self.replay_button.setAccessibleName(f"Replay current {unit}")
        self.next_button.setAccessibleName(f"Next {unit}")

    def highlight_range(self, start: int | None, end: int | None) -> None:
        """Highlight the active source range without moving the edit cursor."""
        if start is None or end is None or start >= end:
            self.text_edit.setExtraSelections([])
            return
        selection = QTextEdit.ExtraSelection()
        cursor = QTextCursor(self.text_edit.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor
        selection.format = QTextCharFormat()
        selection.format.setBackground(QColor("#ffe9a8"))
        selection.format.setForeground(QColor("#172033"))
        self.text_edit.setExtraSelections([selection])
        self.text_edit.ensureCursorVisible()

    def update_character_count(self, maximum: int) -> None:
        """Update the visible character counter."""
        text_length = len(normalize_for_speech(self.text_edit.toPlainText()))
        self.character_count_label.setText(
            f"Speech characters: {text_length}/{maximum}"
        )

    def set_playback_controls(
        self,
        *,
        speak_enabled: bool,
        export_enabled: bool,
        pause_text: str,
        pause_enabled: bool,
        stop_enabled: bool,
        clear_enabled: bool,
    ) -> None:
        """Apply the enabled state represented by the application lifecycle."""
        self.speak_button.setEnabled(speak_enabled)
        self.export_button.setEnabled(export_enabled)
        self.pause_resume_button.setText(pause_text)
        self.pause_resume_button.setEnabled(pause_enabled)
        self.stop_button.setEnabled(stop_enabled)
        self.clear_button.setEnabled(clear_enabled)

    def set_feedback(self, message: str) -> None:
        self.feedback_label.setText(message)


class SettingsPanel(QGroupBox):
    """Settings controls and their mapping to the persisted settings schema."""

    clear_local_data_requested = Signal()
    hotkey_apply_requested = Signal()
    restart_requested = Signal()
    setup_again_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        active_backend: str = DEFAULT_TTS_BACKEND,
    ) -> None:
        super().__init__("Settings", parent)
        self.setObjectName("card")
        self._active_backend = self._normalize_backend(active_backend)

        self.start_minimized_checkbox = QCheckBox("Start minimized to tray")
        self.run_on_startup_checkbox = QCheckBox("Run Syllavox at startup")
        self.run_on_startup_checkbox.setToolTip(
            "Start Syllavox automatically when you sign in to "
            f"{startup_platform_name()}."
        )
        self.run_on_startup_checkbox.setVisible(is_startup_supported())
        self.remember_window_checkbox = QCheckBox("Remember window size")
        self.backend_combo = QComboBox()
        self.backend_combo.setAccessibleName("Speech engine")
        self.max_text_length_spinbox = QSpinBox()
        self.hotkey_action_combo = QComboBox()
        self.hotkey_edit = HotkeyEdit()
        self.reset_hotkey_button = QPushButton("Reset")
        self.reset_hotkey_button.setObjectName("quietButton")
        self.apply_hotkey_button = QPushButton("Apply changes")
        self.apply_hotkey_button.setObjectName("accentButton")
        self.hotkey_hint_label = QLabel(
            hotkey_hint()
        )
        self.hotkey_hint_label.setObjectName("sectionHint")
        self.hotkey_error_label = QLabel()
        self.hotkey_error_label.setObjectName("fieldError")
        self.hotkey_error_label.setWordWrap(True)
        self.hotkey_error_label.hide()
        self.backend_hint_label = QLabel(
            "Piper is the default. Sherpa-ONNX is an optional backend; its "
            "model bundles are installed separately and apply after restart."
        )
        self.backend_hint_label.setObjectName("sectionHint")
        self.backend_hint_label.setWordWrap(True)
        self.backend_restart_hint_label = QLabel()
        self.backend_restart_hint_label.setObjectName("sectionHint")
        self.backend_restart_hint_label.setWordWrap(True)
        self.backend_restart_button = QPushButton("Restart to apply")
        self.backend_restart_button.setObjectName("accentButton")
        self.backend_restart_button.setToolTip(
            "Save the selected speech engine and restart Syllavox."
        )
        self.backend_restart_hint_label.hide()
        self.backend_restart_button.hide()
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_value_label = QLabel()
        self.rate_spinbox = QDoubleSpinBox()
        self.clear_local_data_button = QPushButton(
            "Clear local data and quit"
        )
        self.setup_again_button = QPushButton("Run setup again…")
        self.setup_again_button.setAccessibleDescription(
            "Show the quick setup tutorial and sample again without changing your saved text."
        )
        self.advanced_button = QPushButton("Show advanced settings")
        self.advanced_button.setCheckable(True)
        self.advanced_button.setAccessibleDescription(
            "Show speech engine and maximum request length controls."
        )
        self.advanced_panel = QWidget()
        self.advanced_panel.setObjectName("advancedSettings")
        self.advanced_panel.hide()

        self.max_text_length_spinbox.setRange(
            100,
            MAX_CONFIGURABLE_TEXT_LENGTH,
        )
        self.max_text_length_spinbox.setSingleStep(100)
        self.volume_slider.setRange(0, 100)
        self.rate_spinbox.setRange(MIN_PLAYBACK_RATE, MAX_PLAYBACK_RATE)
        self.rate_spinbox.setSingleStep(0.1)
        self.rate_spinbox.setDecimals(1)
        self.rate_spinbox.setSuffix("×")

        self.hotkey_action_combo.addItem("Speak clipboard", "speak_clipboard")
        self.hotkey_action_combo.addItem("Open window", "open_window")
        self.hotkey_action_combo.setEnabled(False)
        for descriptor in backend_descriptors():
            self.backend_combo.addItem(
                descriptor.display_name,
                descriptor.backend_id,
            )
        self.backend_combo.currentIndexChanged.connect(
            self._on_backend_selection_changed
        )
        self.backend_restart_button.clicked.connect(
            self.restart_requested.emit
        )
        self.reset_hotkey_button.clicked.connect(
            lambda: self.hotkey_edit.set_hotkey(DEFAULT_READ_HOTKEY)
        )
        self.apply_hotkey_button.clicked.connect(
            self.hotkey_apply_requested.emit
        )
        self.hotkey_edit.validation_changed.connect(
            self._show_hotkey_validation
        )
        self.clear_local_data_button.clicked.connect(
            self.clear_local_data_requested
        )
        self.setup_again_button.clicked.connect(self.setup_again_requested)
        self.advanced_button.toggled.connect(self.advanced_panel.setVisible)
        self.advanced_button.toggled.connect(
            lambda expanded: self.advanced_button.setText(
                "Hide advanced settings" if expanded else "Show advanced settings"
            )
        )

        form = QFormLayout()
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow(self.start_minimized_checkbox)
        form.addRow(self.run_on_startup_checkbox)
        form.addRow(self.remember_window_checkbox)
        backend_action_layout = QHBoxLayout()
        backend_action_layout.setContentsMargins(0, 0, 0, 0)
        backend_action_layout.addWidget(self.backend_restart_hint_label)
        backend_action_layout.addStretch()
        backend_action_layout.addWidget(self.backend_restart_button)
        advanced_form = QFormLayout(self.advanced_panel)
        advanced_form.setContentsMargins(0, 0, 0, 0)
        advanced_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        advanced_form.addRow("Speech engine:", self.backend_combo)
        advanced_form.addRow(self.backend_hint_label)
        advanced_form.addRow(backend_action_layout)
        advanced_form.addRow("Max text length:", self.max_text_length_spinbox)

        hotkey_layout = QHBoxLayout()
        hotkey_layout.addWidget(self.hotkey_edit)
        hotkey_layout.addWidget(self.reset_hotkey_button)
        hotkey_layout.addWidget(self.apply_hotkey_button)
        form.addRow("Read hotkey:", hotkey_layout)
        form.addRow("", self.hotkey_hint_label)
        form.addRow("", self.hotkey_error_label)

        volume_layout = QHBoxLayout()
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value_label)
        form.addRow("Volume:", volume_layout)
        form.addRow("Speed:", self.rate_spinbox)
        form.addRow("Privacy:", self.clear_local_data_button)
        form.addRow("Help:", self.setup_again_button)
        form.addRow(self.advanced_button)
        form.addRow(self.advanced_panel)
        self.setLayout(form)

        for control in (
            self.backend_combo,
            self.max_text_length_spinbox,
            self.hotkey_edit,
            self.rate_spinbox,
        ):
            control.setMinimumHeight(36)
        for button in (
            self.reset_hotkey_button,
            self.apply_hotkey_button,
            self.backend_restart_button,
            self.clear_local_data_button,
            self.setup_again_button,
        ):
            button.setMinimumHeight(36)
        self.backend_combo.setMinimumWidth(220)
        self.backend_combo.setMaximumWidth(320)
        self.max_text_length_spinbox.setMinimumWidth(120)
        self.max_text_length_spinbox.setMaximumWidth(180)
        self.rate_spinbox.setMinimumWidth(120)
        self.rate_spinbox.setMaximumWidth(180)
        self.clear_local_data_button.setMaximumWidth(260)
        self.volume_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.volume_value_label.setMinimumWidth(42)
        self._update_backend_controls()

    def load_settings(self, settings: dict[str, Any]) -> None:
        """Load persisted values into the controls."""
        ui_settings = settings.get("ui", {})
        window_settings = settings.get("window", {})
        hotkey_settings = settings.get("hotkey", {})
        tts_settings = settings.get("tts", {})
        playback_settings = settings.get("playback", {})

        self.start_minimized_checkbox.setChecked(
            bool(ui_settings.get("start_minimized_to_tray", True))
        )
        self.run_on_startup_checkbox.setChecked(
            bool(ui_settings.get("run_on_startup", False))
        )
        self.remember_window_checkbox.setChecked(
            bool(window_settings.get("remember_position", True))
        )
        self.max_text_length_spinbox.setValue(
            int(tts_settings.get("max_text_length", DEFAULT_MAX_TEXT_LENGTH))
        )

        backend_value = str(
            tts_settings.get("backend", DEFAULT_TTS_BACKEND)
        ).strip().lower().replace("-", "_")
        backend_index = self.backend_combo.findData(backend_value)
        self.backend_combo.blockSignals(True)
        self.backend_combo.setCurrentIndex(
            backend_index if backend_index >= 0 else 0
        )
        self.backend_combo.blockSignals(False)
        self._update_backend_controls()

        hotkey_action = hotkey_settings.get("action", "speak_clipboard")
        index = self.hotkey_action_combo.findData(hotkey_action)
        self.hotkey_action_combo.setCurrentIndex(index if index >= 0 else 0)

        configured_hotkey = hotkey_settings.get(
            "key",
            DEFAULT_READ_HOTKEY,
        )
        if not self.hotkey_edit.set_hotkey(str(configured_hotkey)):
            self.hotkey_edit.set_hotkey(DEFAULT_READ_HOTKEY)
            self._show_hotkey_validation(
                "The saved shortcut was invalid; the default was restored."
            )

        volume = normalize_playback_value(
            playback_settings.get("volume", DEFAULT_PLAYBACK_VOLUME),
            DEFAULT_PLAYBACK_VOLUME,
            0.0,
            1.0,
        )
        rate = normalize_playback_value(
            playback_settings.get("rate", DEFAULT_PLAYBACK_RATE),
            DEFAULT_PLAYBACK_RATE,
            MIN_PLAYBACK_RATE,
            MAX_PLAYBACK_RATE,
        )
        self.volume_slider.setValue(round(volume * 100))
        self.rate_spinbox.setValue(rate)

    def write_settings(
        self,
        settings: dict[str, Any],
        *,
        voice_id: str | None,
    ) -> None:
        """Write current control values into the persisted settings mapping."""
        ui_settings = settings.setdefault("ui", {})
        window_settings = settings.setdefault("window", {})
        hotkey_settings = settings.setdefault("hotkey", {})
        tts_settings = settings.setdefault("tts", {})
        playback_settings = settings.setdefault("playback", {})

        ui_settings["start_minimized_to_tray"] = (
            self.start_minimized_checkbox.isChecked()
        )
        ui_settings["run_on_startup"] = self.run_on_startup_checkbox.isChecked()
        window_settings["remember_position"] = (
            self.remember_window_checkbox.isChecked()
        )
        tts_settings["max_text_length"] = self.max_text_length_spinbox.value()
        tts_settings["voice_id"] = voice_id
        tts_settings["backend"] = self.backend_combo.currentData()
        hotkey_settings["action"] = self.hotkey_action_combo.currentData()
        hotkey_settings["key"] = self.hotkey_edit.hotkey()
        playback_settings["volume"] = self.volume_slider.value() / 100
        playback_settings["rate"] = self.rate_spinbox.value()

    def _show_hotkey_validation(self, message: str) -> None:
        self.hotkey_error_label.setText(message)
        self.hotkey_error_label.setVisible(bool(message))

    def _on_backend_selection_changed(self, index: int) -> None:
        del index
        self._update_backend_controls()

    def _update_backend_controls(self) -> None:
        selected_backend = self._normalize_backend(self.backend_combo.currentData())
        restart_required = selected_backend != self._active_backend

        self.backend_restart_button.setText(
            f"Restart to use {self._backend_display_name(selected_backend)}"
        )
        self.backend_restart_hint_label.setText(
            f"Save settings and restart to switch to "
            f"{self._backend_display_name(selected_backend)}."
        )
        self.backend_restart_hint_label.setVisible(restart_required)
        self.backend_restart_button.setVisible(restart_required)

        if selected_backend == SHERPA_ONNX_TTS_BACKEND:
            self.backend_hint_label.setText(
                "Sherpa-ONNX is optional and uses separately installed model "
                "bundles. It becomes active after restarting Syllavox."
            )
        elif selected_backend == WINDOWS_SAPI_TTS_BACKEND:
            self.backend_hint_label.setText(
                "Windows SAPI uses voices installed in Windows; Syllavox "
                "does not download or manage their model files. It becomes "
                "active after restarting Syllavox."
            )
        elif selected_backend == MACOS_SYSTEM_TTS_BACKEND:
            self.backend_hint_label.setText(
                "macOS system speech uses voices installed in macOS; "
                "Syllavox does not download or manage their voice files. It "
                "becomes active after restarting Syllavox."
            )
        elif selected_backend == LINUX_ESPEAK_TTS_BACKEND:
            self.backend_hint_label.setText(
                "Linux system speech uses voices provided by the installed "
                "eSpeak NG package; Syllavox does not download or manage "
                "those voices. It becomes active after restarting Syllavox."
            )
        else:
            self.backend_hint_label.setText(
                "Piper is the default speech engine. Its installed voices "
                "remain available when Sherpa-ONNX is not selected."
            )

    @staticmethod
    def _normalize_backend(value: object) -> str:
        return normalize_backend_id(value)

    @staticmethod
    def _backend_display_name(value: str) -> str:
        return backend_display_name(value)


__all__ = [
    "HotkeyEdit",
    "OnboardingPanel",
    "SAMPLE_TEXT",
    "SettingsPanel",
    "SpeechEditorWidget",
    "VoiceSelectorWidget",
]
