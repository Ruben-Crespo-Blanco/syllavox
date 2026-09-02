from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import syllavox.tts.backend_registry as registry
import syllavox.startup as startup
from syllavox.constants import (
    LINUX_ESPEAK_TTS_BACKEND,
    MACOS_SYSTEM_TTS_BACKEND,
    WINDOWS_SAPI_TTS_BACKEND,
)
from syllavox.tray.voice_management_view import VoiceManagementView
from syllavox.tray.window_widgets import SettingsPanel, VoiceSelectorWidget
from syllavox.tts.base import VoiceInfo


_QT_APP = QApplication.instance() or QApplication([])


def test_settings_panel_exposes_sapi_with_a_generic_restart_message(monkeypatch) -> None:
    monkeypatch.setattr(registry.sys, "platform", "win32")
    monkeypatch.setattr(registry.importlib.util, "find_spec", lambda name: object())

    panel = SettingsPanel(active_backend="piper")
    index = panel.backend_combo.findData(WINDOWS_SAPI_TTS_BACKEND)
    panel.backend_combo.setCurrentIndex(index)

    assert index >= 0
    assert panel.backend_restart_button.text() == "Restart to use Windows SAPI"
    assert panel.backend_restart_button.isHidden() is False
    assert "installed in Windows" in panel.backend_hint_label.text()


def test_settings_panel_exposes_macos_system_speech(monkeypatch) -> None:
    monkeypatch.setattr(registry.sys, "platform", "darwin")
    monkeypatch.setattr(startup.sys, "platform", "darwin")

    panel = SettingsPanel(active_backend="piper")
    index = panel.backend_combo.findData(MACOS_SYSTEM_TTS_BACKEND)
    panel.backend_combo.setCurrentIndex(index)

    assert index >= 0
    assert panel.backend_restart_button.text() == (
        "Restart to use macOS system voices"
    )
    assert panel.run_on_startup_checkbox.isHidden() is False
    assert "installed in macOS" in panel.backend_hint_label.text()


def test_settings_panel_exposes_linux_espeak_system_speech(monkeypatch) -> None:
    monkeypatch.setattr(registry.sys, "platform", "linux")
    monkeypatch.setattr(registry.shutil, "which", lambda name: "/usr/bin/espeak-ng")

    panel = SettingsPanel(active_backend="piper")
    index = panel.backend_combo.findData(LINUX_ESPEAK_TTS_BACKEND)
    panel.backend_combo.setCurrentIndex(index)

    assert index >= 0
    assert panel.backend_restart_button.text() == (
        "Restart to use Linux system voices (eSpeak NG)"
    )
    assert "installed eSpeak NG package" in panel.backend_hint_label.text()


def test_system_voice_selector_hides_download_action() -> None:
    selector = VoiceSelectorWidget()

    selector.set_system_voice_mode(True)

    assert selector.find_button.isHidden() is True
    assert selector.manage_button.text() == "System voices…"


def test_system_voice_management_view_is_read_only() -> None:
    view = VoiceManagementView(system_voice_mode=True)
    voice = VoiceInfo(
        voice_id="windows_sapi:test",
        name="Example Voice",
        language="en",
        language_code="en-US",
        language_name="English",
        country_name="United States",
    )

    view.populate([voice], lambda _: 123, lambda _: True)

    assert view.tree.headerItem().text(2) == "Source"
    assert view.tree.topLevelItem(0).text(2) == "Windows SAPI"
    assert view.tree.topLevelItem(0).text(3) == "Available"
    assert view.load_button.isHidden() is True
    assert view.unload_button.isHidden() is True
    assert view.delete_button.isHidden() is True
    assert view.remove_resources_button.isHidden() is True
    assert "managed by the operating system" in view.intro_label.text()


def test_system_voice_management_view_uses_platform_voice_provider_name() -> None:
    view = VoiceManagementView(
        system_voice_mode=True,
        system_voice_name="macOS system voices",
    )

    voice = VoiceInfo(
        voice_id="macos_system:test",
        name="Alex",
        language="en",
        language_code="en-US",
        language_name="English",
    )
    view.populate([voice], lambda _: 123, lambda _: True)

    assert view.tree.topLevelItem(0).text(2) == "macOS system voices"
    assert "macOS system voices" in view.intro_label.text()
