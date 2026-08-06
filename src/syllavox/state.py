"""
Application state model.

Defines:
- allowed application states
- legal state transitions
- state manager with optional error details
- state change listeners for UI updates

This module is intentionally independent of the GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class AppState(Enum):
    STARTING = "starting"
    READY = "ready"
    SPEAKING = "speaking"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state transition is attempted."""


_ALLOWED_TRANSITIONS: dict[AppState, set[AppState]] = {
    AppState.STARTING: {AppState.READY, AppState.ERROR},
    AppState.READY: {AppState.SPEAKING, AppState.ERROR},
    AppState.SPEAKING: {AppState.PAUSED, AppState.STOPPED, AppState.ERROR},
    AppState.PAUSED: {AppState.SPEAKING, AppState.STOPPED, AppState.ERROR},
    AppState.STOPPED: {AppState.READY, AppState.ERROR},
    AppState.ERROR: {AppState.READY, AppState.ERROR},
}


@dataclass(frozen=True)
class StateSnapshot:
    state: AppState
    error_message: Optional[str] = None


StateChangeListener = Callable[[StateSnapshot], None]


class StateManager:
    """
    Deterministic application state manager.

    Rules:
    - Only legal transitions are allowed.
    - Any state may transition to ERROR via set_error().
    - ERROR may transition back to READY via clear_error().
    - Listeners are notified after successful state changes.
    """

    def __init__(self) -> None:
        self._state: AppState = AppState.STARTING
        self._error_message: Optional[str] = None
        self._listeners: list[StateChangeListener] = []

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            state=self._state,
            error_message=self._error_message,
        )

    def add_listener(self, listener: StateChangeListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: StateChangeListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_listeners(self) -> None:
        snapshot = self.snapshot()

        for listener in list(self._listeners):
            listener(snapshot)

    def can_transition_to(self, new_state: AppState) -> bool:
        return new_state in _ALLOWED_TRANSITIONS[self._state]

    def transition_to(self, new_state: AppState) -> None:
        """
        Transition to a new state if legal.

        Transitioning to READY clears any previous error message.
        """
        if not self.can_transition_to(new_state):
            raise InvalidStateTransitionError(
                f"Cannot transition from {self._state.name} to {new_state.name}"
            )

        old_state = self._state
        self._state = new_state

        if new_state == AppState.READY:
            self._error_message = None

        if old_state != new_state:
            self._notify_listeners()

    def set_error(self, message: Optional[str] = None) -> None:
        """
        Transition to ERROR from any state and optionally store an error message.
        """
        old_state = self._state

        self._state = AppState.ERROR
        self._error_message = message

        if old_state != AppState.ERROR or message is not None:
            self._notify_listeners()

    def clear_error(self) -> None:
        """
        Recover from ERROR back to READY and clear the stored error message.
        """
        if self._state != AppState.ERROR:
            raise InvalidStateTransitionError(
                f"Cannot clear error when current state is {self._state.name}"
            )

        self._state = AppState.READY
        self._error_message = None
        self._notify_listeners()

    def mark_ready(self) -> None:
        self.transition_to(AppState.READY)

    def mark_speaking(self) -> None:
        self.transition_to(AppState.SPEAKING)

    def mark_stopped(self) -> None:
        self.transition_to(AppState.STOPPED)

    def mark_paused(self) -> None:
        self.transition_to(AppState.PAUSED)
