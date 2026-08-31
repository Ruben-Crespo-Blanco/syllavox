from __future__ import annotations

from types import SimpleNamespace

import pytest

import syllavox.hotkey.macos_hotkey as macos_hotkey
from syllavox.hotkey.errors import HotkeyRegistrationError, HotkeyUnsupportedPlatformError


class FakeNSEvent:
    global_handler = None
    local_handler = None
    removed: list[object] = []

    @classmethod
    def addGlobalMonitorForEventsMatchingMask_handler_(cls, mask, handler):
        del mask
        cls.global_handler = handler
        return "global-monitor"

    @classmethod
    def addLocalMonitorForEventsMatchingMask_handler_(cls, mask, handler):
        del mask
        cls.local_handler = handler
        return "local-monitor"

    @classmethod
    def removeMonitor_(cls, monitor):
        cls.removed.append(monitor)


class FakeAppKit:
    NSEvent = FakeNSEvent
    NSEventMaskKeyDown = 1
    NSEventModifierFlagControl = 1 << 18
    NSEventModifierFlagOption = 1 << 19
    NSEventModifierFlagShift = 1 << 17
    NSEventModifierFlagCommand = 1 << 20


def test_macos_hotkey_matches_configured_command_modifier(monkeypatch) -> None:
    monkeypatch.setattr(macos_hotkey.sys, "platform", "darwin")
    triggered: list[bool] = []
    backend = macos_hotkey.MacOSGlobalHotkey(
        lambda: triggered.append(True),
        appkit=FakeAppKit,
    )

    binding = backend.register("Ctrl+Alt+R")
    event = SimpleNamespace(
        keyCode=lambda: 15,
        modifierFlags=lambda: (
            FakeAppKit.NSEventModifierFlagControl
            | FakeAppKit.NSEventModifierFlagOption
        ),
    )
    FakeNSEvent.global_handler(event)

    assert binding.display_name == "Ctrl+Alt+R"
    assert backend.is_registered() is True
    assert triggered == [True]

    backend.unregister()
    assert backend.is_registered() is False
    assert FakeNSEvent.removed[-2:] == ["global-monitor", "local-monitor"]


def test_macos_hotkey_reports_input_monitoring_permission_failure(
    monkeypatch,
) -> None:
    class PermissionDeniedNSEvent(FakeNSEvent):
        @classmethod
        def addGlobalMonitorForEventsMatchingMask_handler_(cls, mask, handler):
            del mask, handler
            return None

    class PermissionDeniedAppKit(FakeAppKit):
        NSEvent = PermissionDeniedNSEvent

    monkeypatch.setattr(macos_hotkey.sys, "platform", "darwin")
    backend = macos_hotkey.MacOSGlobalHotkey(
        lambda: None,
        appkit=PermissionDeniedAppKit,
    )

    with pytest.raises(HotkeyRegistrationError, match="Input Monitoring"):
        backend.register("Ctrl+Alt+R")


def test_macos_hotkey_rejects_key_without_a_macos_keycode(monkeypatch) -> None:
    monkeypatch.setattr(macos_hotkey.sys, "platform", "darwin")
    backend = macos_hotkey.MacOSGlobalHotkey(
        lambda: None,
        appkit=FakeAppKit,
    )

    with pytest.raises(HotkeyRegistrationError, match="does not support"):
        backend.register("Ctrl+Alt+F24")


def test_macos_hotkey_is_rejected_off_macos(monkeypatch) -> None:
    monkeypatch.setattr(macos_hotkey.sys, "platform", "win32")
    backend = macos_hotkey.MacOSGlobalHotkey(lambda: None, appkit=FakeAppKit)

    with pytest.raises(HotkeyUnsupportedPlatformError, match="only on macOS"):
        backend.register("Ctrl+Alt+R")
