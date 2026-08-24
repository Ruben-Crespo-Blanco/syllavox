"""Canonical application settings schema and merge rules."""

from __future__ import annotations

import copy
from typing import Any

from .constants import (
    CURRENT_CONFIG_SCHEMA_VERSION,
    DEFAULT_MAX_TEXT_LENGTH,
    DEFAULT_READ_HOTKEY,
)


def get_default_settings() -> dict[str, Any]:
    """Return a fresh default settings structure."""
    return {
        "version": CURRENT_CONFIG_SCHEMA_VERSION,
        "window": {
            "width": 720,
            "height": 720,
            "remember_position": True,
        },
        "ui": {
            "start_minimized_to_tray": True,
        },
        "hotkey": {
            "enabled": True,
            "key": DEFAULT_READ_HOTKEY,
            "action": "speak_clipboard",
        },
        "tts": {
            "backend": "piper",
            "voice_id": None,
            "max_text_length": DEFAULT_MAX_TEXT_LENGTH,
        },
        "playback": {
            "volume": 1.0,
            "rate": 1.0,
        },
    }


def merge_with_defaults(
    defaults: dict[str, Any],
    loaded: dict[str, Any],
) -> dict[str, Any]:
    """Merge persisted values into defaults while preserving future keys."""
    result = copy.deepcopy(defaults)

    for key, loaded_value in loaded.items():
        if key in result:
            default_value = result[key]
            if isinstance(default_value, dict) and isinstance(loaded_value, dict):
                result[key] = merge_with_defaults(default_value, loaded_value)
            else:
                result[key] = copy.deepcopy(loaded_value)
        else:
            result[key] = copy.deepcopy(loaded_value)

    return result


__all__ = ["get_default_settings", "merge_with_defaults"]
