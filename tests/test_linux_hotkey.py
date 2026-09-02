from __future__ import annotations

from types import SimpleNamespace

import pytest

import syllavox.hotkey.linux_hotkey as linux_hotkey
from syllavox.hotkey.errors import HotkeyUnsupportedPlatformError


def test_portal_trigger_uses_xdg_modifier_names() -> None:
    binding = linux_hotkey.parse_hotkey("Ctrl+Alt+Shift+Win+R")

    assert linux_hotkey._portal_trigger(binding) == "CTRL+ALT+SHIFT+LOGO+R"


def test_linux_hotkey_selector_uses_wayland_factory(monkeypatch) -> None:
    calls: list[object] = []

    class FakeBackend:
        def __init__(self, callback) -> None:
            calls.append(callback)
            self.registered = None

        def register(self, hotkey):
            self.registered = hotkey
            return SimpleNamespace(display_name=hotkey)

        def unregister(self):
            self.registered = None

        def shutdown(self):
            self.registered = None

        def is_registered(self):
            return self.registered is not None

        def current_hotkey(self):
            return self.registered

    monkeypatch.setattr(linux_hotkey.sys, "platform", "linux")
    callback = lambda: None
    backend = linux_hotkey.LinuxGlobalHotkey(
        callback,
        environment={
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-0",
        },
        wayland_factory=FakeBackend,
    )

    binding = backend.register("Ctrl+Alt+R")

    assert binding.display_name == "Ctrl+Alt+R"
    assert backend.is_registered() is True
    assert calls == [callback]
    backend.shutdown()


def test_linux_hotkey_selector_rejects_sessions_without_display(monkeypatch) -> None:
    monkeypatch.setattr(linux_hotkey.sys, "platform", "linux")
    backend = linux_hotkey.LinuxGlobalHotkey(lambda: None, environment={})

    with pytest.raises(HotkeyUnsupportedPlatformError, match="DISPLAY"):
        backend.register("Ctrl+Alt+R")


def test_x11_hotkey_registration_uses_lock_variants(monkeypatch) -> None:
    class FakeX:
        ControlMask = 1
        Mod1Mask = 2
        ShiftMask = 4
        Mod4Mask = 8
        LockMask = 16
        Mod2Mask = 32
        GrabModeAsync = 64
        KeyPress = 2

    class FakeXK:
        @staticmethod
        def string_to_keysym(value):
            assert value == "r"
            return 42

    class FakeRoot:
        def __init__(self) -> None:
            self.grabs = []
            self.ungrabs = []

        def grab_key(self, *args):
            self.grabs.append(args)

        def ungrab_key(self, *args):
            self.ungrabs.append(args)

    class FakeDisplay:
        def __init__(self) -> None:
            self.root = FakeRoot()
            self.closed = False

        def screen(self):
            return SimpleNamespace(root=self.root)

        def keysym_to_keycode(self, keysym):
            assert keysym == 42
            return 15

        def sync(self):
            return None

        def next_event(self):
            raise RuntimeError("end test event stream")

        def close(self):
            self.closed = True

    display = FakeDisplay()
    monkeypatch.setattr(linux_hotkey.sys, "platform", "linux")
    backend = linux_hotkey.LinuxX11GlobalHotkey(
        lambda: None,
        display_factory=lambda: display,
        x_module=FakeX,
        xk_module=FakeXK,
    )

    backend.register("Ctrl+Alt+R")

    assert len(display.root.grabs) == 4
    assert all(grab[0] == 15 for grab in display.root.grabs)
    assert backend.is_registered() is True
    backend.unregister()
    assert len(display.root.ungrabs) == 4
    assert display.closed is True
