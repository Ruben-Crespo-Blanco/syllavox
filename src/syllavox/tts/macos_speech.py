"""macOS system-voice provider.

The first macOS adapter deliberately uses Apple's built-in ``say`` and
``afconvert`` commands. This keeps the Syllavox bundle small and avoids a
second speech runtime dependency while still exposing the same validated WAV
contract as Piper, Sherpa-ONNX, and Windows SAPI.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import wave
from collections.abc import Callable
from pathlib import Path
from tempfile import mkstemp
from typing import Any

from syllavox.constants import MACOS_SYSTEM_TTS_BACKEND
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


MACOS_VOICE_PREFIX = "macos_system:"
SAY_PATH = "/usr/bin/say"
AFCONVERT_PATH = "/usr/bin/afconvert"
_VOICE_LINE = re.compile(
    r"^(?P<name>.+?)\s+(?P<locale>[A-Za-z]{2,3}(?:[-_][A-Za-z]{2,4})?)"
    r"(?:\s+#.*)?$"
)


def _stable_voice_id(voice_name: str, locale_code: str) -> str:
    digest = hashlib.sha256(
        f"{voice_name}\x00{locale_code}".encode("utf-8")
    ).hexdigest()
    return f"{MACOS_VOICE_PREFIX}{digest}"


def _normalize_locale(value: str) -> str:
    pieces = value.replace("_", "-").split("-")
    if len(pieces) == 1:
        return pieces[0].lower()

    language = pieces[0].lower()
    region = pieces[1]
    if len(region) == 2 and region.isalpha():
        region = region.upper()
    return "-".join([language, region, *pieces[2:]])


def _error_text(error: BaseException) -> str:
    return str(error) or error.__class__.__name__


class MacOSSystemSpeechProvider:
    """Discover macOS voices and render them to local WAV files."""

    def __init__(
        self,
        *,
        command_runner: Callable[..., Any] | None = None,
        command_exists: Callable[[str], bool] | None = None,
    ) -> None:
        self._command_runner = command_runner or subprocess.run
        self._command_exists = command_exists or os.path.isfile
        self._voice_names: dict[str, str] = {}
        self._logger = get_logger(__name__)

    def backend_name(self) -> str:
        return MACOS_SYSTEM_TTS_BACKEND

    def health(self) -> BackendHealth:
        if sys.platform != "darwin":
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details="macOS system speech is available only on macOS.",
            )

        try:
            self._ensure_supported()
            voices = self.list_voices()
        except Exception as exc:
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details=f"macOS system speech is unavailable: {_error_text(exc)}",
            )

        if not voices:
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details="No macOS system voices are installed or visible.",
            )

        return BackendHealth(
            name=self.backend_name(),
            healthy=True,
            details=f"{len(voices)} macOS system voice(s) available.",
        )

    def list_voices(self) -> list[VoiceInfo]:
        """Return the voices reported by ``say -v ?``."""
        self._ensure_supported()
        result = self._run(
            [SAY_PATH, "-v", "?"],
            input="",
        )
        output = getattr(result, "stdout", "") or ""
        stderr = getattr(result, "stderr", "") or ""
        if stderr:
            output = f"{output}\n{stderr}"
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")

        discovered: list[VoiceInfo] = []
        voice_names: dict[str, str] = {}
        for line in str(output).splitlines():
            match = _VOICE_LINE.match(line.strip())
            if match is None:
                continue

            voice_name = match.group("name").strip()
            language_code = _normalize_locale(match.group("locale"))
            language = language_code.split("-", 1)[0]
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
                    quality="macOS system voice",
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
        """Render text with ``say``, convert it to WAV, and validate it."""
        self._ensure_supported()
        voice_id = request.voice_id
        if voice_id is None:
            raise SynthesisFailedError(
                "macOS system speech requires a resolved voice ID."
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
                get_retained_audio_path(request.request_id)
                if request.retention == AudioRetention.RETAIN
                else get_request_audio_path(request.request_id)
            )
        )
        final_path.parent.mkdir(parents=True, exist_ok=True)
        aiff_path = self._temporary_path(final_path, ".aiff")
        wav_path = self._temporary_path(final_path, ".wav")

        try:
            self._run(
                [SAY_PATH, "-v", voice_name, "-o", str(aiff_path)],
                input=request.text,
            )
            self._run(
                [
                    AFCONVERT_PATH,
                    "-f",
                    "WAVE",
                    "-d",
                    "LEI16@22050",
                    "-c",
                    "1",
                    str(aiff_path),
                    str(wav_path),
                ],
                input=None,
            )
            self._validate_wav(wav_path)
            os.replace(wav_path, final_path)
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
                f"macOS system speech synthesis failed: {_error_text(exc)}"
            ) from exc
        finally:
            for path in (aiff_path, wav_path):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    self._logger.debug(
                        "Could not remove temporary macOS speech file: %s",
                        path,
                        exc_info=True,
                    )

    def shutdown(self) -> None:
        self._voice_names.clear()

    def _ensure_supported(self) -> None:
        if sys.platform != "darwin":
            raise BackendUnavailableError(
                "macOS system speech is available only on macOS."
            )

        missing = [
            path
            for path in (SAY_PATH, AFCONVERT_PATH)
            if not self._command_exists(path)
        ]
        if missing:
            raise BackendUnavailableError(
                "Required macOS speech command(s) are missing: "
                + ", ".join(missing)
            )

    def _run(self, command: list[str], *, input: str | None) -> Any:
        return self._command_runner(
            command,
            input=input,
            capture_output=True,
            text=True,
            check=True,
        )

    @staticmethod
    def _temporary_path(final_path: Path, suffix: str) -> Path:
        descriptor, path = mkstemp(
            prefix=f".{final_path.stem}-",
            suffix=suffix,
            dir=final_path.parent,
        )
        os.close(descriptor)
        return Path(path)

    @staticmethod
    def _validate_wav(path: Path) -> None:
        if not path.is_file() or path.stat().st_size <= 44:
            raise SynthesisFailedError(
                "macOS system speech produced no usable WAV file."
            )

        try:
            with wave.open(str(path), "rb") as wav_file:
                if wav_file.getnchannels() != 1:
                    raise SynthesisFailedError(
                        "macOS system speech produced non-mono WAV output."
                    )
                if wav_file.getsampwidth() != 2:
                    raise SynthesisFailedError(
                        "macOS system speech produced non-16-bit WAV output."
                    )
                if wav_file.getnframes() <= 0:
                    raise SynthesisFailedError(
                        "macOS system speech produced an empty WAV file."
                    )
        except (wave.Error, OSError) as exc:
            raise SynthesisFailedError(
                "macOS system speech produced an invalid WAV file."
            ) from exc


__all__ = ["MACOS_VOICE_PREFIX", "MacOSSystemSpeechProvider"]
