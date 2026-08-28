from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from syllavox.settings_schema import get_default_settings
from syllavox.tray.window_widgets import HotkeyEdit, SettingsPanel


_QT_APP = QApplication.instance() or QApplication([])


def test_hotkey_editor_canonicalizes_valid_shortcuts() -> None:
    editor = HotkeyEdit()

    assert editor.set_hotkey("meta+control+f10") is True
    assert editor.hotkey() == "Ctrl+Win+F10"


def test_hotkey_editor_rejects_invalid_shortcuts_without_replacing_value() -> None:
    editor = HotkeyEdit()

    assert editor.hotkey() == "Ctrl+Alt+R"
    assert editor.set_hotkey("Ctrl+Alt+F25") is False
    assert editor.hotkey() == "Ctrl+Alt+R"


def test_hotkey_editor_captures_keyboard_shortcuts() -> None:
    editor = HotkeyEdit()
    editor.show()
    editor.setFocus()

    QTest.keyClick(
        editor,
        Qt.Key.Key_S,
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier,
    )

    assert editor.hotkey() == "Ctrl+Alt+S"


def test_settings_panel_persists_selected_read_hotkey() -> None:
    panel = SettingsPanel()
    settings = get_default_settings()

    panel.hotkey_edit.set_hotkey("Ctrl+Shift+R")
    panel.write_settings(settings, voice_id=None)

    assert settings["hotkey"]["key"] == "Ctrl+Shift+R"


def test_settings_panel_exposes_visible_hotkey_apply_action() -> None:
    panel = SettingsPanel()
    applied: list[bool] = []
    panel.hotkey_apply_requested.connect(lambda: applied.append(True))

    panel.apply_hotkey_button.click()

    assert applied == [True]


def test_settings_panel_shows_restart_action_for_backend_change() -> None:
    panel = SettingsPanel()
    restart_requests: list[bool] = []
    panel.restart_requested.connect(lambda: restart_requests.append(True))

    assert panel.backend_restart_button.isHidden() is True

    panel.backend_combo.setCurrentIndex(1)

    assert panel.backend_restart_button.isHidden() is False
    assert panel.backend_restart_button.text() == "Restart to use Sherpa-ONNX"

    panel.backend_restart_button.click()
    assert restart_requests == [True]
