"""
TTS model and temporary audio path helpers.
"""

from __future__ import annotations

from pathlib import Path

from syllavox.constants import (
    MODELS_DIR_NAME,
    PIPER_DIR_NAME,
    RETAINED_AUDIO_DIR_NAME,
    TMP_DIR_NAME,
)
from syllavox.paths import get_app_base_dir


def get_models_dir() -> Path:
    """
    Return the root runtime models directory.

    Example:
        %LOCALAPPDATA%/Syllavox/models
    """
    return get_app_base_dir() / MODELS_DIR_NAME


def get_piper_models_dir() -> Path:
    """
    Return the Piper models directory.

    Example:
        %LOCALAPPDATA%/Syllavox/models/piper
    """
    return get_models_dir() / PIPER_DIR_NAME


def get_tmp_dir() -> Path:
    """
    Return the temporary audio output directory.

    Example:
        %LOCALAPPDATA%/Syllavox/tmp
    """
    return get_app_base_dir() / TMP_DIR_NAME


def get_retained_audio_dir() -> Path:
    """Return the directory reserved for explicitly retained audio files."""
    return get_app_base_dir() / RETAINED_AUDIO_DIR_NAME


def ensure_tts_directories() -> None:
    """
    Create all required runtime TTS directories if missing.
    """
    get_models_dir().mkdir(parents=True, exist_ok=True)
    get_piper_models_dir().mkdir(parents=True, exist_ok=True)
    get_tmp_dir().mkdir(parents=True, exist_ok=True)
    get_retained_audio_dir().mkdir(parents=True, exist_ok=True)


def cleanup_temporary_audio_files() -> tuple[int, int]:
    """Remove leftover temporary WAV files from an earlier application run.

    Returns:
        A tuple containing ``(removed_count, failed_count)``.

    Retained audio is kept in a separate directory and is not considered by
    this cleanup.
    """
    tmp_dir = get_tmp_dir()

    if not tmp_dir.exists():
        return 0, 0

    removed_count = 0
    failed_count = 0

    for audio_path in tmp_dir.glob("*.wav"):
        try:
            audio_path.unlink(missing_ok=True)
            removed_count += 1
        except OSError:
            failed_count += 1

    return removed_count, failed_count


def get_request_audio_path(
    request_id: str,
) -> Path:
    """
    Return the WAV output path for a synthesis request.

    Example:
        %LOCALAPPDATA%/Syllavox/tmp/<request_id>.wav
    """
    filename = f"{request_id}.wav"

    return get_tmp_dir() / filename


def get_retained_audio_path(request_id: str) -> Path:
    """Return the path for an explicitly retained synthesis artifact."""
    filename = f"{request_id}.wav"
    return get_retained_audio_dir() / filename
