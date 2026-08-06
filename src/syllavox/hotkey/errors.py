"""
Global hotkey exception types.

These errors represent registration and execution failures only.

They are independent from:
- UI
- clipboard handling
- TTS
- audio playback
"""


class HotkeyError(Exception):
    """
    Base exception for all hotkey-related failures.
    """


class HotkeyRegistrationError(HotkeyError):
    """
    Raised when a global hotkey cannot be registered.

    Examples:
    - shortcut already used by another application
    - OS registration failure
    - missing permissions
    """


class HotkeyUnsupportedPlatformError(HotkeyError):
    """
    Raised when global hotkeys are not supported
    on the current platform/backend.
    """


class HotkeyActionError(HotkeyError):
    """
    Raised when a registered hotkey fires,
    but executing its configured action fails.

    Examples:
    - clipboard unavailable
    - action callback failure
    """