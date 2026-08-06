from __future__ import annotations

import logging
import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from syllavox.tray.voice_catalog_dialog import VoiceCatalogDialog
from syllavox.tts.catalog import VoiceCatalogEntry


_QT_APP = QApplication.instance() or QApplication([])


def make_entry() -> VoiceCatalogEntry:
    return VoiceCatalogEntry(
        voice_id="en_US-lessac-medium",
        name="lessac",
        language_code="en_US",
        language_name="English",
        country_name="United States",
        quality="medium",
        num_speakers=1,
        model_url="https://example.test/voice.onnx",
        config_url="https://example.test/voice.onnx.json",
    )


class FakeCatalog:
    def fetch_catalog(self) -> list[VoiceCatalogEntry]:
        return [make_entry()]

    def install_voice(self, entry: VoiceCatalogEntry) -> VoiceCatalogEntry:
        return replace(entry, installed=True)


def test_dialog_coordinates_catalog_and_install_operations(
    monkeypatch,
) -> None:
    assert _QT_APP is not None
    monkeypatch.setattr(VoiceCatalogDialog, "_load_catalog", lambda self: None)

    installed_voice_ids: list[str] = []
    dialog = VoiceCatalogDialog(
        catalog=FakeCatalog(),
        installed_voice_ids=set(),
        on_voice_installed=installed_voice_ids.append,
        logger=logging.getLogger("tests.voice_catalog_dialog"),
    )

    entry = make_entry()
    dialog._on_worker_result(("catalog", [entry]))
    dialog._tree.setCurrentItem(dialog._tree.topLevelItem(0).child(0))

    operations: list[tuple[object, str]] = []
    dialog._start_worker = (
        lambda operation, operation_name="success": operations.append(
            (operation, operation_name)
        )
    )
    dialog._install_selected()

    assert len(operations) == 1
    operation, operation_name = operations[0]
    assert operation_name == "installed"
    installed_entry = operation()
    dialog._on_worker_result((operation_name, installed_entry))

    assert installed_voice_ids == [entry.voice_id]
    assert entry.voice_id in dialog._installed_voice_ids
    assert "Installed" in dialog._status_label.text()

    dialog.close()


def test_dialog_displays_background_operation_errors(monkeypatch) -> None:
    assert _QT_APP is not None
    monkeypatch.setattr(VoiceCatalogDialog, "_load_catalog", lambda self: None)

    dialog = VoiceCatalogDialog(
        catalog=FakeCatalog(),
        installed_voice_ids=set(),
        on_voice_installed=lambda _voice_id: None,
        logger=logging.getLogger("tests.voice_catalog_dialog"),
    )

    dialog._on_worker_result(("error", "catalog unavailable"))

    assert dialog._status_label.text() == "catalog unavailable"
    assert dialog._refresh_button.isEnabled() is True

    dialog.close()
