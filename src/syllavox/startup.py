"""User-controlled application startup registration.

Windows startup registration lives behind this small module so the settings
and application composition layers do not depend directly on the Windows
registry. The registration is per-user and opt-in; it does not require
administrator privileges and does not run the application as administrator.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .constants import PRODUCT_NAME


STARTUP_REGISTRY_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


class StartupRegistrationError(RuntimeError):
    """Raised when the requested startup registration cannot be changed."""


def is_startup_supported(platform_name: str | None = None) -> bool:
    """Return whether this host supports Syllavox's startup integration."""
    return (platform_name or sys.platform) == "win32"


def build_startup_command(
    *,
    executable: str | Path | None = None,
    arguments: Sequence[str] | None = None,
) -> str:
    """Build a Windows-safe command line for the Run registry value."""
    if executable is None:
        executable = sys.executable

    if arguments is None:
        arguments = () if getattr(sys, "frozen", False) else ("-m", "syllavox.main")

    return subprocess.list2cmdline([
        str(executable),
        *(str(argument) for argument in arguments),
    ])


def _load_registry_module() -> Any:
    """Import winreg only on the platform that provides it."""
    try:
        import winreg
    except ImportError as exc:
        raise StartupRegistrationError(
            "Windows startup integration is unavailable on this system."
        ) from exc

    return winreg


def set_startup_enabled(
    enabled: bool,
    *,
    command: str | None = None,
    registry_module: Any | None = None,
) -> None:
    """Enable or disable Syllavox for the current user's Windows startup.

    ``registry_module`` is an internal test seam; production callers should
    leave it unset so the standard Windows registry module is used.
    """
    if not is_startup_supported():
        if enabled:
            raise StartupRegistrationError(
                "Run on startup is currently available only on Windows."
            )
        return

    registry = registry_module or _load_registry_module()
    startup_command = command or build_startup_command()
    key = None

    try:
        if enabled:
            try:
                key = registry.OpenKey(
                    registry.HKEY_CURRENT_USER,
                    STARTUP_REGISTRY_SUBKEY,
                    0,
                    registry.KEY_SET_VALUE,
                )
            except FileNotFoundError:
                key = registry.CreateKey(
                    registry.HKEY_CURRENT_USER,
                    STARTUP_REGISTRY_SUBKEY,
                )
        else:
            try:
                key = registry.OpenKey(
                    registry.HKEY_CURRENT_USER,
                    STARTUP_REGISTRY_SUBKEY,
                    0,
                    registry.KEY_SET_VALUE,
                )
            except FileNotFoundError:
                return

        if enabled:
            registry.SetValueEx(
                key,
                PRODUCT_NAME,
                0,
                registry.REG_SZ,
                startup_command,
            )
        else:
            try:
                registry.DeleteValue(key, PRODUCT_NAME)
            except FileNotFoundError:
                pass
    except OSError as exc:
        action = "enable" if enabled else "disable"
        raise StartupRegistrationError(
            f"Could not {action} Syllavox on Windows startup: {exc}"
        ) from exc
    finally:
        if key is not None:
            try:
                registry.CloseKey(key)
            except OSError:
                pass


def sync_startup_registration(enabled: bool) -> None:
    """Reconcile the persisted preference with Windows startup registration."""
    if not is_startup_supported():
        return

    set_startup_enabled(enabled)


__all__ = [
    "STARTUP_REGISTRY_SUBKEY",
    "StartupRegistrationError",
    "build_startup_command",
    "is_startup_supported",
    "set_startup_enabled",
    "sync_startup_registration",
]
