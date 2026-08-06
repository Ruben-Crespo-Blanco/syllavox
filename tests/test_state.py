import pytest

from syllavox.state import (
    AppState,
    InvalidStateTransitionError,
    StateManager,
)


def test_initial_state_is_starting() -> None:
    manager = StateManager()
    assert manager.state == AppState.STARTING
    assert manager.error_message is None


def test_valid_transitions_succeed() -> None:
    manager = StateManager()

    manager.mark_ready()
    assert manager.state == AppState.READY

    manager.mark_speaking()
    assert manager.state == AppState.SPEAKING

    manager.mark_paused()
    assert manager.state == AppState.PAUSED

    manager.mark_speaking()
    assert manager.state == AppState.SPEAKING

    manager.mark_stopped()
    assert manager.state == AppState.STOPPED

    manager.mark_ready()
    assert manager.state == AppState.READY


@pytest.mark.parametrize(
    ("start_state", "target_state"),
    [
        (AppState.STARTING, AppState.SPEAKING),
        (AppState.STARTING, AppState.STOPPED),
        (AppState.READY, AppState.STARTING),
        (AppState.READY, AppState.STOPPED),
        (AppState.SPEAKING, AppState.READY),
        (AppState.SPEAKING, AppState.STARTING),
        (AppState.PAUSED, AppState.READY),
        (AppState.PAUSED, AppState.STARTING),
        (AppState.STOPPED, AppState.SPEAKING),
        (AppState.STOPPED, AppState.STARTING),
        (AppState.ERROR, AppState.SPEAKING),
        (AppState.ERROR, AppState.STOPPED),
        (AppState.ERROR, AppState.STARTING),
    ],
)
def test_invalid_transitions_are_rejected(
    start_state: AppState, target_state: AppState
) -> None:
    manager = StateManager()

    # Force manager into the desired start state using only legal transitions
    if start_state == AppState.READY:
        manager.mark_ready()
    elif start_state == AppState.SPEAKING:
        manager.mark_ready()
        manager.mark_speaking()
    elif start_state == AppState.STOPPED:
        manager.mark_ready()
        manager.mark_speaking()
        manager.mark_stopped()
    elif start_state == AppState.PAUSED:
        manager.mark_ready()
        manager.mark_speaking()
        manager.mark_paused()
    elif start_state == AppState.ERROR:
        manager.set_error("test error")

    with pytest.raises(InvalidStateTransitionError):
        manager.transition_to(target_state)


def test_any_state_can_transition_to_error() -> None:
    manager = StateManager()

    manager.set_error("startup failure")
    assert manager.state == AppState.ERROR
    assert manager.error_message == "startup failure"

    manager.clear_error()
    manager.mark_speaking()
    manager.set_error("playback failure")
    assert manager.state == AppState.ERROR
    assert manager.error_message == "playback failure"


def test_error_state_stores_error_details() -> None:
    manager = StateManager()

    manager.set_error("backend unhealthy")
    assert manager.state == AppState.ERROR
    assert manager.error_message == "backend unhealthy"


def test_clearing_error_returns_to_ready() -> None:
    manager = StateManager()

    manager.set_error("temporary failure")
    manager.clear_error()

    assert manager.state == AppState.READY
    assert manager.error_message is None


def test_clearing_error_when_not_in_error_is_rejected() -> None:
    manager = StateManager()

    with pytest.raises(InvalidStateTransitionError):
        manager.clear_error()


def test_transition_to_ready_clears_previous_error() -> None:
    manager = StateManager()

    manager.set_error("temporary failure")
    manager.clear_error()

    assert manager.state == AppState.READY
    assert manager.error_message is None


def test_snapshot_returns_current_state_and_error() -> None:
    manager = StateManager()
    snap = manager.snapshot()

    assert snap.state == AppState.STARTING
    assert snap.error_message is None

    manager.set_error("example")
    snap = manager.snapshot()

    assert snap.state == AppState.ERROR
    assert snap.error_message == "example"

def test_listener_is_called_after_valid_transition() -> None:
    manager = StateManager()
    snapshots = []

    manager.add_listener(snapshots.append)

    manager.mark_ready()

    assert len(snapshots) == 1
    assert snapshots[0].state == AppState.READY
    assert snapshots[0].error_message is None


def test_listener_is_not_called_after_invalid_transition() -> None:
    manager = StateManager()
    snapshots = []

    manager.add_listener(snapshots.append)

    with pytest.raises(InvalidStateTransitionError):
        manager.mark_speaking()

    assert snapshots == []


def test_listener_receives_error_snapshot() -> None:
    manager = StateManager()
    snapshots = []

    manager.add_listener(snapshots.append)

    manager.set_error("example failure")

    assert len(snapshots) == 1
    assert snapshots[0].state == AppState.ERROR
    assert snapshots[0].error_message == "example failure"


def test_remove_listener_stops_notifications() -> None:
    manager = StateManager()
    snapshots = []

    manager.add_listener(snapshots.append)
    manager.remove_listener(snapshots.append)

    manager.mark_ready()

    assert snapshots == []
