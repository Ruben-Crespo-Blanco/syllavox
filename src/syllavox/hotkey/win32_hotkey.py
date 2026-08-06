"""
Windows global hotkey implementation.

Uses the Win32 RegisterHotKey API through ctypes and receives WM_HOTKEY
messages through Qt's native event-filter mechanism.

This module:
- supports configurable hotkey strings
- performs no persistent Windows configuration
- safely unregisters hotkeys during shutdown
- automatically loses registration if the process crashes or terminates
"""

from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

from syllavox.hotkey.errors import (
    HotkeyRegistrationError,
    HotkeyUnsupportedPlatformError,
)
from syllavox.hotkey.parser import (
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
    MOD_WIN,
    MODIFIER_VALUES,
    NAMED_VIRTUAL_KEYS,
    parse_hotkey,
)


WM_HOTKEY = 0x0312

DEFAULT_HOTKEY_ID = 1

HotkeyCallback = Callable[[], None]


if sys.platform == "win32":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)

    _user32.RegisterHotKey.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    _user32.RegisterHotKey.restype = ctypes.c_bool

    _user32.UnregisterHotKey.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    _user32.UnregisterHotKey.restype = ctypes.c_bool
else:
    _user32 = None


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


class MSG(ctypes.Structure):
    """
    Win32 MSG structure used to inspect native Qt messages.
    """

    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_uint32),
        ("pt", POINT),
        ("lPrivate", ctypes.c_uint32),
    ]


class Win32HotkeyFilter(QAbstractNativeEventFilter):
    """
    Receives WM_HOTKEY through Qt's existing event loop.
    """

    def __init__(
        self,
        hotkey_id: int,
        callback: HotkeyCallback,
    ) -> None:
        super().__init__()
        self._hotkey_id = hotkey_id
        self._callback = callback

    def nativeEventFilter(
        self,
        event_type,
        message,
    ) -> tuple[bool, int]:
        try:
            message_address = int(message)
            native_message = ctypes.cast(
                message_address,
                ctypes.POINTER(MSG),
            ).contents
        except (TypeError, ValueError, OSError):
            return False, 0

        if (
            native_message.message == WM_HOTKEY
            and int(native_message.wParam) == self._hotkey_id
        ):
            self._callback()
            return True, 0

        return False, 0


class Win32GlobalHotkey:
    """
    Configurable Windows global-hotkey registration.

    Registration exists only while the current process is alive. No registry
    entries or permanent Windows settings are modified.
    """

    def __init__(
        self,
        callback: HotkeyCallback,
        hotkey_id: int = DEFAULT_HOTKEY_ID,
    ) -> None:
        self._callback = callback
        self._hotkey_id = hotkey_id

        self._registered = False
        self._binding: HotkeyBinding | None = None
        self._filter: Win32HotkeyFilter | None = None

    def register(self, hotkey: str) -> HotkeyBinding:
        """
        Register an arbitrary supported hotkey.

        If another hotkey is already registered by this object, it is safely
        unregistered first.

        Returns the parsed canonical binding.

        Raises:
            HotkeyUnsupportedPlatformError
            HotkeyRegistrationError
        """
        self._require_windows()

        binding = parse_hotkey(hotkey)

        if (
            self._registered
            and self._binding == binding
        ):
            return binding

        # Reconfiguration is deterministic: release the previous shortcut
        # before attempting the new one.
        self.unregister()

        application = QCoreApplication.instance()

        if application is None:
            raise HotkeyRegistrationError(
                "Cannot register global hotkey before the Qt application exists."
            )

        if _user32 is None:
            raise HotkeyUnsupportedPlatformError(
                "Win32 hotkey API is unavailable."
            )

        ctypes.set_last_error(0)

        success = _user32.RegisterHotKey(
            None,
            self._hotkey_id,
            binding.modifiers,
            binding.virtual_key,
        )

        if not success:
            error_code = ctypes.get_last_error()

            self._reset_state()

            raise HotkeyRegistrationError(
                "Failed to register global hotkey "
                f"{binding.display_name!r}. "
                f"The shortcut may already be in use. "
                f"Win32 error: {error_code}"
            )

        event_filter = Win32HotkeyFilter(
            hotkey_id=self._hotkey_id,
            callback=self._invoke_callback,
        )

        try:
            application.installNativeEventFilter(event_filter)
        except Exception as exc:
            # RegisterHotKey succeeded but Qt filter installation failed.
            # Immediately release the OS registration.
            _user32.UnregisterHotKey(
                None,
                self._hotkey_id,
            )
            self._reset_state()

            raise HotkeyRegistrationError(
                "The hotkey was registered with Windows, but the Qt event "
                "filter could not be installed."
            ) from exc

        self._filter = event_filter
        self._binding = binding
        self._registered = True

        return binding

    def unregister(self) -> None:
        """
        Unregister the active hotkey.

        This method is idempotent and safe to call repeatedly.
        """
        event_filter = self._filter
        application = QCoreApplication.instance()

        # Remove the Qt filter first, preventing new callbacks while the OS
        # registration is being released.
        if event_filter is not None and application is not None:
            try:
                application.removeNativeEventFilter(event_filter)
            except Exception:
                # Cleanup should remain best-effort and must not prevent the
                # OS registration from being released.
                pass

        if self._registered and _user32 is not None:
            try:
                _user32.UnregisterHotKey(
                    None,
                    self._hotkey_id,
                )
            finally:
                self._reset_state()
        else:
            self._reset_state()

    def shutdown(self) -> None:
        """
        Explicit lifecycle cleanup alias.

        Safe to connect to QApplication.aboutToQuit and safe to call again
        after qt_app.exec() returns.
        """
        self.unregister()

    def is_registered(self) -> bool:
        return self._registered

    def current_binding(self) -> HotkeyBinding | None:
        return self._binding

    def current_hotkey(self) -> str | None:
        if self._binding is None:
            return None

        return self._binding.display_name

    def _invoke_callback(self) -> None:
        """
        Run the configured callback without allowing callback exceptions to
        escape through Qt's native event-processing boundary.
        """
        try:
            self._callback()
        except Exception:
            # App-level HotkeyManager will later log and surface action
            # failures. Native event-filter callbacks must not propagate.
            return

    def _require_windows(self) -> None:
        if sys.platform != "win32":
            raise HotkeyUnsupportedPlatformError(
                "The Win32 global-hotkey backend is available only on Windows."
            )

    def _reset_state(self) -> None:
        self._registered = False
        self._binding = None
        self._filter = None

    def __del__(self) -> None:
        """
        Best-effort fallback only.

        Explicit shutdown through QApplication.aboutToQuit remains the primary
        cleanup mechanism.
        """
        try:
            self.shutdown()
        except Exception:
            pass
