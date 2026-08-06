from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from syllavox.api.context import ApiContext
from syllavox.api.routes import create_router
from syllavox.constants import DEFAULT_MAX_TEXT_LENGTH
from syllavox.fakes import FakeAudioPlayer, FakeBackend
from syllavox.speech.controller import SpeechController
from syllavox.state import StateManager
from syllavox.tts.base import TTSBackend
from syllavox.tts.manager import TTSBackendManager


def make_api_context(
    *,
    tmp_path: Path | None = None,
    backend: TTSBackend | None = None,
    audio_player: FakeAudioPlayer | None = None,
    max_text_length: int = DEFAULT_MAX_TEXT_LENGTH,
    ready: bool = True,
) -> tuple[ApiContext, TTSBackend, FakeAudioPlayer]:
    if backend is None:
        audio_path = tmp_path / "fake.wav" if tmp_path is not None else Path("fake.wav")
        if tmp_path is not None:
            audio_path.write_bytes(b"fake wav")
        backend = FakeBackend(audio_path=audio_path)

    if audio_player is None:
        audio_player = FakeAudioPlayer()

    state_manager = StateManager()
    if ready:
        state_manager.mark_ready()

    backend_manager = TTSBackendManager(
        backend=backend,
        max_text_length=max_text_length,
    )
    logger = logging.getLogger("test")
    context = ApiContext(
        state_manager=state_manager,
        backend_manager=backend_manager,
        speech_controller=SpeechController(
            state_manager=state_manager,
            backend_manager=backend_manager,
            audio_player=audio_player,
            logger=logger,
        ),
        logger=logger,
    )

    return context, backend, audio_player


def make_api_client(
    *,
    tmp_path: Path | None = None,
    backend: TTSBackend | None = None,
    audio_player: FakeAudioPlayer | None = None,
    max_text_length: int = DEFAULT_MAX_TEXT_LENGTH,
    ready: bool = True,
) -> tuple[TestClient, ApiContext, TTSBackend, FakeAudioPlayer]:
    context, backend, audio_player = make_api_context(
        tmp_path=tmp_path,
        backend=backend,
        audio_player=audio_player,
        max_text_length=max_text_length,
        ready=ready,
    )
    app = FastAPI()
    app.include_router(create_router(context))
    return TestClient(app), context, backend, audio_player
