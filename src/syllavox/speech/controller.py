"""
Shared text-to-speech orchestration.

SpeechController is the single application-level entry point for speaking text.

Both HTTP API requests and global-hotkey actions should use this controller
rather than independently coordinating synthesis, playback, and state.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import wraps
from logging import Logger
from pathlib import Path
import threading
from typing import Any, Callable, TypeVar

from syllavox.audio.errors import PlaybackError
from syllavox.audio.player import AudioPlayerPort
from syllavox.state import AppState, StateManager
from syllavox.tts.base import (
    AudioRetention,
    SynthesisRequest,
    SynthesisResult,
)
from syllavox.tts.errors import InvalidSynthesisRequestError
from syllavox.tts.manager import TTSBackendManager
from syllavox.text_formatting import normalize_for_speech


_ReturnT = TypeVar("_ReturnT")


def _serialized_command(
    method: Callable[..., _ReturnT],
) -> Callable[..., _ReturnT]:
    """Run one speech lifecycle command at a time, in arrival order."""

    @wraps(method)
    def synchronized(
        self: "SpeechController",
        *args: Any,
        **kwargs: Any,
    ) -> _ReturnT:
        with self._command_lock:
            return method(self, *args, **kwargs)

    return synchronized


class SpeechController:
    """
    Coordinate application-level speech behavior.

    Responsibilities:

    - validate input
    - interrupt current playback
    - move application state to SPEAKING
    - synthesize through TTSBackendManager
    - start playback through AudioPlayer
    - preserve a single speech path for API and hotkey actions
    """

    def __init__(
        self,
        state_manager: StateManager,
        backend_manager: TTSBackendManager,
        audio_player: AudioPlayerPort,
        logger: Logger,
    ) -> None:
        self._state_manager = state_manager
        self._backend_manager = backend_manager
        self._audio_player = audio_player
        self._logger = logger
        self._active_request_id: str | None = None
        self._command_lock = threading.RLock()
        self._completion_listeners: list[Callable[[str], None]] = []

    @_serialized_command
    def add_completion_listener(self, listener: Callable[[str], None]) -> None:
        """Register a callback for natural playback completion."""
        if listener not in self._completion_listeners:
            self._completion_listeners.append(listener)

    @_serialized_command
    def remove_completion_listener(self, listener: Callable[[str], None]) -> None:
        """Remove a previously registered completion callback."""
        if listener in self._completion_listeners:
            self._completion_listeners.remove(listener)

    @property
    @_serialized_command
    def active_request_id(self) -> str | None:
        """Return the request currently owned by the speech lifecycle."""
        return self._active_request_id

    @_serialized_command
    def speak(
        self,
        text: str,
        request_id: str,
        voice_id: str | None = None,
    ) -> SynthesisResult:
        """
        Synthesize and play text.

        A new request interrupts active playback. No queue is maintained.

        Exceptions from validation, synthesis, playback, or state transitions
        are allowed to propagate so the caller can map them to its own error
        format.
        """
        normalized_text = self._normalize_text(text)

        self._interrupt_active_playback(
            new_request_id=request_id,
        )

        self._ensure_speaking_state()

        try:
            result = self._backend_manager.synthesize(
                SynthesisRequest(
                    text=normalized_text,
                    request_id=request_id,
                    voice_id=voice_id,
                )
            )

            self._active_request_id = result.request_id

            self._audio_player.play(
                audio_path=result.audio_path,
                request_id=result.request_id,
                retention=result.retention,
            )

        except Exception as exc:
            self._active_request_id = None
            self._state_manager.set_error(str(exc))
            raise

        self._logger.info(
            "Speech synthesis and playback started: "
            "request_id=%s voice_id=%s audio_path=%s",
            result.request_id,
            result.voice_id,
            result.audio_path,
        )

        return result

    @_serialized_command
    def export_wav(
        self,
        text: str,
        output_path: Path,
        request_id: str,
        voice_id: str | None = None,
    ) -> SynthesisResult:
        """Synthesize text to an explicitly selected WAV destination.

        Export does not start playback or change the application speech state.
        The backend is responsible for removing partial output on failure.
        """
        normalized_text = self._normalize_text(text)

        result = self._backend_manager.synthesize(
            SynthesisRequest(
                text=normalized_text,
                request_id=request_id,
                voice_id=voice_id,
                retention=AudioRetention.RETAIN,
                output_path=Path(output_path),
            )
        )

        self._logger.info(
            "WAV export completed: request_id=%s voice_id=%s audio_path=%s",
            result.request_id,
            result.voice_id,
            result.audio_path,
        )

        return result

    @_serialized_command
    def stop(self) -> bool:
        """
        Stop active playback.

        Returns:
            True if active playback was stopped.
            False if playback was already idle.
        """
        current_request_id = self._audio_player.current_request_id()
        is_playing = self._audio_player.is_playing()
        is_paused = self._audio_player.is_paused()

        if (
            not is_playing
            and not is_paused
            and current_request_id is None
            and self._active_request_id is None
        ):
            return False

        request_id = current_request_id or self._active_request_id

        try:
            with self._playback_error_boundary():
                self._audio_player.stop()

                if self._state_manager.state in {
                    AppState.SPEAKING,
                    AppState.PAUSED,
                }:
                    self._state_manager.mark_stopped()
        finally:
            self._active_request_id = None

        self._logger.info(
            "Speech playback stopped: request_id=%s",
            request_id,
        )

        return True

    @_serialized_command
    def pause(self) -> bool:
        """Pause the active request without releasing its audio artifact."""
        if (
            self._state_manager.state != AppState.SPEAKING
            or self._active_request_id is None
            or not self._audio_player.is_playing()
        ):
            return False

        with self._playback_error_boundary():
            self._audio_player.pause()
            self._state_manager.mark_paused()

        self._logger.info(
            "Speech playback paused: request_id=%s",
            self._active_request_id,
        )
        return True

    @_serialized_command
    def resume(self) -> bool:
        """Resume the currently paused request."""
        if (
            self._state_manager.state != AppState.PAUSED
            or self._active_request_id is None
            or not self._audio_player.is_paused()
        ):
            return False

        with self._playback_error_boundary():
            self._audio_player.resume()
            self._state_manager.mark_speaking()

        self._logger.info(
            "Speech playback resumed: request_id=%s",
            self._active_request_id,
        )
        return True

    @_serialized_command
    def set_volume(self, volume: float) -> None:
        """Set the shared playback volume."""
        self._audio_player.set_volume(volume)

    @_serialized_command
    def volume(self) -> float:
        """Return the shared playback volume."""
        return self._audio_player.volume()

    @_serialized_command
    def set_playback_rate(self, rate: float) -> None:
        """Set the shared playback speed multiplier."""
        self._audio_player.set_playback_rate(rate)

    @_serialized_command
    def playback_rate(self) -> float:
        """Return the shared playback speed multiplier."""
        return self._audio_player.playback_rate()

    @_serialized_command
    def handle_playback_finished(self, request_id: str) -> None:
        """Apply a natural-completion event to the active speech request."""
        if request_id != self._active_request_id:
            self._logger.info(
                "Ignoring stale playback completion: request_id=%s active_request_id=%s",
                request_id,
                self._active_request_id,
            )
            return

        self._active_request_id = None

        self._logger.info(
            "Playback completed naturally: request_id=%s",
            request_id,
        )

        try:
            self._complete_playback_state()
        except Exception as exc:
            self._state_manager.set_error(str(exc))
            self._logger.warning(
                "Failed to transition to READY after playback completion: %s",
                exc,
            )
            return

        for listener in list(self._completion_listeners):
            try:
                listener(request_id)
            except Exception:
                self._logger.exception(
                    "Playback completion listener failed: request_id=%s",
                    request_id,
                )

    def _interrupt_active_playback(
        self,
        new_request_id: str,
    ) -> None:
        if not self._audio_player.is_playing():
            if (
                self._audio_player.current_request_id() is None
                and self._active_request_id is None
            ):
                return

        interrupted_request_id = (
            self._audio_player.current_request_id()
        )

        self._logger.info(
            "Interrupting active playback: "
            "interrupted_request_id=%s new_request_id=%s",
            interrupted_request_id,
            new_request_id,
        )

        try:
            self._audio_player.stop()

        except PlaybackError:
            self._active_request_id = None
            raise

        except Exception as exc:
            self._active_request_id = None
            raise PlaybackError(
                "Unable to interrupt current playback."
            ) from exc

        self._active_request_id = None

    def _ensure_speaking_state(self) -> None:
        current_state = self._state_manager.state

        if current_state == AppState.SPEAKING:
            return

        if current_state == AppState.ERROR:
            self._state_manager.clear_error()

        elif current_state == AppState.PAUSED:
            self._state_manager.mark_stopped()

        if self._state_manager.state == AppState.STOPPED:
            self._state_manager.mark_ready()

        self._state_manager.mark_speaking()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize input text and reject empty requests consistently."""
        normalized_text = normalize_for_speech(text)

        if not normalized_text:
            raise InvalidSynthesisRequestError("Text cannot be empty.")

        return normalized_text

    @contextmanager
    def _playback_error_boundary(self) -> Iterator[None]:
        """Record playback-operation failures in the application state."""
        try:
            yield
        except Exception as exc:
            self._state_manager.set_error(str(exc))
            raise

    def _complete_playback_state(self) -> None:
        """Return the application to READY after natural playback completion."""
        if self._state_manager.state in {
            AppState.SPEAKING,
            AppState.PAUSED,
        }:
            self._state_manager.mark_stopped()

        if self._state_manager.state == AppState.STOPPED:
            self._state_manager.mark_ready()
