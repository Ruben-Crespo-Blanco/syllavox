"""Lazy registry for the speech engines exposed by the desktop UI."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass

from syllavox.constants import (
    DEFAULT_TTS_BACKEND,
    LINUX_ESPEAK_TTS_BACKEND,
    MACOS_SYSTEM_TTS_BACKEND,
    SHERPA_ONNX_TTS_BACKEND,
    WINDOWS_SAPI_TTS_BACKEND,
)
from syllavox.tts.base import TTSBackend
from syllavox.tts.errors import BackendUnavailableError


@dataclass(frozen=True)
class BackendDescriptor:
    """UI and factory metadata for one backend choice."""

    backend_id: str
    display_name: str
    is_system_backend: bool = False


_BACKEND_DESCRIPTORS = (
    BackendDescriptor(DEFAULT_TTS_BACKEND, "Piper (default)"),
    BackendDescriptor(SHERPA_ONNX_TTS_BACKEND, "Sherpa-ONNX"),
    BackendDescriptor(
        WINDOWS_SAPI_TTS_BACKEND,
        "Windows SAPI",
        is_system_backend=True,
    ),
    BackendDescriptor(
        MACOS_SYSTEM_TTS_BACKEND,
        "macOS system voices",
        is_system_backend=True,
    ),
    BackendDescriptor(
        LINUX_ESPEAK_TTS_BACKEND,
        "Linux system voices (eSpeak NG)",
        is_system_backend=True,
    ),
)


def normalize_backend_id(value: object) -> str:
    """Normalize persisted and UI backend values to their stable IDs."""
    return str(value or DEFAULT_TTS_BACKEND).strip().lower().replace("-", "_")


def backend_descriptors() -> list[BackendDescriptor]:
    """Return backend choices that can be presented in this environment."""
    descriptors = list(_BACKEND_DESCRIPTORS[:2])
    if sys.platform == "win32" and importlib.util.find_spec("comtypes"):
        descriptors.append(_BACKEND_DESCRIPTORS[2])
    if sys.platform == "darwin":
        descriptors.append(_BACKEND_DESCRIPTORS[3])
    if sys.platform.startswith("linux") and shutil.which("espeak-ng"):
        descriptors.append(_BACKEND_DESCRIPTORS[4])
    return descriptors


def get_backend_descriptor(backend_id: object) -> BackendDescriptor | None:
    normalized = normalize_backend_id(backend_id)
    return next(
        (
            descriptor
            for descriptor in _BACKEND_DESCRIPTORS
            if descriptor.backend_id == normalized
        ),
        None,
    )


def backend_display_name(backend_id: object) -> str:
    """Return the human-readable name used in settings and status messages."""
    descriptor = get_backend_descriptor(backend_id)
    if descriptor is not None:
        return descriptor.display_name.removesuffix(" (default)")
    return normalize_backend_id(backend_id)


def is_system_backend(backend_id: object) -> bool:
    descriptor = get_backend_descriptor(backend_id)
    return bool(descriptor and descriptor.is_system_backend)


def create_backend(
    backend_id: object,
    *,
    factories: dict[str, Callable[[], TTSBackend]] | None = None,
) -> TTSBackend:
    """Create a backend lazily so optional engines stay out of base imports."""
    normalized = normalize_backend_id(backend_id)
    if factories and normalized in factories:
        return factories[normalized]()

    if normalized == DEFAULT_TTS_BACKEND:
        from syllavox.tts.piper import PiperBackend

        return PiperBackend()

    if normalized == SHERPA_ONNX_TTS_BACKEND:
        from syllavox.tts.sherpa_onnx import SherpaOnnxBackend

        return SherpaOnnxBackend()

    if normalized == WINDOWS_SAPI_TTS_BACKEND:
        if sys.platform != "win32":
            raise BackendUnavailableError(
                "Windows SAPI is available only on Windows."
            )

        from syllavox.tts.system_speech import SystemSpeechBackend
        from syllavox.tts.windows_sapi import WindowsSapiProvider

        return SystemSpeechBackend(WindowsSapiProvider())

    if normalized == MACOS_SYSTEM_TTS_BACKEND:
        if sys.platform != "darwin":
            raise BackendUnavailableError(
                "macOS system speech is available only on macOS."
            )

        from syllavox.tts.macos_speech import MacOSSystemSpeechProvider
        from syllavox.tts.system_speech import SystemSpeechBackend

        return SystemSpeechBackend(MacOSSystemSpeechProvider())

    if normalized == LINUX_ESPEAK_TTS_BACKEND:
        if not sys.platform.startswith("linux"):
            raise BackendUnavailableError(
                "Linux eSpeak NG system speech is available only on Linux."
            )

        from syllavox.tts.linux_espeak import LinuxESpeakProvider
        from syllavox.tts.system_speech import SystemSpeechBackend

        return SystemSpeechBackend(LinuxESpeakProvider())

    raise BackendUnavailableError(f"Unknown TTS backend: {backend_id}")


__all__ = [
    "BackendDescriptor",
    "backend_descriptors",
    "backend_display_name",
    "create_backend",
    "get_backend_descriptor",
    "is_system_backend",
    "normalize_backend_id",
]
