"""HTTP route definitions for the local application API."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from syllavox.api.context import ApiContext
from syllavox.api.errors import (
    ErrorCode,
    make_rejected_response,
    make_speech_error_response,
)
from syllavox.api.schemas import (
    ApiError,
    BackendStatus,
    PlaybackControlResponse,
    SpeakRequest,
    SpeakResponse,
    StatusResponse,
    StopResponse,
    Voice,
    VoicesResponse,
)
from syllavox.audio.errors import PlaybackError
from syllavox.constants import API_VERSION
from syllavox.request_ids import new_request_id
from syllavox.state import InvalidStateTransitionError
from syllavox.tts.errors import BackendUnavailableError


def create_router(context: ApiContext) -> APIRouter:
    """Create the API router with injected application services."""
    router = APIRouter(prefix=f"/{API_VERSION}")

    @router.get("/status", response_model=StatusResponse)
    def get_status() -> StatusResponse:
        error = None

        if context.state_manager.error_message:
            error = ApiError(
                code="APP_ERROR",
                message=context.state_manager.error_message,
            )

        backend_health = context.backend_manager.health()

        return StatusResponse(
            state=context.state_manager.state.value,
            backend=BackendStatus(
                name=backend_health.name,
                healthy=backend_health.healthy,
                details=backend_health.details,
            ),
            error=error,
        )

    @router.post("/speak", response_model=SpeakResponse)
    def post_speak(request: SpeakRequest) -> SpeakResponse | dict:
        request_id = _resolve_request_id(request.requestId)
        text = request.text.strip()

        if not text:
            return make_rejected_response(
                ErrorCode.EMPTY_TEXT,
                "Text cannot be empty.",
                request_id=request_id,
            )

        try:
            context.speech_controller.speak(
                text=text,
                request_id=request_id,
                voice_id=request.voiceId,
            )
        except Exception as exc:
            return make_speech_error_response(
                exc=exc,
                request_id=request_id,
                logger=context.logger,
            )

        return SpeakResponse(
            status="accepted",
            requestId=request_id,
            error=None,
        )

    @router.post("/stop", response_model=StopResponse)
    def post_stop() -> StopResponse:
        status = _execute_playback_control(
            context=context,
            action=context.speech_controller.stop,
            action_name="stop",
            success_status="stopped",
            idle_log_message=(
                "Stop request received while playback is idle. state=%s"
            ),
        )
        return StopResponse(status=status)

    @router.post("/pause", response_model=PlaybackControlResponse)
    def post_pause() -> PlaybackControlResponse:
        status = _execute_playback_control(
            context=context,
            action=context.speech_controller.pause,
            action_name="pause",
            success_status="paused",
            idle_log_message=(
                "Pause request received while playback is not active. state=%s"
            ),
        )
        return PlaybackControlResponse(status=status)

    @router.post("/resume", response_model=PlaybackControlResponse)
    def post_resume() -> PlaybackControlResponse:
        status = _execute_playback_control(
            context=context,
            action=context.speech_controller.resume,
            action_name="resume",
            success_status="resumed",
            idle_log_message=(
                "Resume request received while playback is not paused. state=%s"
            ),
        )
        return PlaybackControlResponse(status=status)

    @router.get("/voices", response_model=VoicesResponse)
    def get_voices() -> VoicesResponse:
        try:
            voices = context.backend_manager.list_voices()
        except BackendUnavailableError as exc:
            context.logger.warning("Voice listing unavailable: %s", exc)
            return VoicesResponse(voices=[])

        return VoicesResponse(
            voices=[
                Voice(
                    voiceId=voice.voice_id,
                    name=voice.name,
                    language=voice.language,
                )
                for voice in voices
            ]
        )

    return router


def _execute_playback_control(
    context: ApiContext,
    action: Callable[[], bool],
    *,
    action_name: str,
    success_status: str,
    idle_log_message: str,
) -> str:
    """Run a playback control action and return its API status."""
    try:
        performed = action()

    except PlaybackError as exc:
        context.logger.error("Failed to %s playback: %s", action_name, exc)
        return "idle"

    except InvalidStateTransitionError as exc:
        context.logger.warning(
            "Failed to transition after playback %s: %s",
            action_name,
            exc,
        )
        return "idle"

    if not performed:
        context.logger.info(
            idle_log_message,
            context.state_manager.state.value,
        )
        return "idle"

    return success_status


def _resolve_request_id(request_id: str | None) -> str:
    """Use the caller's request ID or generate one for the API request."""
    return request_id or new_request_id()
