"""Platform-neutral contract for global hotkey implementations."""

from __future__ import annotations

from typing import Protocol

from .parser import HotkeyBinding


class GlobalHotkeyBackend(Protocol):
    """Operations required by the application-level hotkey manager."""

    def register(self, hotkey: str) -> HotkeyBinding:
        """Register a shortcut with the host operating system."""
        ...

    def unregister(self) -> None:
        """Release the active shortcut, if any."""
        ...

    def shutdown(self) -> None:
        """Release all operating-system resources."""
        ...

    def is_registered(self) -> bool:
        """Return whether a shortcut is currently registered."""
        ...

    def current_hotkey(self) -> str | None:
        """Return the canonical active shortcut, if any."""
        ...


__all__ = ["GlobalHotkeyBackend"]
