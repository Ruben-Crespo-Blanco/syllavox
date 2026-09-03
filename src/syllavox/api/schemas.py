"""
API request and response schemas.

Defines Pydantic models for:
- POST /v1/speak
- POST /v1/stop
- POST /v1/pause
- POST /v1/resume
- GET /v1/status
- GET /v1/voices
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str


class SpeakRequest(BaseModel):
    text: str = Field(..., description="Text to speak locally.")
    voiceId: str | None = Field(
        default=None,
        description="Optional voice identifier. Uses selected default voice if omitted.",
    )
    requestId: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[^\x00-\x1f\x7f]+$",
        description="Optional client-provided request identifier.",
    )


class SpeakResponse(BaseModel):
    status: Literal["accepted", "rejected"]
    requestId: str | None
    error: ApiError | None = None


class StopResponse(BaseModel):
    status: Literal["stopped", "idle"]


class PlaybackControlResponse(BaseModel):
    status: Literal["paused", "resumed", "idle"]


class BackendStatus(BaseModel):
    name: str
    healthy: bool
    details: str | None = None


class StatusResponse(BaseModel):
    state: Literal[
        "starting",
        "ready",
        "speaking",
        "paused",
        "stopped",
        "error",
    ]
    backend: BackendStatus
    error: ApiError | None = None


class Voice(BaseModel):
    voiceId: str
    name: str
    language: str


class VoicesResponse(BaseModel):
    voices: list[Voice]
