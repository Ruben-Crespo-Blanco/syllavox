"""
Audio playback exception types.

These exceptions are specific to the audio playback layer and are
independent from TTS backend errors.
"""

from __future__ import annotations


class PlaybackError(RuntimeError):
    """
    Base class for all playback-related errors.
    """


class AudioFileNotFoundError(PlaybackError):
    """
    Raised when the requested audio file does not exist.
    """


class PlaybackStartError(PlaybackError):
    """
    Raised when playback cannot be started.
    """
