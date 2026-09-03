"""Platform-specific protection against duplicate Syllavox instances."""

from __future__ import annotations

import ctypes
import hashlib
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QLockFile

from .platform_paths import get_platform_app_dir


INSTANCE_MUTEX_NAME = "Local\\Syllavox"
_ERROR_ALREADY_EXISTS = 183


if sys.platform == "win32":
    from ctypes import wintypes

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.CreateMutexW.argtypes = (
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    )
    _KERNEL32.CreateMutexW.restype = wintypes.HANDLE
    _KERNEL32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _KERNEL32.CloseHandle.restype = wintypes.BOOL
else:
    _KERNEL32 = None


class _WindowsMutex:
    """Small wrapper around the named Win32 mutex used by the app."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._handle: Any = None

    def acquire(self) -> bool:
        if self._handle is not None:
            return True

        if _KERNEL32 is None:  # pragma: no cover - defensive platform check
            raise RuntimeError("Windows mutex support is unavailable")

        ctypes.set_last_error(0)
        handle = _KERNEL32.CreateMutexW(None, False, self._name)
        if not handle:
            error_code = ctypes.get_last_error()
            raise OSError(
                error_code,
                f"Could not create application mutex: Win32 error {error_code}",
            )

        if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
            _KERNEL32.CloseHandle(handle)
            return False

        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is None:
            return

        if _KERNEL32 is not None:
            _KERNEL32.CloseHandle(self._handle)
        self._handle = None


class _QtLockFile:
    """Cross-platform fallback for development on non-Windows systems."""

    def __init__(self, name: str) -> None:
        lock_path = get_instance_lock_path(name)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_file = QLockFile(str(lock_path))
        self._acquired = False

    def acquire(self) -> bool:
        if self._acquired:
            return True

        self._acquired = self._lock_file.tryLock(0)
        return self._acquired

    def release(self) -> None:
        if not self._acquired:
            return

        self._lock_file.unlock()
        self._acquired = False


def get_instance_lock_path(
    name: str = INSTANCE_MUTEX_NAME,
    *,
    platform_name: str | None = None,
    environment: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return a collision-resistant lock path in the current user's data dir."""
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "syllavox"
    name_digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
    return (
        get_platform_app_dir(
            platform_name=platform_name,
            environment=environment,
            home=home,
        )
        / "runtime"
        / f"{safe_name}-{name_digest}.lock"
    )


class InstanceLock(Protocol):
    """Platform-neutral contract for the single-instance lock."""

    def acquire(self) -> bool:
        """Acquire the process lock, returning whether this is the owner."""
        ...

    def release(self) -> None:
        """Release the process lock."""
        ...


def create_instance_lock(name: str = INSTANCE_MUTEX_NAME) -> InstanceLock:
    """Select the host lock implementation behind one platform seam."""
    return _WindowsMutex(name) if sys.platform == "win32" else _QtLockFile(name)


class SingleInstanceGuard:
    """Own a per-user process-wide application guard."""

    def __init__(
        self,
        name: str = INSTANCE_MUTEX_NAME,
        implementation: InstanceLock | None = None,
    ) -> None:
        self._implementation = implementation or create_instance_lock(name)

    def acquire(self) -> bool:
        """Acquire the guard, returning ``False`` if another instance owns it."""
        return self._implementation.acquire()

    def release(self) -> None:
        """Release the guard; safe to call repeatedly."""
        self._implementation.release()


__all__ = [
    "INSTANCE_MUTEX_NAME",
    "InstanceLock",
    "SingleInstanceGuard",
    "create_instance_lock",
    "get_instance_lock_path",
]
