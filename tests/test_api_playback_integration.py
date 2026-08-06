from pathlib import Path

from fastapi.testclient import TestClient

from syllavox.api.context import ApiContext
from syllavox.state import AppState
from syllavox.fakes import FakeBackend, FakeAudioPlayer
from tests.api_helpers import make_api_client


def make_test_client(
    tmp_path: Path,
    audio_path: Path | None = None,
    audio_player: FakeAudioPlayer | None = None,
) -> tuple[TestClient, ApiContext, FakeBackend, FakeAudioPlayer]:
    if audio_path is None:
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake wav")

    backend = FakeBackend(audio_path=audio_path)
    return make_api_client(
        backend=backend,
        audio_player=audio_player,
        tmp_path=tmp_path,
    )


def test_speak_calls_playback_after_synthesis(tmp_path: Path) -> None:
    client, context, backend, audio_player = make_test_client(tmp_path)

    response = client.post(
        "/v1/speak",
        json={
            "text": "Hello",
            "requestId": "req-1",
        },
    )

    payload = response.json()

    assert payload["status"] == "accepted"
    assert payload["requestId"] == "req-1"

    assert len(backend.synthesis_calls) == 1
    assert backend.synthesis_calls[0].text == "Hello"

    assert audio_player.play_calls == [
        (backend.audio_path, "req-1")
    ]

    assert context.state_manager.state == AppState.SPEAKING


def test_stop_stops_active_playback(tmp_path: Path) -> None:
    client, context, _, audio_player = make_test_client(tmp_path)

    client.post(
        "/v1/speak",
        json={
            "text": "Hello",
            "requestId": "req-1",
        },
    )

    response = client.post("/v1/stop")

    payload = response.json()

    assert payload["status"] == "stopped"
    assert audio_player.stop_calls == 1
    assert audio_player.is_playing() is False
    assert context.state_manager.state == AppState.STOPPED


def test_pause_and_resume_control_active_playback(tmp_path: Path) -> None:
    client, context, _, audio_player = make_test_client(tmp_path)

    client.post(
        "/v1/speak",
        json={"text": "Hello", "requestId": "req-1"},
    )

    pause_response = client.post("/v1/pause")
    assert pause_response.json() == {"status": "paused"}
    assert audio_player.pause_calls == 1
    assert context.state_manager.state == AppState.PAUSED

    resume_response = client.post("/v1/resume")
    assert resume_response.json() == {"status": "resumed"}
    assert audio_player.resume_calls == 1
    assert context.state_manager.state == AppState.SPEAKING


def test_pause_and_resume_are_idle_safe(tmp_path: Path) -> None:
    client, context, _, _ = make_test_client(tmp_path)

    assert client.post("/v1/pause").json() == {"status": "idle"}
    assert client.post("/v1/resume").json() == {"status": "idle"}
    assert context.state_manager.state == AppState.READY


def test_second_speak_interrupts_previous_playback(tmp_path: Path) -> None:
    client, context, backend, audio_player = make_test_client(tmp_path)

    response_1 = client.post(
        "/v1/speak",
        json={
            "text": "First",
            "requestId": "req-1",
        },
    )

    response_2 = client.post(
        "/v1/speak",
        json={
            "text": "Second",
            "requestId": "req-2",
        },
    )

    assert response_1.json()["status"] == "accepted"
    assert response_2.json()["status"] == "accepted"

    assert audio_player.stop_calls == 1
    assert audio_player.play_calls == [
        (backend.audio_path, "req-1"),
        (backend.audio_path, "req-2"),
    ]

    assert context.state_manager.state == AppState.SPEAKING


def test_missing_audio_file_returns_structured_error(tmp_path: Path) -> None:
    missing_audio_path = tmp_path / "missing.wav"

    client, context, _, audio_player = make_test_client(
        tmp_path=tmp_path,
        audio_path=missing_audio_path,
    )

    response = client.post(
        "/v1/speak",
        json={
            "text": "Hello",
            "requestId": "req-1",
        },
    )

    payload = response.json()

    assert payload["status"] == "rejected"
    assert payload["requestId"] == "req-1"
    assert payload["error"]["code"] == "INTERNAL_ERROR"
    assert payload["error"]["message"] == "Playback failed."

    assert audio_player.play_calls == []
    assert context.state_manager.state == AppState.ERROR


def test_playback_completion_transitions_state_to_ready(tmp_path: Path) -> None:
    """
    The speech controller owns the natural-completion state transition.
    """
    client, context, _, _ = make_test_client(tmp_path)

    client.post(
        "/v1/speak",
        json={
            "text": "Hello",
            "requestId": "req-1",
        },
    )

    assert context.state_manager.state == AppState.SPEAKING

    context.speech_controller.handle_playback_finished("req-1")

    assert context.state_manager.state == AppState.READY
