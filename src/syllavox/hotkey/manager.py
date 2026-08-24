"""
Application-level global hotkey manager.

This module maps a registered hotkey event to one of the supported app actions:

- speak_clipboard
- open_window

Platform-specific registration remains isolated in win32_hotkey.py.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from logging import Logger
from dataclasses import dataclass

from syllavox.hotkey.errors import HotkeyActionError, HotkeyRegistrationError, HotkeyUnsupportedPlatformError
from syllavox.hotkey.win32_hotkey import Win32GlobalHotkey


ActionCallback = Callable[[], None]

@dataclass(frozen=True)
class HotkeyStatus:
    enabled: bool
    registered: bool
    key: str | None
    message: str

class HotkeyAction(StrEnum):
    """
    Supported Phase 1 hotkey actions.
    """

    SPEAK_CLIPBOARD = "speak_clipboard"
    OPEN_WINDOW = "open_window"


class HotkeyManager:
    """
    Coordinates global hotkey registration and app-level action execution.

    The manager does not directly know how to:
    - read clipboard contents
    - synthesize speech
    - open the window

    Those behaviors are injected as callbacks.
    """

    def __init__(
        self,
        logger: Logger,
        speak_clipboard_callback: ActionCallback,
        open_window_callback: ActionCallback,
    ) -> None:
        self._logger = logger
        self._speak_clipboard_callback = speak_clipboard_callback
        self._open_window_callback = open_window_callback

        self._action = HotkeyAction.SPEAK_CLIPBOARD

        self._backend = Win32GlobalHotkey(
            callback=self._handle_hotkey_pressed,
        )
        self._status = HotkeyStatus(
            enabled=False,
            registered=False,
            key=None,
            message="Disabled",
            )

    def status(self) -> HotkeyStatus:
        return self._status
    
    def set_disabled(self) -> None:
        """
        Mark the hotkey as disabled by application settings.
        """
        self._status = HotkeyStatus(
            enabled=False,
            registered=False,
            key=None,
            message="Disabled",
        )

    def set_action(
        self,
        action: str | HotkeyAction,
    ) -> HotkeyAction:
        """
        Set the action triggered by the global hotkey.

        Raises HotkeyActionError for unsupported action values.
        """
        try:
            parsed_action = HotkeyAction(action)
        except ValueError as exc:
            raise HotkeyActionError(
                f"Unsupported hotkey action: {action!r}"
            ) from exc

        self._action = parsed_action

        self._logger.info(
            "Hotkey action configured: %s",
            parsed_action.value,
        )

        return parsed_action

    def current_action(self) -> HotkeyAction:
        """
        Return the currently configured action.
        """
        return self._action

    def register(
        self,
        hotkey: str,
    ) -> str:
        """
        Register the configured global hotkey.

        Returns the canonical display form of the registered shortcut.

        Registration failures are recorded in the manager status and then
        re-raised so the application bootstrap can log them without stopping
        the application.
        """
        try:
            binding = self._backend.register(hotkey)

        except (
            HotkeyRegistrationError,
            HotkeyUnsupportedPlatformError,
        ) as exc:
            self._status = HotkeyStatus(
                enabled=True,
                registered=False,
                key=hotkey,
                message=str(exc),
            )
            raise

        self._logger.info(
            "Global hotkey registered: %s",
            binding.display_name,
        )

        self._status = HotkeyStatus(
            enabled=True,
            registered=True,
            key=binding.display_name,
            message="Registered",
        )

        return binding.display_name

    def reconfigure(self, hotkey: str) -> str:
        """Replace the active shortcut and restore it if the new one fails."""
        previous_hotkey = self.current_hotkey()
        previous_status = self._status

        try:
            return self.register(hotkey)
        except (HotkeyRegistrationError, HotkeyUnsupportedPlatformError) as exc:
            if previous_hotkey and previous_status.registered:
                try:
                    restored_hotkey = self.register(previous_hotkey)
                except (
                    HotkeyRegistrationError,
                    HotkeyUnsupportedPlatformError,
                ) as restore_exc:
                    self._status = HotkeyStatus(
                        enabled=previous_status.enabled,
                        registered=False,
                        key=previous_hotkey,
                        message=(
                            f"New shortcut failed: {exc} Previous shortcut "
                            f"could not be restored: {restore_exc}"
                        ),
                    )
                else:
                    self._status = HotkeyStatus(
                        enabled=previous_status.enabled,
                        registered=True,
                        key=restored_hotkey,
                        message=f"Previous shortcut kept: {exc}",
                    )

            raise

    def unregister(self) -> None:
        """
        Unregister the current global hotkey.
        """
        self._backend.unregister()

    def shutdown(self) -> None:
        """
        Release all hotkey resources.

        Safe to call repeatedly.
        """
        self._backend.shutdown()

    def is_registered(self) -> bool:
        """
        Return whether the platform backend currently owns a hotkey.
        """
        return self._backend.is_registered()

    def current_hotkey(self) -> str | None:
        """
        Return the canonical registered shortcut, if any.
        """
        return self._backend.current_hotkey()

    def trigger_action(self) -> None:
        """
        Execute the currently selected action.

        Public primarily for deterministic tests. Normal runtime activation
        comes from the Win32 hotkey callback.
        """
        try:
            if self._action == HotkeyAction.SPEAK_CLIPBOARD:
                self._speak_clipboard_callback()

            elif self._action == HotkeyAction.OPEN_WINDOW:
                self._open_window_callback()

            else:
                raise HotkeyActionError(
                    f"Unsupported hotkey action: {self._action!r}"
                )

        except HotkeyActionError:
            raise

        except Exception as exc:
            raise HotkeyActionError(
                f"Hotkey action {self._action.value!r} failed."
            ) from exc

    def _handle_hotkey_pressed(self) -> None:
        """
        Handle an activation received from the platform backend.

        Exceptions cannot propagate through the Qt native event boundary.
        """
        if not self._status.enabled:
            self._logger.debug(
                "Ignoring global hotkey activation because hotkeys are disabled"
            )
            return

        if not self._status.registered:
            self._logger.debug(
                "Ignoring global hotkey activation because no hotkey is registered"
            )
            return

        self._logger.info(
            "Global hotkey pressed: action=%s",
            self._action.value,
        )

        try:
            self.trigger_action()
        except HotkeyActionError as exc:
            self._logger.exception(
                "Global hotkey action failed: action=%s error=%s",
                self._action.value,
                exc,
            )
