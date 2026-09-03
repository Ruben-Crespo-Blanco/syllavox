from fastapi.testclient import TestClient
from syllavox.constants import DEFAULT_MAX_TEXT_LENGTH
from syllavox.state import AppState
from pathlib import Path
from tests.api_helpers import make_api_client


def make_test_client(tmp_path: Path) -> tuple[TestClient, object]:
    client, context, _, _ = make_api_client(tmp_path=tmp_path)
    return client, context


def test_status_returns_current_state(tmp_path: Path) -> None:
    client, context = make_test_client(tmp_path)

    response = client.get("/v1/status")

    assert response.status_code == 200

    payload = response.json()

    assert payload["state"] == "ready"
    assert payload["backend"]["name"] == "fake"
    assert payload["backend"]["healthy"] is True
    assert payload["error"] is None


def test_speak_accepts_valid_text(tmp_path: Path) -> None:
    client, context = make_test_client(tmp_path)

    response = client.post(
        "/v1/speak",
        json={"text": "Hello world"},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "accepted"
    assert payload["requestId"] is not None
    assert payload["error"] is None

    assert context.state_manager.state == AppState.SPEAKING


def test_speak_rejects_empty_text(tmp_path: Path) -> None:
    client, context = make_test_client(tmp_path)

    response = client.post(
        "/v1/speak",
        json={"text": "   "},
    )

    payload = response.json()

    assert payload["status"] == "rejected"
    assert payload["error"]["code"] == "EMPTY_TEXT"


def test_speak_rejects_text_too_long(tmp_path: Path) -> None:
    client, context = make_test_client(tmp_path)

    long_text = "A" * (DEFAULT_MAX_TEXT_LENGTH + 1)

    response = client.post(
        "/v1/speak",
        json={"text": long_text},
    )

    payload = response.json()

    assert payload["status"] == "rejected"
    assert payload["error"]["code"] == "INVALID_PAYLOAD"


def test_speak_preserves_request_id(tmp_path: Path) -> None:
    client, context = make_test_client(tmp_path)

    response = client.post(
        "/v1/speak",
        json={
            "text": "Hello",
            "requestId": "custom-id",
        },
    )

    payload = response.json()

    assert payload["requestId"] == "custom-id"


def test_client_request_id_is_not_used_as_an_artifact_name(tmp_path: Path) -> None:
    client, _context, backend, _audio_player = make_api_client(tmp_path=tmp_path)

    response = client.post(
        "/v1/speak",
        json={"text": "Hello", "requestId": "../outside"},
    )

    assert response.status_code == 200
    assert backend.last_request.request_id == "../outside"
    assert backend.last_request.artifact_id != "../outside"
    assert "/" not in backend.last_request.artifact_id


def test_stop_transitions_to_stopped(tmp_path: Path) -> None:
    client, context = make_test_client(tmp_path)

    client.post("/v1/speak", json={"text": "Hello"})

    response = client.post("/v1/stop")

    payload = response.json()

    assert payload["status"] == "stopped"
    assert context.state_manager.state == AppState.STOPPED


def test_stop_returns_idle_when_not_speaking(tmp_path: Path) -> None:
    client, context = make_test_client(tmp_path)

    response = client.post("/v1/stop")

    payload = response.json()

    assert payload["status"] == "idle"


def test_status_reports_paused_state(tmp_path: Path) -> None:
    client, context = make_test_client(tmp_path)

    client.post("/v1/speak", json={"text": "Hello"})
    client.post("/v1/pause")

    response = client.get("/v1/status")

    assert response.json()["state"] == "paused"
    assert context.state_manager.state == AppState.PAUSED


def test_voices_returns_backend_voices(tmp_path: Path) -> None:
    client, context = make_test_client(tmp_path)

    response = client.get("/v1/voices")

    assert response.status_code == 200

    payload = response.json()

    assert payload["voices"] == [
        {
            "voiceId": "fake-voice",
            "name": "Fake Voice",
            "language": "en",
        }
    ]
