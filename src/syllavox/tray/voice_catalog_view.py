"""Presentation widget for browsing and selecting catalog voices."""

from __future__ import annotations

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

from syllavox.tts.catalog_models import SherpaCatalogEntry, VoiceCatalogEntry


class VoiceCatalogView(QWidget):
    """Render catalog entries and expose selection/action signals."""

    refresh_requested = Signal()
    install_requested = Signal()
    close_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        backend_label: str = "Piper",
        catalog_url: str | None = None,
    ) -> None:
        super().__init__(parent)

        intro_label = QLabel(
            f"Choose a {backend_label} voice to install locally. Downloads happen only "
            "when you press Install."
        )
        intro_label.setWordWrap(True)

        if catalog_url:
            source_label = QLabel(
                f'Source: <a href="{catalog_url}">official {backend_label} '
                "model catalog</a>"
            )
        else:
            source_label = QLabel(
                'Source: <a href="https://huggingface.co/rhasspy/piper-voices">'
                "official Piper voice catalog on Hugging Face</a> \u00b7 "
                '<a href="https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md">'
                "Piper voice documentation</a>"
            )
        source_label.setOpenExternalLinks(True)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Voice", "Quality", "Status"])
        self.tree.setRootIsDecorated(True)
        self.tree.currentItemChanged.connect(self._on_current_item_changed)

        self.status_label = QLabel(f"Loading {backend_label} voice catalog\u2026")
        self.status_label.setWordWrap(True)

        self.refresh_button = QPushButton("Refresh catalog")
        self.install_button = QPushButton("Install selected")
        self.close_button = QPushButton("Close")

        self.refresh_button.clicked.connect(self.refresh_requested)
        self.install_button.clicked.connect(self.install_requested)
        self.close_button.clicked.connect(self.close_requested)
        self.install_button.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(self.install_button)
        button_layout.addWidget(self.close_button)

        layout = QVBoxLayout()
        layout.addWidget(intro_label)
        layout.addWidget(source_label)
        layout.addWidget(self.tree)
        layout.addWidget(self.status_label)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        self._installed_voice_ids: set[str] = set()
        self._busy = False

    def populate(
        self,
        entries: list[VoiceCatalogEntry | SherpaCatalogEntry],
        installed_voice_ids: set[str],
    ) -> None:
        """Render catalog entries grouped by language."""
        self._installed_voice_ids = set(installed_voice_ids)
        self.tree.clear()

        groups: dict[str, QTreeWidgetItem] = {}

        for entry in sorted(
            entries,
            key=lambda item: (
                item.language_label.lower(),
                item.name.lower(),
                item.quality.lower(),
            ),
        ):
            group = groups.get(entry.language_label)
            if group is None:
                group = QTreeWidgetItem(self.tree, [entry.language_label])
                group.setFirstColumnSpanned(True)
                groups[entry.language_label] = group

            installed = entry.voice_id in self._installed_voice_ids or entry.installed
            voice_item = QTreeWidgetItem(
                group,
                [
                    entry.display_name,
                    entry.quality,
                    "Installed" if installed else "Available",
                ],
            )
            voice_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                entry.voice_id,
            )
            voice_item.setData(
                0,
                Qt.ItemDataRole.UserRole + 1,
                entry,
            )

        self.tree.expandAll()
        if self.tree.topLevelItemCount() > 0:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        self._update_install_button()

    def selected_entry(self) -> VoiceCatalogEntry | SherpaCatalogEntry | None:
        """Return the selected catalog entry, if a voice row is selected."""
        item = self.tree.currentItem()
        if item is None:
            return None

        entry = item.data(0, Qt.ItemDataRole.UserRole + 1)
        return (
            entry
            if isinstance(entry, (VoiceCatalogEntry, SherpaCatalogEntry))
            else None
        )

    def set_busy(self, message: str, busy: bool) -> None:
        """Update status text and action controls for a background operation."""
        self._busy = busy
        self.status_label.setText(message)
        self.refresh_button.setEnabled(not busy)
        self._update_install_button()

    def _on_current_item_changed(
        self,
        current: QTreeWidgetItem | None,
        previous: QTreeWidgetItem | None,
    ) -> None:
        del current, previous
        self._update_install_button()

    def _update_install_button(self) -> None:
        entry = self.selected_entry()
        self.install_button.setEnabled(
            not self._busy
            and entry is not None
            and entry.voice_id not in self._installed_voice_ids
            and not entry.installed
        )


__all__ = ["VoiceCatalogView"]
