"""Presentation widget for the installed-voice management dialog."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from syllavox.tts.base import VoiceInfo
from syllavox.tts.catalog import format_language_label


class VoiceManagementView(QWidget):
    """Render installed voices and expose user interaction signals."""

    selection_changed = Signal()
    load_requested = Signal()
    unload_requested = Signal()
    delete_requested = Signal()
    remove_resources_requested = Signal()
    close_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        system_voice_mode: bool = False,
        system_voice_name: str = "Windows SAPI",
    ) -> None:
        super().__init__(parent)
        self._system_voice_mode = system_voice_mode
        self._system_voice_name = system_voice_name

        self.intro_label = QLabel(
            (
                f"These voices are provided by {system_voice_name} and are "
                "managed by the operating system. Syllavox can select them "
                "but cannot install, unload, or delete them."
                if system_voice_mode
                else "Load a voice before speaking to avoid first-use loading "
                "delay. Unload removes it from memory; Delete removes its "
                "local files."
            )
        )
        self.intro_label.setWordWrap(True)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["Voice", "Language", "Source", "Status"]
            if system_voice_mode
            else ["Voice", "Language", "Size", "Status"]
        )
        self.tree.currentItemChanged.connect(self._on_current_item_changed)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)

        self.load_button = QPushButton("Load")
        self.unload_button = QPushButton("Unload")
        self.delete_button = QPushButton("Delete")
        self.remove_resources_button = QPushButton(
            "Remove unused language data"
        )
        self.close_button = QPushButton("Close")

        for button in (
            self.load_button,
            self.unload_button,
            self.delete_button,
            self.remove_resources_button,
        ):
            button.setVisible(not system_voice_mode)

        self.load_button.clicked.connect(self.load_requested)
        self.unload_button.clicked.connect(self.unload_requested)
        self.delete_button.clicked.connect(self.delete_requested)
        self.remove_resources_button.clicked.connect(
            self.remove_resources_requested
        )
        self.close_button.clicked.connect(self.close_requested)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self.load_button)
        action_layout.addWidget(self.unload_button)
        action_layout.addWidget(self.delete_button)
        action_layout.addWidget(self.remove_resources_button)
        action_layout.addStretch()
        action_layout.addWidget(self.close_button)

        layout = QVBoxLayout()
        layout.addWidget(self.intro_label)
        layout.addWidget(self.tree)
        layout.addWidget(self.status_label)
        layout.addLayout(action_layout)
        self.setLayout(layout)

    def populate(
        self,
        voices: list[VoiceInfo],
        model_size: Callable[[str], int],
        is_loaded: Callable[[str], bool],
    ) -> None:
        """Render the current installed voice inventory."""
        self.tree.clear()

        for voice in sorted(voices, key=self._voice_sort_key):
            if self._system_voice_mode:
                source_text = self._system_voice_name
                status = "Available"
            else:
                try:
                    source_text = self._format_size(model_size(voice.voice_id))
                except Exception:
                    source_text = "Unknown"
                status = "Loaded" if is_loaded(voice.voice_id) else "Unloaded"

            item = QTreeWidgetItem(
                self.tree,
                [
                    self._display_name(voice),
                    format_language_label(
                        voice.language_code or voice.language,
                        language_name=voice.language_name,
                        country_name=voice.country_name,
                    ),
                    source_text,
                    status,
                ],
            )
            item.setData(0, Qt.ItemDataRole.UserRole, voice.voice_id)

        if self.tree.topLevelItemCount() > 0:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def selected_voice_id(self) -> str | None:
        """Return the selected installed voice ID, if any."""
        item = self.tree.currentItem()
        if item is None:
            return None

        voice_id = item.data(0, Qt.ItemDataRole.UserRole)
        return voice_id if isinstance(voice_id, str) else None

    def set_controls(
        self,
        *,
        load_enabled: bool,
        unload_enabled: bool,
        delete_enabled: bool,
        close_enabled: bool,
    ) -> None:
        """Apply the enabled state calculated by the dialog controller."""
        self.load_button.setEnabled(load_enabled)
        self.unload_button.setEnabled(unload_enabled)
        self.delete_button.setEnabled(delete_enabled)
        self.close_button.setEnabled(close_enabled)

    def set_remove_resources_enabled(self, enabled: bool) -> None:
        """Set whether unused shared language data can be removed."""
        self.remove_resources_button.setEnabled(
            enabled and not self._system_voice_mode
        )

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def _on_current_item_changed(
        self,
        current: QTreeWidgetItem | None,
        previous: QTreeWidgetItem | None,
    ) -> None:
        del current, previous
        self.selection_changed.emit()

    @staticmethod
    def _voice_sort_key(voice: VoiceInfo) -> tuple[str, str, str]:
        return (
            format_language_label(
                voice.language_code or voice.language,
                language_name=voice.language_name,
                country_name=voice.country_name,
            ).lower(),
            voice.name.lower(),
            voice.voice_id,
        )

    @staticmethod
    def _display_name(voice: VoiceInfo) -> str:
        quality = f" ({voice.quality})" if voice.quality else ""
        return f"{voice.name}{quality}"

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        value = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.1f} {unit}"
            value /= 1024


__all__ = ["VoiceManagementView"]
