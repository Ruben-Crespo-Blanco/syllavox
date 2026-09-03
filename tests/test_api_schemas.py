import pytest
from pydantic import ValidationError

from syllavox.api.schemas import (
    ApiError,
    BackendStatus,
    PlaybackControlResponse,
    SpeakRequest,
    SpeakResponse,
    StatusResponse,
    StopResponse,
    VoicesResponse,
)


def test_speak_request_parsing() -> None:
    request = SpeakRequest(
        text="Hello world",
        voiceId="en_US-test",
        requestId="abc123",
    )

    assert request.text == "Hello world"
    assert request.voiceId == "en_US-test"
    assert request.requestId == "abc123"


@pytest.mark.parametrize(
    "request_id",
    ("", "line\nbreak", "control\x00character", "x" * 129),
)
def test_speak_request_rejects_invalid_correlation_ids(request_id: str) -> None:
    with pytest.raises(ValidationError):
        SpeakRequest(text="Hello", requestId=request_id)


def test_speak_response_creation() -> None:
    response = SpeakResponse(
        status="accepted",
        requestId="abc123",
        error=None,
    )

    assert response.status == "accepted"
    assert response.requestId == "abc123"
    assert response.error is None


def test_api_error_creation() -> None:
    error = ApiError(
        code="TEXT_TOO_LONG",
        message="Text exceeds the limit.",
    )

    assert error.code == "TEXT_TOO_LONG"
    assert error.message == "Text exceeds the limit."


def test_status_response_creation() -> None:
    response = StatusResponse(
        state="ready",
        backend=BackendStatus(
            name="not_implemented",
            healthy=False,
        ),
        error=None,
    )

    assert response.state == "ready"
    assert response.backend.name == "not_implemented"
    assert response.backend.healthy is False
    assert response.error is None


def test_stop_response_creation() -> None:
    response = StopResponse(status="stopped")
    assert response.status == "stopped"


def test_playback_control_response_creation() -> None:
    paused = PlaybackControlResponse(status="paused")
    resumed = PlaybackControlResponse(status="resumed")

    assert paused.status == "paused"
    assert resumed.status == "resumed"


def test_voices_response_creation() -> None:
    response = VoicesResponse(voices=[])
    assert response.voices == []
