"""Linux system-voice provider backed by the optional eSpeak NG command.

eSpeak NG is intentionally treated as a host-provided system voice engine.
Syllavox discovers it through ``PATH`` and renders a validated WAV file from
the command line, so the base Piper application does not need to bundle it.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import wave
from collections.abc import Callable
from pathlib import Path
from tempfile import mkstemp
from typing import Any

from syllavox.constants import LINUX_ESPEAK_TTS_BACKEND
from syllavox.logging_config import get_logger
from syllavox.tts.base import (
    AudioRetention,
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    VoiceInfo,
)
from syllavox.tts.catalog_models import LANGUAGE_NAMES
from syllavox.tts.errors import (
    BackendUnavailableError,
    SynthesisFailedError,
    VoiceNotFoundError,
)
from syllavox.tts.paths import get_request_audio_path, get_retained_audio_path


ESPEAK_NG_COMMAND = "espeak-ng"
ESPEAK_VOICE_PREFIX = "linux_espeak_ng:"

# eSpeak NG prints columns in the form:
#   Pty Language Age/Gender VoiceName File Other Languages
#   5   en       M           en        English
_VOICE_LINE = re.compile(
    r"^\s*-?\d+\s+"
    r"(?P<language>[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)?)\s+"
    r"(?P<age_gender>\S+)\s+"
    r"(?P<voice>[A-Za-z0-9_.+-]+)"
    r"(?:\s+(?P<label>.+?))?\s*$"
)


def _stable_voice_id(voice_name: str, language_code: str) -> str:
    digest = hashlib.sha256(
        f"{voice_name}\x00{language_code}".encode("utf-8")
    ).hexdigest()
    return f"{ESPEAK_VOICE_PREFIX}{digest}"


def _normalize_language_code(value: str) -> str:
    parts = value.replace("_", "-").split("-")
    if len(parts) == 1:
        return parts[0].lower()

    language = parts[0].lower()
    remainder = [
        part.upper() if len(part) == 2 and part.isalpha() else part
        for part in parts[1:]
    ]
    return "-".join([language, *remainder])


def _error_text(error: BaseException) -> str:
    return str(error) or error.__class__.__name__


class LinuxESpeakProvider:
    """Discover eSpeak NG voices and render them into Syllavox WAV files."""

    def __init__(
        self,
        *,
        command_runner: Callable[..., Any] | None = None,
        command_exists: Callable[[str], str | None] | None = None,
    ) -> None:
        self._command_runner = command_runner or subprocess.run
        self._command_exists = command_exists or shutil.which
        self._voice_names: dict[str, str] = {}
        self._logger = get_logger(__name__)

    def backend_name(self) -> str:
        return LINUX_ESPEAK_TTS_BACKEND

    def health(self) -> BackendHealth:
        if not sys.platform.startswith("linux"):
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details="eSpeak NG system speech is available only on Linux.",
            )

        try:
            self._ensure_supported()
            voices = self.list_voices()
        except Exception as exc:
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details=f"eSpeak NG is unavailable: {_error_text(exc)}",
            )

        if not voices:
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details="No eSpeak NG voices are installed or visible.",
            )

        return BackendHealth(
            name=self.backend_name(),
            healthy=True,
            details=f"{len(voices)} eSpeak NG voice(s) available.",
        )

    def list_voices(self) -> list[VoiceInfo]:
        """Return voices reported by ``espeak-ng --voices``."""
        command = self._ensure_supported()
        result = self._run([command, "--voices"], input=None)
        output = getattr(result, "stdout", "") or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")

        discovered: list[VoiceInfo] = []
        voice_names: dict[str, str] = {}
        for line in str(output).splitlines():
            match = _VOICE_LINE.match(line)
            if match is None:
                continue

            language_code = _normalize_language_code(match.group("language"))
            language = language_code.split("-", 1)[0]
            voice_name = match.group("voice")
            voice_id = _stable_voice_id(voice_name, language_code)
            voice_names[voice_id] = voice_name
            discovered.append(
                VoiceInfo(
                    voice_id=voice_id,
                    name=voice_name,
                    language=language,
                    language_code=language_code,
                    language_name=LANGUAGE_NAMES.get(
                        language,
                        "Unknown language" if language == "und" else language.upper(),
                    ),
                    quality="eSpeak NG system voice",
                )
            )

        self._voice_names = voice_names
        return sorted(
            discovered,
            key=lambda voice: (
                (voice.language_name or voice.language).lower(),
                voice.language_code or "",
                voice.name.lower(),
                voice.voice_id,
            ),
        )

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Render text through eSpeak NG and validate the resulting WAV."""
        command = self._ensure_supported()
        voice_id = request.voice_id
        if voice_id is None:
            raise SynthesisFailedError(
                "eSpeak NG system speech requires a resolved voice ID."
            )

        voice_name = self._voice_names.get(voice_id)
        if voice_name is None:
            self.list_voices()
            voice_name = self._voice_names.get(voice_id)
        if voice_name is None:
            raise VoiceNotFoundError(voice_id)

        final_path = Path(
            request.output_path
            or (
                get_retained_audio_path(request.artifact_id)
                if request.retention == AudioRetention.RETAIN
                else get_request_audio_path(request.artifact_id)
            )
        )
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._temporary_path(final_path)

        try:
            self._run(
                [command, "--stdin", "-v", voice_name, "-w", str(temporary_path)],
                input=request.text,
            )
            self._validate_wav(temporary_path)
            os.replace(temporary_path, final_path)
            return SynthesisResult(
                request_id=request.request_id,
                voice_id=voice_id,
                audio_path=final_path,
                mime_type="audio/wav",
                retention=request.retention,
            )
        except VoiceNotFoundError:
            raise
        except Exception as exc:
            raise SynthesisFailedError(
                f"eSpeak NG system speech synthesis failed: {_error_text(exc)}"
            ) from exc
        finally:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                self._logger.debug(
                    "Could not remove temporary eSpeak NG file: %s",
                    temporary_path,
                    exc_info=True,
                )

    def shutdown(self) -> None:
        self._voice_names.clear()

    def _ensure_supported(self) -> str:
        if not sys.platform.startswith("linux"):
            raise BackendUnavailableError(
                "eSpeak NG system speech is available only on Linux."
            )

        command = self._command_exists(ESPEAK_NG_COMMAND)
        if not command:
            raise BackendUnavailableError(
                "eSpeak NG is not installed. Install the 'espeak-ng' system "
                "package and try again."
            )

        return str(command)

    def _run(self, command: list[str], *, input: str | None) -> Any:
        return self._command_runner(
            command,
            input=input,
            capture_output=True,
            text=True,
            check=True,
        )

    @staticmethod
    def _temporary_path(final_path: Path) -> Path:
        descriptor, path = mkstemp(
            prefix=f".{final_path.stem}-",
            suffix=".wav",
            dir=final_path.parent,
        )
        os.close(descriptor)
        return Path(path)

    @staticmethod
    def _validate_wav(path: Path) -> None:
        if not path.is_file() or path.stat().st_size <= 44:
            raise SynthesisFailedError(
                "eSpeak NG produced no usable WAV file."
            )

        try:
            with wave.open(str(path), "rb") as wav_file:
                if wav_file.getnchannels() != 1:
                    raise SynthesisFailedError(
                        "eSpeak NG produced non-mono WAV output."
                    )
                if wav_file.getsampwidth() != 2:
                    raise SynthesisFailedError(
                        "eSpeak NG produced non-16-bit WAV output."
                    )
                if wav_file.getnframes() <= 0:
                    raise SynthesisFailedError(
                        "eSpeak NG produced an empty WAV file."
                    )
        except (wave.Error, OSError) as exc:
            raise SynthesisFailedError(
                "eSpeak NG produced an invalid WAV file."
            ) from exc


__all__ = [
    "ESPEAK_NG_COMMAND",
    "ESPEAK_VOICE_PREFIX",
    "LinuxESpeakProvider",
]
