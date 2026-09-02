from __future__ import annotations

import pytest

import syllavox.hotkey.factory as hotkey_factory
from syllavox.hotkey.errors import HotkeyUnsupportedPlatformError
from syllavox.hotkey.factory import UnsupportedGlobalHotkey


def test_unsupported_hotkey_backend_has_safe_noop_lifecycle() -> None:
    backend = UnsupportedGlobalHotkey("linux")

    assert backend.is_registered() is False
    assert backend.current_hotkey() is None
    backend.unregister()
    backend.shutdown()

    with pytest.raises(
        HotkeyUnsupportedPlatformError,
        match="not implemented for 'linux'",
    ):
        backend.register("Ctrl+Alt+R")


def test_hotkey_factory_keeps_windows_selection_isolated(monkeypatch) -> None:
    calls: list[object] = []

    class FakeWindowsBackend:
        def __init__(self, callback) -> None:
            calls.append(callback)

    monkeypatch.setattr(hotkey_factory.sys, "platform", "win32")
    monkeypatch.setattr(hotkey_factory, "Win32GlobalHotkey", FakeWindowsBackend)

    callback = lambda: None
    backend = hotkey_factory.create_global_hotkey_backend(callback)

    assert isinstance(backend, FakeWindowsBackend)
    assert calls == [callback]


def test_hotkey_factory_selects_macos_backend(monkeypatch) -> None:
    calls: list[object] = []

    class FakeMacOSBackend:
        def __init__(self, callback) -> None:
            calls.append(callback)

    monkeypatch.setattr(hotkey_factory.sys, "platform", "darwin")
    monkeypatch.setattr(hotkey_factory, "MacOSGlobalHotkey", FakeMacOSBackend)

    callback = lambda: None
    backend = hotkey_factory.create_global_hotkey_backend(callback)

    assert isinstance(backend, FakeMacOSBackend)
    assert calls == [callback]


def test_hotkey_factory_selects_linux_backend(monkeypatch) -> None:
    calls: list[object] = []

    class FakeLinuxBackend:
        def __init__(self, callback) -> None:
            calls.append(callback)

    monkeypatch.setattr(hotkey_factory.sys, "platform", "linux")
    monkeypatch.setattr(hotkey_factory, "LinuxGlobalHotkey", FakeLinuxBackend)

    callback = lambda: None
    backend = hotkey_factory.create_global_hotkey_backend(callback)

    assert isinstance(backend, FakeLinuxBackend)
    assert calls == [callback]
