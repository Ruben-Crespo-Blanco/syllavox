"""macOS global-hotkey implementation using AppKit event monitors.

The AppKit import is lazy so Windows and Linux builds do not acquire a
PyObjC dependency. macOS may require the user to grant Input Monitoring or
Accessibility permission for global key events; registration failures are
reported through the existing hotkey status path.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from syllavox.hotkey.errors import (
    HotkeyRegistrationError,
    HotkeyUnsupportedPlatformError,
)
from syllavox.hotkey.parser import (
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_WIN,
    parse_hotkey,
)


HotkeyCallback = Callable[[], None]

_MAC_KEY_CODES = {
    "A": 0,
    "S": 1,
    "D": 2,
    "F": 3,
    "H": 4,
    "G": 5,
    "Z": 6,
    "X": 7,
    "C": 8,
    "V": 9,
    "B": 11,
    "Q": 12,
    "W": 13,
    "E": 14,
    "R": 15,
    "Y": 16,
    "T": 17,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "6": 22,
    "5": 23,
    "9": 25,
    "7": 26,
    "8": 28,
    "0": 29,
    "O": 31,
    "U": 32,
    "I": 34,
    "P": 35,
    "L": 37,
    "J": 38,
    "K": 40,
    "N": 45,
    "M": 46,
    "F1": 122,
    "F2": 120,
    "F3": 99,
    "F4": 118,
    "F5": 96,
    "F6": 97,
    "F7": 98,
    "F8": 100,
    "F9": 101,
    "F10": 109,
    "F11": 103,
    "F12": 111,
    "F13": 105,
    "F14": 107,
    "F15": 113,
    "F16": 106,
    "F17": 64,
    "F18": 79,
    "F19": 80,
    "F20": 90,
    "SPACE": 49,
    "ENTER": 36,
    "ESCAPE": 53,
    "TAB": 48,
    "BACKSPACE": 51,
    "DELETE": 117,
    "HOME": 115,
    "END": 119,
    "PAGEUP": 116,
    "PAGEDOWN": 121,
    "LEFT": 123,
    "RIGHT": 124,
    "DOWN": 125,
    "UP": 126,
}


def _load_appkit() -> Any:
    try:
        import AppKit
    except ImportError as exc:
        raise HotkeyUnsupportedPlatformError(
            "macOS global hotkeys require the optional 'macos' dependency "
            "(PyObjC)."
        ) from exc

    return AppKit


class MacOSGlobalHotkey:
    """Register one configurable shortcut with macOS event monitors."""

    def __init__(
        self,
        callback: HotkeyCallback,
        *,
        appkit: Any | None = None,
    ) -> None:
        self._callback = callback
        self._appkit = appkit
        self._global_monitor: Any | None = None
        self._local_monitor: Any | None = None
        self._binding: HotkeyBinding | None = None

    def register(self, hotkey: str) -> HotkeyBinding:
        self._require_macos()
        binding = parse_hotkey(hotkey)

        if self._binding == binding and self.is_registered():
            return binding

        self.unregister()
        appkit = self._appkit or _load_appkit()
        self._appkit = appkit
        event_class = getattr(appkit, "NSEvent", None)
        if event_class is None:
            raise HotkeyUnsupportedPlatformError(
                "The macOS AppKit event monitor is unavailable."
            )

        key_name = binding.display_name.split("+")[-1].upper()
        if key_name not in _MAC_KEY_CODES:
            raise HotkeyRegistrationError(
                f"The macOS global-hotkey backend does not support {key_name!r}."
            )

        event_mask = getattr(
            appkit,
            "NSEventMaskKeyDown",
            getattr(appkit, "NSKeyDownMask", 1 << 10),
        )

        try:
            self._global_monitor = (
                event_class.addGlobalMonitorForEventsMatchingMask_handler_(
                    event_mask,
                    self._on_global_event,
                )
            )
            self._local_monitor = (
                event_class.addLocalMonitorForEventsMatchingMask_handler_(
                    event_mask,
                    self._on_local_event,
                )
            )
        except Exception as exc:
            self.unregister()
            raise HotkeyRegistrationError(
                f"Could not register macOS global hotkey {binding.display_name!r}: "
                f" {exc}"
            ) from exc

        if self._global_monitor is None or self._local_monitor is None:
            self.unregister()
            raise HotkeyRegistrationError(
                "macOS did not grant keyboard-monitoring permission for the "
                "global hotkey. Enable Syllavox in System Settings > Privacy "
                "& Security > Input Monitoring, then try again."
            )

        self._binding = binding
        return binding

    def unregister(self) -> None:
        event_class = getattr(self._appkit, "NSEvent", None)
        for monitor in (self._global_monitor, self._local_monitor):
            if monitor is None or event_class is None:
                continue
            try:
                event_class.removeMonitor_(monitor)
            except Exception:
                pass

        self._global_monitor = None
        self._local_monitor = None
        self._binding = None

    def shutdown(self) -> None:
        self.unregister()

    def is_registered(self) -> bool:
        return (
            self._binding is not None
            and self._global_monitor is not None
            and self._local_monitor is not None
        )

    def current_hotkey(self) -> str | None:
        return self._binding.display_name if self._binding else None

    def _on_global_event(self, event: Any) -> None:
        if self._matches_event(event):
            self._invoke_callback()

    def _on_local_event(self, event: Any) -> Any:
        if self._matches_event(event):
            self._invoke_callback()
        return event

    def _matches_event(self, event: Any) -> bool:
        if self._binding is None:
            return False

        try:
            key_code = int(event.keyCode())
            flags = int(event.modifierFlags())
        except (AttributeError, TypeError, ValueError):
            return False

        key_name = self._binding.display_name.split("+")[-1].upper()
        expected_key_code = _MAC_KEY_CODES.get(key_name)
        if expected_key_code is None or key_code != expected_key_code:
            return False

        appkit = self._appkit or _load_appkit()
        mask = 0
        if self._binding.modifiers & MOD_CONTROL:
            mask |= int(getattr(appkit, "NSEventModifierFlagControl", 1 << 18))
        if self._binding.modifiers & MOD_ALT:
            mask |= int(getattr(appkit, "NSEventModifierFlagOption", 1 << 19))
        if self._binding.modifiers & MOD_SHIFT:
            mask |= int(getattr(appkit, "NSEventModifierFlagShift", 1 << 17))
        if self._binding.modifiers & MOD_WIN:
            mask |= int(getattr(appkit, "NSEventModifierFlagCommand", 1 << 20))

        modifier_mask = (
            int(getattr(appkit, "NSEventModifierFlagControl", 1 << 18))
            | int(getattr(appkit, "NSEventModifierFlagOption", 1 << 19))
            | int(getattr(appkit, "NSEventModifierFlagShift", 1 << 17))
            | int(getattr(appkit, "NSEventModifierFlagCommand", 1 << 20))
        )
        return flags & modifier_mask == mask

    def _invoke_callback(self) -> None:
        try:
            self._callback()
        except Exception:
            return

    @staticmethod
    def _require_macos() -> None:
        if sys.platform != "darwin":
            raise HotkeyUnsupportedPlatformError(
                "The macOS global-hotkey backend is available only on macOS."
            )


__all__ = ["MacOSGlobalHotkey"]
