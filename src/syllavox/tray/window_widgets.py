"""Reusable widgets used by the main Syllavox window.

The main window coordinates application services and user actions.  These
widgets own the presentation details for the voice selector, speech editor,
and settings panel so a future UI redesign can replace each area separately.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
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
from syllavox.constants import DEFAULT_MAX_TEXT_LENGTH
from syllavox.text_formatting import normalize_for_speech
from syllavox.tts.base import VoiceInfo
from syllavox.tts.catalog import format_language_label


class VoiceSelectorWidget(QWidget):
    """Display installed voices grouped by language and expose selection events."""

    voice_changed = Signal(str)
    find_voices_requested = Signal()
    manage_voices_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.combo = QComboBox()
        self.combo.setObjectName("voiceSelector")
        self.find_button = QPushButton("Find more voices…")
        self.manage_button = QPushButton("Manage voices…")
        self._last_voice_index = -1

        self.combo.currentIndexChanged.connect(self._on_index_changed)
        self.find_button.clicked.connect(self.find_voices_requested)
        self.manage_button.clicked.connect(self.manage_voices_requested)

        selector_layout = QHBoxLayout()
        selector_layout.addWidget(self.combo)
        selector_layout.addWidget(self.find_button)
        selector_layout.addWidget(self.manage_button)

        form = QFormLayout()
        form.addRow("Voice:", selector_layout)
        self.setLayout(form)

    def set_no_voices(self) -> None:
        """Show the disabled empty state."""
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem("No voices available")
        self.combo.setEnabled(False)
        self.combo.blockSignals(False)
        self._last_voice_index = -1

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
        self.text_edit.setPlaceholderText("Enter text to read aloud…")
        self.character_count_label = QLabel()

        self.speak_button = QPushButton("Speak")
        self.export_button = QPushButton("Export WAV...")
        self.pause_resume_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.clear_button = QPushButton("Clear")
        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)

        button_layout = QHBoxLayout()
        for button in (
            self.speak_button,
            self.export_button,
            self.pause_resume_button,
            self.stop_button,
            self.clear_button,
        ):
            button_layout.addWidget(button)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.character_count_label)
        layout.addLayout(button_layout)
        layout.addWidget(self.feedback_label)
        self.setLayout(layout)

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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Settings", parent)

        self.start_minimized_checkbox = QCheckBox("Start minimized to tray")
        self.remember_window_checkbox = QCheckBox("Remember window size")
        self.max_text_length_spinbox = QSpinBox()
        self.hotkey_action_combo = QComboBox()
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_value_label = QLabel()
        self.rate_spinbox = QDoubleSpinBox()
        self.clear_local_data_button = QPushButton(
            "Clear local data and quit"
        )

        self.max_text_length_spinbox.setRange(100, 10000)
        self.max_text_length_spinbox.setSingleStep(100)
        self.volume_slider.setRange(0, 100)
        self.rate_spinbox.setRange(MIN_PLAYBACK_RATE, MAX_PLAYBACK_RATE)
        self.rate_spinbox.setSingleStep(0.1)
        self.rate_spinbox.setDecimals(1)
        self.rate_spinbox.setSuffix("×")

        self.hotkey_action_combo.addItem("Speak clipboard", "speak_clipboard")
        self.hotkey_action_combo.addItem("Open window", "open_window")
        self.hotkey_action_combo.setEnabled(False)
        self.clear_local_data_button.clicked.connect(
            self.clear_local_data_requested
        )

        form = QFormLayout()
        form.addRow("", self.start_minimized_checkbox)
        form.addRow("", self.remember_window_checkbox)
        form.addRow("Max text length:", self.max_text_length_spinbox)
        form.addRow("Hotkey action:", self.hotkey_action_combo)

        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value_label)
        form.addRow("Volume:", volume_layout)
        form.addRow("Speed:", self.rate_spinbox)
        form.addRow("Privacy:", self.clear_local_data_button)
        self.setLayout(form)

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
        self.remember_window_checkbox.setChecked(
            bool(window_settings.get("remember_position", True))
        )
        self.max_text_length_spinbox.setValue(
            int(tts_settings.get("max_text_length", DEFAULT_MAX_TEXT_LENGTH))
        )

        hotkey_action = hotkey_settings.get("action", "speak_clipboard")
        index = self.hotkey_action_combo.findData(hotkey_action)
        self.hotkey_action_combo.setCurrentIndex(index if index >= 0 else 0)

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
        window_settings["remember_position"] = (
            self.remember_window_checkbox.isChecked()
        )
        tts_settings["max_text_length"] = self.max_text_length_spinbox.value()
        tts_settings["voice_id"] = voice_id
        hotkey_settings["action"] = self.hotkey_action_combo.currentData()
        playback_settings["volume"] = self.volume_slider.value() / 100
        playback_settings["rate"] = self.rate_spinbox.value()


__all__ = ["SettingsPanel", "SpeechEditorWidget", "VoiceSelectorWidget"]
