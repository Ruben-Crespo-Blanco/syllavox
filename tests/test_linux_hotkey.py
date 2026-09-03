from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import syllavox.hotkey.linux_hotkey as linux_hotkey
from syllavox.hotkey.errors import HotkeyUnsupportedPlatformError


def test_portal_trigger_uses_xdg_modifier_names() -> None:
    binding = linux_hotkey.parse_hotkey("Ctrl+Alt+Shift+Win+R")

    assert linux_hotkey._portal_trigger(binding) == "CTRL+ALT+SHIFT+LOGO+R"


def test_portal_tokens_are_unique_and_safe_for_object_paths() -> None:
    first = linux_hotkey._new_portal_token("bind")
    second = linux_hotkey._new_portal_token("bind")

    assert first != second
    assert first.replace("_", "").isalnum()


def test_wayland_request_subscribes_before_immediate_portal_response() -> None:
    class FakeMessage:
        def __init__(self, **values) -> None:
            self.__dict__.update(values)

    class FakeBus:
        unique_name = ":1.42"

        def __init__(self) -> None:
            self.handlers = []

        def add_message_handler(self, handler) -> None:
            self.handlers.append(handler)

        def remove_message_handler(self, handler) -> None:
            self.handlers.remove(handler)

        async def call(self, message):
            token = message.body[0]["handle_token"]
            request_path = linux_hotkey._portal_request_path(
                self.unique_name,
                token,
            )
            response = SimpleNamespace(
                message_type=SimpleNamespace(name="SIGNAL"),
                path=request_path,
                interface=linux_hotkey.WAYLAND_REQUEST_INTERFACE,
                member="Response",
                body=[0, {"approved": True}],
            )
            for handler in list(self.handlers):
                handler(response)
            return SimpleNamespace(
                message_type=SimpleNamespace(name="METHOD_RETURN"),
                body=[request_path],
            )

    backend = linux_hotkey.LinuxWaylandGlobalHotkey.__new__(
        linux_hotkey.LinuxWaylandGlobalHotkey
    )
    backend._bus = FakeBus()
    backend._timeout_seconds = 0.1
    token = "syllavox_create_test"

    result = asyncio.run(
        backend._call_request(
            FakeMessage,
            object(),
            request_token=token,
            interface=linux_hotkey.WAYLAND_GLOBAL_SHORTCUTS_INTERFACE,
            member="CreateSession",
            signature="a{sv}",
            body=[{"handle_token": token}],
        )
    )

    assert result == {"approved": True}


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
