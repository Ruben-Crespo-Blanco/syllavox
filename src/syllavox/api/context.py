"""
API-to-application bridge.

Provides the shared application services required by API routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger

from syllavox.speech.controller import SpeechController
from syllavox.state import StateManager
from syllavox.tts.manager import TTSBackendManager


@dataclass(frozen=True)
class ApiContext:
    """
    Shared application context for API routes.
    """

    state_manager: StateManager
    backend_manager: TTSBackendManager
    speech_controller: SpeechController
    logger: Logger
