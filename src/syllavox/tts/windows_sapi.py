"""Windows Speech API (SAPI) system-voice provider.

The COM dependency is deliberately imported only when the provider is used.
That keeps the module importable on future macOS and Linux builds and keeps
the base Piper portable build free of SAPI runtime files.
"""

from __future__ import annotations

import hashlib
import locale
import os
import re
import sys
import threading
import wave
from contextlib import contextmanager
from collections.abc import Callable, Iterator
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from syllavox.constants import WINDOWS_SAPI_TTS_BACKEND
from syllavox.logging_config import get_logger
from syllavox.tts.base import (
    AudioRetention,
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    VoiceInfo,
)
from syllavox.tts.errors import (
    BackendUnavailableError,
    SynthesisFailedError,
    VoiceNotFoundError,
)
from syllavox.tts.catalog_models import LANGUAGE_NAMES
from syllavox.tts.paths import get_request_audio_path, get_retained_audio_path


SAPI_VOICE_PREFIX = "windows_sapi:"
_SAPI_FILE_CREATE_FOR_WRITE = 3
_SAPI_DEFAULT_FORMAT_TYPE = 22  # SAFT22kHz16BitMono
_LOCALE_PATTERN = re.compile(r"\b([a-z]{2,3})[-_]([a-z]{2})\b", re.IGNORECASE)
_HEX_PATTERN = re.compile(r"^(?:0x)?[0-9a-f]+$", re.IGNORECASE)


def _load_comtypes() -> Any:
    """Load comtypes lazily and return its top-level module."""
    try:
        import comtypes
    except ImportError as exc:
        raise BackendUnavailableError(
            "Windows SAPI support requires the optional 'sapi' dependency "
            "(comtypes)."
        ) from exc

    return comtypes


def _create_com_object(progid: str) -> Any:
    """Create one SAPI COM object without importing comtypes at module load."""
    try:
        from comtypes.client import CreateObject
    except ImportError as exc:
        raise BackendUnavailableError(
            "Windows SAPI support requires the optional 'sapi' dependency "
            "(comtypes)."
        ) from exc

    return CreateObject(progid)


def _stable_voice_id(token_id: str) -> str:
    digest = hashlib.sha256(token_id.encode("utf-8")).hexdigest()
    return f"{SAPI_VOICE_PREFIX}{digest}"


def _format_sapi_error(error: BaseException) -> str:
    """Add a useful hexadecimal HRESULT when comtypes exposes one."""
    hresult = getattr(error, "hresult", None)
    if isinstance(hresult, int):
        return f"{error} (HRESULT 0x{hresult & 0xFFFFFFFF:08X})"
    return str(error)


def _normalize_locale_code(value: str) -> str:
    """Normalize a locale value into a compact BCP-47-style spelling."""
    pieces = value.replace("_", "-").split("-")
    if not pieces or not pieces[0]:
        return "und"

    language = pieces[0].lower()
    if len(pieces) == 1:
        return language

    region = pieces[1]
    if len(region) == 2 and region.isalpha():
        region = region.upper()
    return "-".join([language, region, *pieces[2:]])


def _locale_from_sapi_attribute(value: object) -> str | None:
    """Convert SAPI's hexadecimal LCID attribute into a locale code."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # SAPI can expose more than one language, separated by commas or
    # semicolons. The first one is the primary voice language.
    text = re.split(r"[,;\s]+", text, maxsplit=1)[0]
    if not _HEX_PATTERN.match(text):
        return _normalize_locale_code(text) if _LOCALE_PATTERN.search(text) else None

    candidates: list[int] = []
    try:
        candidates.append(int(text, 16))
    except ValueError:
        pass
    if text.isdigit():
        try:
            candidates.append(int(text, 10))
        except ValueError:
            pass

    for lcid in candidates:
        locale_value = locale.windows_locale.get(lcid)
        if locale_value:
            return _normalize_locale_code(locale_value)

    return None


def _locale_from_text(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        match = _LOCALE_PATTERN.search(str(value))
        if match:
            return _normalize_locale_code(
                f"{match.group(1)}-{match.group(2)}"
            )
    return None


def _country_from_description(description: str) -> str | None:
    """Extract a human-readable country suffix from common SAPI labels."""
    match = re.search(r"\(([^()]+)\)\s*$", description)
    if not match:
        return None

    candidate = match.group(1).strip()
    if _LOCALE_PATTERN.fullmatch(candidate) or re.fullmatch(
        r"[a-z]{2,3}", candidate, re.IGNORECASE
    ):
        return None
    return candidate or None


def _language_metadata(
    language_attribute: object,
    description: str,
    token_id: str,
) -> tuple[str, str, str | None, str | None]:
    """Return language family, locale code, readable name, and country."""
    language_code = _locale_from_sapi_attribute(language_attribute)
    if language_code is None:
        language_code = _locale_from_text(description, token_id) or "und"

    family = language_code.split("-", 1)[0].lower()
    language_name = LANGUAGE_NAMES.get(family)
    if language_name is None:
        language_name = "Unknown language" if family == "und" else family.upper()

    return (
        family,
        language_code,
        language_name,
        _country_from_description(description),
    )


def _safe_token_value(token: Any, attribute: str) -> str | None:
    try:
        value = token.GetAttribute(attribute)
    except Exception:
        return None

    if value is None:
        return None
    text = str(value).strip()
    return text or None


class WindowsSapiProvider:
    """Enumerate Windows SAPI voices and render speech through SAPI COM."""

    def __init__(
        self,
        *,
        object_factory: Callable[[str], Any] | None = None,
        com_module: Any | None = None,
    ) -> None:
        self._object_factory = object_factory
        self._com_module = com_module
        self._voice_tokens: dict[str, str] = {}
        self._lock = threading.RLock()
        self._logger = get_logger(__name__)

    def backend_name(self) -> str:
        return WINDOWS_SAPI_TTS_BACKEND

    def health(self) -> BackendHealth:
        """Return a non-raising availability check for Windows SAPI."""
        if sys.platform != "win32":
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details="Windows SAPI is available only on Windows.",
            )

        try:
            voices = self.list_voices()
        except Exception as exc:
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details=f"Windows SAPI is unavailable: {_format_sapi_error(exc)}",
            )

        if not voices:
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details=(
                    "No Windows SAPI voices are installed or visible to "
                    "the current user."
                ),
            )

        return BackendHealth(
            name=self.backend_name(),
            healthy=True,
            details=f"{len(voices)} Windows SAPI voice(s) available.",
        )

    def list_voices(self) -> list[VoiceInfo]:
        """Return readable metadata for installed SAPI voice tokens."""
        self._ensure_supported()

        with self._lock, self._com_session():
            voice = self._create_object("SAPI.SpVoice")
            tokens = voice.GetVoices()
            count = int(tokens.Count)
            discovered: list[VoiceInfo] = []
            token_ids: dict[str, str] = {}

            for index in range(count):
                token = tokens.Item(index)
                token_id = str(getattr(token, "Id", "")).strip()
                if not token_id:
                    continue

                description = str(
                    getattr(token, "GetDescription", lambda: "")()
                    or token_id
                ).strip()
                family, language_code, language_name, country_name = (
                    _language_metadata(
                        _safe_token_value(token, "Language"),
                        description,
                        token_id,
                    )
                )
                voice_id = _stable_voice_id(token_id)
                token_ids[voice_id] = token_id
                discovered.append(
                    VoiceInfo(
                        voice_id=voice_id,
                        name=description,
                        language=family,
                        language_code=language_code,
                        language_name=language_name,
                        country_name=country_name,
                        quality="Windows SAPI",
                    )
                )

            self._voice_tokens = token_ids
            return sorted(
                discovered,
                key=lambda item: (
                    (item.language_name or item.language).lower(),
                    (item.country_name or "").lower(),
                    item.name.lower(),
                    item.voice_id,
                ),
            )

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Render one request to a validated WAV file through SpFileStream."""
        self._ensure_supported()
        voice_id = request.voice_id
        if voice_id is None:
            raise SynthesisFailedError(
                "Windows SAPI synthesis requires a resolved voice ID."
            )

        with self._lock:
            token_id = self._voice_tokens.get(voice_id)
            if token_id is None:
                self.list_voices()
                token_id = self._voice_tokens.get(voice_id)
            if token_id is None:
                raise VoiceNotFoundError(voice_id)

            final_path, working_path = self._prepare_output_paths(request)
            stream: Any | None = None
            try:
                with self._com_session():
                    try:
                        voice = self._create_object("SAPI.SpVoice")
                        token = self._find_token(voice.GetVoices(), token_id)
                        if token is None:
                            raise VoiceNotFoundError(voice_id)

                        voice.Voice = token
                        stream = self._create_object("SAPI.SpFileStream")
                        stream.Open(
                            str(working_path),
                            _SAPI_FILE_CREATE_FOR_WRITE,
                            False,
                        )
                        self._configure_stream(stream)
                        voice.AudioOutputStream = stream
                        voice.Speak(request.text, 0)
                    finally:
                        if stream is not None:
                            try:
                                stream.Close()
                            except Exception:
                                self._logger.debug(
                                    "Ignoring SAPI stream close failure",
                                    exc_info=True,
                                )

                self._validate_output_path(working_path)
                os.replace(working_path, final_path)
                return SynthesisResult(
                    request_id=request.request_id,
                    voice_id=voice_id,
                    audio_path=final_path,
                    mime_type="audio/wav",
                    retention=request.retention,
                )
            except (VoiceNotFoundError, SynthesisFailedError):
                raise
            except Exception as exc:
                raise SynthesisFailedError(
                    "Windows SAPI synthesis failed: "
                    f"{_format_sapi_error(exc)}"
                ) from exc
            finally:
                self._cleanup_partial_output(working_path)

    def shutdown(self) -> None:
        """Forget cached token metadata; SAPI objects are operation-scoped."""
        with self._lock:
            self._voice_tokens.clear()

    def _ensure_supported(self) -> None:
        if sys.platform != "win32":
            raise BackendUnavailableError(
                "Windows SAPI is available only on Windows."
            )
        if self._com_module is None:
            _load_comtypes()

    def _create_object(self, progid: str) -> Any:
        if self._object_factory is not None:
            return self._object_factory(progid)
        return _create_com_object(progid)

    @contextmanager
    def _com_session(self) -> Iterator[None]:
        com_module = self._com_module or _load_comtypes()
        initialized = False
        initialize = getattr(com_module, "CoInitialize", None)
        uninitialize = getattr(com_module, "CoUninitialize", None)
        try:
            if callable(initialize):
                initialize()
                initialized = True
            yield
        finally:
            if initialized and callable(uninitialize):
                uninitialize()

    def _find_token(self, tokens: Any, token_id: str) -> Any | None:
        for index in range(int(tokens.Count)):
            token = tokens.Item(index)
            if str(getattr(token, "Id", "")).strip() == token_id:
                return token
        return None

    @staticmethod
    def _configure_stream(stream: Any) -> None:
        """Set a conservative mono PCM format when the stream exposes one."""
        try:
            stream.Format.Type = _SAPI_DEFAULT_FORMAT_TYPE
        except Exception:
            # SAPI may expose a read-only/default format on some engines. The
            # engine's native stream format is still valid and is validated
            # after Speak returns.
            return

    def _prepare_output_paths(
        self,
        request: SynthesisRequest,
    ) -> tuple[Path, Path]:
        if request.output_path is not None:
            final_path = Path(request.output_path)
        elif request.retention == AudioRetention.RETAIN:
            final_path = get_retained_audio_path(request.request_id)
        else:
            final_path = get_request_audio_path(request.request_id)

        final_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            prefix=f".{final_path.stem}-",
            suffix=".wav",
            dir=final_path.parent,
            delete=False,
        ) as temporary_file:
            working_path = Path(temporary_file.name)
        working_path.unlink(missing_ok=True)
        return final_path, working_path

    @staticmethod
    def _validate_output_path(audio_path: Path) -> None:
        if not audio_path.exists():
            raise SynthesisFailedError(
                "Windows SAPI completed but output file was not created: "
                f"{audio_path}"
            )

        if audio_path.stat().st_size <= 44:
            raise SynthesisFailedError(
                f"Windows SAPI output file is empty or invalid: {audio_path}"
            )

        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                if (
                    wav_file.getnchannels() <= 0
                    or wav_file.getsampwidth() <= 0
                    or wav_file.getframerate() <= 0
                    or wav_file.getnframes() <= 0
                ):
                    raise ValueError("WAV contains no audio frames")
        except (OSError, wave.Error, ValueError) as exc:
            raise SynthesisFailedError(
                f"Windows SAPI output is not a valid WAV file: {exc}"
            ) from exc

    def _cleanup_partial_output(self, audio_path: Path) -> None:
        try:
            audio_path.unlink(missing_ok=True)
        except OSError as exc:
            self._logger.warning(
                "Failed to remove partial Windows SAPI output %s: %s",
                audio_path,
                exc,
            )


__all__ = [
    "SAPI_VOICE_PREFIX",
    "WindowsSapiProvider",
]
