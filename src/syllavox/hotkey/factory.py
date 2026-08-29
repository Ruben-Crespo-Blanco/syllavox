"""Selection of the host platform's global-hotkey implementation."""

from __future__ import annotations

import sys
from collections.abc import Callable

from .backend import GlobalHotkeyBackend
from .errors import HotkeyUnsupportedPlatformError
from .parser import HotkeyBinding
from .win32_hotkey import Win32GlobalHotkey


HotkeyCallback = Callable[[], None]


class UnsupportedGlobalHotkey:
    """Explicit placeholder until a platform hotkey backend is implemented.

    Keeping unsupported platforms behind the same contract lets the rest of
    the application start normally and gives v0.5/v0.6 a narrow integration
    point for native macOS and Linux implementations.
    """

    def __init__(self, platform_name: str) -> None:
        self._platform_name = platform_name

    def register(self, hotkey: str) -> HotkeyBinding:
        raise HotkeyUnsupportedPlatformError(
            f"Global hotkeys are not implemented for {self._platform_name!r}."
        )

    def unregister(self) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def is_registered(self) -> bool:
        return False

    def current_hotkey(self) -> str | None:
        return None


def create_global_hotkey_backend(
    callback: HotkeyCallback,
) -> GlobalHotkeyBackend:
    """Create the host platform backend without leaking OS selection upward."""
    if sys.platform == "win32":
        return Win32GlobalHotkey(callback=callback)

    return UnsupportedGlobalHotkey(sys.platform)


__all__ = [
    "UnsupportedGlobalHotkey",
    "create_global_hotkey_backend",
]
