from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from syllavox.tray.voice_catalog_view import VoiceCatalogView
from syllavox.tts.catalog import VoiceCatalogEntry


_QT_APP = QApplication.instance() or QApplication([])


def make_entry(voice_id: str, name: str, language_code: str) -> VoiceCatalogEntry:
    return VoiceCatalogEntry(
        voice_id=voice_id,
        name=name,
        language_code=language_code,
        language_name=language_code.split("_", 1)[0],
        country_name=None,
        quality="medium",
        num_speakers=1,
        model_url=f"https://example.test/{voice_id}.onnx",
        config_url=f"https://example.test/{voice_id}.onnx.json",
    )


def test_view_groups_entries_and_returns_selected_voice() -> None:
    assert _QT_APP is not None
    english = make_entry("en_US-lessac-medium", "lessac", "en_US")
    spanish = make_entry("es_ES-davefx-medium", "davefx", "es_ES")
    view = VoiceCatalogView()

    view.populate([spanish, english], set())

    assert view.tree.topLevelItemCount() == 2
    first_group = view.tree.topLevelItem(0)
    first_voice = first_group.child(0)
    view.tree.setCurrentItem(first_voice)

    assert view.selected_entry() is not None
    assert view.selected_entry().voice_id == "en_US-lessac-medium"
    assert view.install_button.isEnabled() is True

    view.close()


def test_view_disables_install_for_installed_voice_and_while_busy() -> None:
    assert _QT_APP is not None
    entry = make_entry("en_US-lessac-medium", "lessac", "en_US")
    view = VoiceCatalogView()

    view.populate([entry], {entry.voice_id})
    view.tree.setCurrentItem(view.tree.topLevelItem(0).child(0))
    assert view.install_button.isEnabled() is False

    view.populate([entry], set())
    view.tree.setCurrentItem(view.tree.topLevelItem(0).child(0))
    view.set_busy("Installing...", busy=True)
    assert view.refresh_button.isEnabled() is False
    assert view.install_button.isEnabled() is False

    view.close()
