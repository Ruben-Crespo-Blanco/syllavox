"""Dialog controller for browsing and installing local voice bundles."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import QDialog, QVBoxLayout

from syllavox.tray.background_worker import BackgroundWorkerMixin
from syllavox.tray.voice_catalog_view import VoiceCatalogView
from syllavox.tts.catalog_models import SherpaCatalogEntry, VoiceCatalogEntry


VoiceInstalledCallback = Callable[[str], None]


class VoiceCatalogDialog(BackgroundWorkerMixin, QDialog):
    """Coordinate catalog operations and display them in ``VoiceCatalogView``."""

    def __init__(
        self,
        catalog: object,
        installed_voice_ids: set[str],
        on_voice_installed: VoiceInstalledCallback,
        logger: logging.Logger,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._catalog = catalog
        self._installed_voice_ids = set(installed_voice_ids)
        self._on_voice_installed = on_voice_installed
        self._logger = logger
        self._entries: dict[str, Any] = {}
        self._initialize_worker(self._on_worker_result)

        backend_label = str(getattr(catalog, "display_name", "Voice"))
        catalog_url = getattr(catalog, "catalog_url", None)
        self.setWindowTitle(f"{backend_label} voices")
        self.setMinimumSize(700, 500)

        self._view = VoiceCatalogView(
            backend_label=backend_label,
            catalog_url=catalog_url,
        )
        self._view.refresh_requested.connect(self._load_catalog)
        self._view.install_requested.connect(self._install_selected)
        self._view.close_requested.connect(self.close)

        # Preserve the previous private widget aliases for callers and tests.
        self._tree = self._view.tree
        self._status_label = self._view.status_label
        self._refresh_button = self._view.refresh_button
        self._install_button = self._view.install_button
        self._close_button = self._view.close_button

        layout = QVBoxLayout()
        layout.addWidget(self._view)
        self.setLayout(layout)

        self._view.set_busy(
            f"Loading {backend_label} voice catalog\u2026",
            busy=False,
        )
        self._load_catalog()

    def _load_catalog(self) -> None:
        if self._is_worker_running():
            return

        self._view.set_busy(
            f"Loading {self.windowTitle()} catalog\u2026",
            busy=True,
        )
        self._start_worker(self._catalog.fetch_catalog, "catalog")

    def _install_selected(self) -> None:
        entry = self._view.selected_entry()
        if entry is None:
            return

        self._view.set_busy(f"Installing {entry.voice_id}\u2026", busy=True)
        self._start_worker(
            lambda: self._catalog.install_voice(entry),
            "installed",
        )

    def _on_worker_result(self, result: tuple[str, object]) -> None:
        operation, payload = result
        self._worker = None

        if operation == "error":
            self._view.set_busy(str(payload), busy=False)
            self._logger.warning("Voice catalog operation failed: %s", payload)
            return

        if operation == "catalog":
            if not isinstance(payload, list) or not all(
                isinstance(entry, (VoiceCatalogEntry, SherpaCatalogEntry))
                for entry in payload
            ):
                self._view.set_busy(
                    "The voice catalog returned invalid data.",
                    busy=False,
                )
                return

            entries = payload
            self._entries = {entry.voice_id: entry for entry in entries}
            self._view.populate(entries, self._installed_voice_ids)
            self._view.set_busy(
                f"{len(entries)} {self.windowTitle().split(' voices', 1)[0]} models found.",
                busy=False,
            )
            return

        if operation == "installed" and isinstance(
            payload,
            (VoiceCatalogEntry, SherpaCatalogEntry),
        ):
            self._installed_voice_ids.add(payload.voice_id)
            self._entries[payload.voice_id] = payload
            self._view.populate(
                list(self._entries.values()),
                self._installed_voice_ids,
            )
            self._view.set_busy(
                f"Installed {payload.voice_id}.",
                busy=False,
            )
            self._on_voice_installed(payload.voice_id)


__all__ = ["VoiceCatalogDialog"]
