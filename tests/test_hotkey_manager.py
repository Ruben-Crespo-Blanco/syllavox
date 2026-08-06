from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import pytest

import syllavox.hotkey.manager as manager_module
from syllavox.hotkey.errors import (
    HotkeyActionError,
    HotkeyRegistrationError,
)
from syllavox.hotkey.manager import (
    HotkeyAction,
    HotkeyManager,
)


@dataclass(frozen=True)
class FakeBinding:
    display_name: str


class FakeHotkeyBackend:
    """
    In-memory replacement for Win32GlobalHotkey.

    It never calls the operating system.
    """

    def __init__(
        self,
        callback: Callable[[], None],
    ) -> None:
        self.callback = callback
        self.registered = False
        self.hotkey: str | None = None
        self.shutdown_called = False
        self.registration_error: Exception | None = None

    def register(self, hotkey: str) -> FakeBinding:
        if self.registration_error is not None:
            raise self.registration_error

        self.registered = True
        self.hotkey = hotkey

        return FakeBinding(display_name=hotkey)

    def unregister(self) -> None:
        self.registered = False
        self.hotkey = None

    def shutdown(self) -> None:
        self.shutdown_called = True
        self.unregister()

    def is_registered(self) -> bool:
        return self.registered

    def current_hotkey(self) -> str | None:
        return self.hotkey

    def simulate_press(self) -> None:
        self.callback()


@pytest.fixture
def fake_backend_class(
    monkeypatch: pytest.MonkeyPatch,
) -> type[FakeHotkeyBackend]:
    monkeypatch.setattr(
        manager_module,
        "Win32GlobalHotkey",
        FakeHotkeyBackend,
    )
    return FakeHotkeyBackend


@pytest.fixture
def logger() -> logging.Logger:
    return logging.getLogger("tests.hotkey_manager")


def test_default_action_is_speak_clipboard(
    fake_backend_class: type[FakeHotkeyBackend],
    logger: logging.Logger,
) -> None:
    manager = HotkeyManager(
        logger=logger,
        speak_clipboard_callback=lambda: None,
        open_window_callback=lambda: None,
    )

    assert manager.current_action() == HotkeyAction.SPEAK_CLIPBOARD


def test_action_selection(
    fake_backend_class: type[FakeHotkeyBackend],
    logger: logging.Logger,
) -> None:
    manager = HotkeyManager(
        logger=logger,
        speak_clipboard_callback=lambda: None,
        open_window_callback=lambda: None,
    )

    result = manager.set_action("open_window")

    assert result == HotkeyAction.OPEN_WINDOW
    assert manager.current_action() == HotkeyAction.OPEN_WINDOW


def test_invalid_action_is_rejected(
    fake_backend_class: type[FakeHotkeyBackend],
    logger: logging.Logger,
) -> None:
    manager = HotkeyManager(
        logger=logger,
        speak_clipboard_callback=lambda: None,
        open_window_callback=lambda: None,
    )

    with pytest.raises(HotkeyActionError):
        manager.set_action("unsupported_action")


def test_successful_registration_updates_status(
    fake_backend_class: type[FakeHotkeyBackend],
    logger: logging.Logger,
) -> None:
    manager = HotkeyManager(
        logger=logger,
        speak_clipboard_callback=lambda: None,
        open_window_callback=lambda: None,
    )

    registered_name = manager.register("Ctrl+Alt+R")
    status = manager.status()

    assert registered_name == "Ctrl+Alt+R"
    assert status.enabled is True
    assert status.registered is True
    assert status.key == "Ctrl+Alt+R"
    assert status.message == "Registered"


def test_registration_failure_is_stored_and_propagated(
    fake_backend_class: type[FakeHotkeyBackend],
    logger: logging.Logger,
) -> None:
    manager = HotkeyManager(
        logger=logger,
        speak_clipboard_callback=lambda: None,
        open_window_callback=lambda: None,
    )

    backend = manager._backend
    assert isinstance(backend, FakeHotkeyBackend)

    backend.registration_error = HotkeyRegistrationError(
        "Hotkey is already in use"
    )

    with pytest.raises(
        HotkeyRegistrationError,
        match="already in use",
    ):
        manager.register("Ctrl+Alt+R")

    status = manager.status()

    assert status.enabled is True
    assert status.registered is False
    assert status.key == "Ctrl+Alt+R"
    assert "already in use" in status.message


def test_registration_failure_can_be_logged(
    fake_backend_class: type[FakeHotkeyBackend],
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    manager = HotkeyManager(
        logger=logger,
        speak_clipboard_callback=lambda: None,
        open_window_callback=lambda: None,
    )

    backend = manager._backend
    assert isinstance(backend, FakeHotkeyBackend)

    backend.registration_error = HotkeyRegistrationError(
        "Operating-system registration failed"
    )

    with caplog.at_level(logging.WARNING):
        try:
            manager.register("Ctrl+Alt+R")
        except HotkeyRegistrationError as exc:
            logger.warning(
                "Global hotkey registration failed: %s",
                exc,
            )

    assert "Global hotkey registration failed" in caplog.text
    assert "Operating-system registration failed" in caplog.text


def test_disabled_hotkey_does_nothing(
    fake_backend_class: type[FakeHotkeyBackend],
    logger: logging.Logger,
) -> None:
    speak_calls = 0
    window_calls = 0

    def speak_clipboard() -> None:
        nonlocal speak_calls
        speak_calls += 1

    def open_window() -> None:
        nonlocal window_calls
        window_calls += 1

    manager = HotkeyManager(
        logger=logger,
        speak_clipboard_callback=speak_clipboard,
        open_window_callback=open_window,
    )

    manager.set_disabled()

    backend = manager._backend
    assert isinstance(backend, FakeHotkeyBackend)

    backend.simulate_press()

    assert speak_calls == 0
    assert window_calls == 0
    assert manager.status().enabled is False


def test_registered_hotkey_dispatches_selected_action(
    fake_backend_class: type[FakeHotkeyBackend],
    logger: logging.Logger,
) -> None:
    speak_calls = 0

    def speak_clipboard() -> None:
        nonlocal speak_calls
        speak_calls += 1

    manager = HotkeyManager(
        logger=logger,
        speak_clipboard_callback=speak_clipboard,
        open_window_callback=lambda: None,
    )

    manager.register("Ctrl+Alt+R")

    backend = manager._backend
    assert isinstance(backend, FakeHotkeyBackend)

    backend.simulate_press()

    assert speak_calls == 1