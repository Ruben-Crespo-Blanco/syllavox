"""Platform-specific protection against duplicate Syllavox instances."""

from __future__ import annotations

import ctypes
import sys
import tempfile
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QLockFile


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
        safe_name = name.replace("\\", "_").replace("/", "_")
        lock_path = Path(tempfile.gettempdir()) / f"{safe_name}.lock"
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
]
