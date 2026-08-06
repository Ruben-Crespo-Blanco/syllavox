from pathlib import Path

from fastapi.testclient import TestClient

from syllavox.api.context import ApiContext
from syllavox.fakes import FakeBackend
from syllavox.tts.base import TTSBackend
from tests.api_helpers import make_api_client


def make_test_client(
    backend: TTSBackend,
    tmp_path: Path,
) -> tuple[TestClient, ApiContext]:
    client, context, _, _ = make_api_client(
        backend=backend,
        tmp_path=tmp_path,
    )
    return client, context


def test_status_reflects_backend_health(tmp_path: Path) -> None:
    client, _ = make_test_client(
        backend=FakeBackend(),
        tmp_path=tmp_path,
    )

    response = client.get("/v1/status")

    assert response.status_code == 200

    payload = response.json()

    assert payload["backend"]["name"] == "fake"
    assert payload["backend"]["healthy"] is True


def test_voices_returns_backend_voices(tmp_path: Path) -> None:
    client, _ = make_test_client(
        backend=FakeBackend(),
        tmp_path=tmp_path,
    )

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


def test_voices_returns_empty_list_when_backend_is_unavailable(
    tmp_path: Path,
) -> None:
    client, _ = make_test_client(
        backend=FakeBackend(healthy=False),
        tmp_path=tmp_path,
    )

    response = client.get("/v1/voices")

    assert response.status_code == 200
    assert response.json() == {"voices": []}


def test_speak_uses_backend_and_accepts_request(tmp_path: Path) -> None:
    audio_path = tmp_path / "fake.wav"
    audio_path.write_bytes(b"fake wav")

    client, _ = make_test_client(
        backend=FakeBackend(audio_path=audio_path),
        tmp_path=tmp_path,
    )

    response = client.post(
        "/v1/speak",
        json={
            "text": "Hello",
            "requestId": "abc123",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    
    print(payload)

    assert payload["status"] == "accepted"
    assert payload["requestId"] == "abc123"
    assert payload["error"] is None


def test_speak_maps_backend_unavailable_to_structured_error(
    tmp_path: Path,
) -> None:
    client, _ = make_test_client(
        backend=FakeBackend(healthy=False),
        tmp_path=tmp_path,
    )

    response = client.post(
        "/v1/speak",
        json={
            "text": "Hello",
            "requestId": "abc123",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "rejected"
    assert payload["requestId"] == "abc123"
    assert payload["error"]["code"] == "BACKEND_UNAVAILABLE"
