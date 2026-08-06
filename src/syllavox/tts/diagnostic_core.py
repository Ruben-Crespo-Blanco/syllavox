"""Reusable core logic for classifying Piper voice compatibility failures."""

from __future__ import annotations

import json
import logging
import time
import wave
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from syllavox.request_ids import new_request_id
from syllavox.tts.base import AudioRetention, SynthesisRequest
from syllavox.tts.diagnostic_models import (
    AudioDiagnostics,
    DiagnosticStatus,
    VoiceDiagnosticReport,
    VoiceDiagnosticResult,
)
from syllavox.tts.errors import VoiceNotFoundError
from syllavox.tts.paths import get_piper_models_dir
from syllavox.tts.piper import PiperBackend


def discover_local_voice_ids(models_dir: Path) -> list[str]:
    """Return voice IDs represented by complete or partial local file pairs."""
    if not models_dir.exists():
        return []

    voice_ids: set[str] = {path.stem for path in models_dir.glob("*.onnx")}
    config_suffix = ".onnx.json"
    voice_ids.update(
        path.name[: -len(config_suffix)]
        for path in models_dir.glob("*.onnx.json")
        if path.name.endswith(config_suffix)
    )
    return sorted(voice_ids)


def classify_failure(
    error: BaseException,
    *,
    phase: str,
) -> DiagnosticStatus:
    """Classify a Piper failure without changing or hiding its message."""
    message = str(error).lower()

    if isinstance(error, VoiceNotFoundError):
        return DiagnosticStatus.MISSING_MODEL_FILES

    if any(
        marker in message
        for marker in (
            "no module named",
            "cannot import",
            "importerror",
            "onnxruntime",
            "espeak",
        )
    ):
        return DiagnosticStatus.DEPENDENCY_FAILURE

    if any(
        marker in message
        for marker in (
            "g2pw",
            "pinyin",
            "phonemizer",
            "phoneme resource",
            "resource",
        )
    ):
        return DiagnosticStatus.MISSING_RESOURCE

    if any(
        marker in message
        for marker in (
            "# channels not specified",
            "channels not specified",
            "sample rate not specified",
            "sampwidth",
            "wave.error",
            "invalid wav",
            "wav file",
        )
    ):
        return DiagnosticStatus.AUDIO_FORMAT_FAILURE

    if any(
        marker in message
        for marker in (
            "onnx",
            "protobuf",
            "invalid graph",
            "model file",
            "tensor",
        )
    ):
        return DiagnosticStatus.MODEL_FAILURE

    if phase == "load":
        return DiagnosticStatus.LOAD_FAILURE
    if phase == "synthesis":
        return DiagnosticStatus.SYNTHESIS_FAILURE
    if phase == "audio_validation":
        return DiagnosticStatus.AUDIO_FORMAT_FAILURE

    return DiagnosticStatus.UNKNOWN_FAILURE


def diagnose_installed_voices(
    models_dir: Path,
    *,
    voice_ids: Iterable[str] | None = None,
    text: str | None = None,
) -> VoiceDiagnosticReport:
    """Diagnose local Piper voice files without retaining generated audio."""
    backend = PiperBackend(models_dir=models_dir)
    selected_voice_ids = list(voice_ids or discover_local_voice_ids(models_dir))

    results = tuple(
        diagnose_voice(
            backend,
            voice_id,
            text=text,
        )
        for voice_id in selected_voice_ids
    )
    return VoiceDiagnosticReport(models_dir=models_dir, results=results)


def diagnose_voice(
    backend: PiperBackend,
    voice_id: str,
    *,
    text: str | None = None,
) -> VoiceDiagnosticResult:
    """Diagnose one voice through file, load, synthesis, and WAV stages."""
    started_at = time.monotonic()
    models_dir_value = getattr(backend, "models_dir", None)
    if models_dir_value is None:
        models_dir_value = getattr(backend, "_models_dir")
    models_dir = Path(models_dir_value)
    language_code = voice_id.split("-", 1)[0] if voice_id else ""
    captured_warnings: list[str] = []

    def result(
        status: DiagnosticStatus,
        phase: str,
        message: str,
        *,
        phoneme_type: str | None = None,
        expected_sample_rate: int | None = None,
        audio: AudioDiagnostics | None = None,
        warnings: tuple[str, ...] | None = None,
    ) -> VoiceDiagnosticResult:
        return VoiceDiagnosticResult(
            voice_id=voice_id,
            language_code=language_code,
            phoneme_type=phoneme_type,
            status=status,
            phase=phase,
            message=message,
            elapsed_ms=round((time.monotonic() - started_at) * 1000),
            expected_sample_rate=expected_sample_rate,
            audio=audio,
            warnings=(
                tuple(captured_warnings)
                if warnings is None
                else warnings
            ),
        )

    if (
        not voice_id
        or Path(voice_id).name != voice_id
        or voice_id in {".", ".."}
    ):
        return result(
            DiagnosticStatus.INVALID_VOICE_ID,
            "files",
            "Voice ID is not a safe local filename.",
        )

    model_path = models_dir / f"{voice_id}.onnx"
    config_path = models_dir / f"{voice_id}.onnx.json"

    if not model_path.is_file() or not config_path.is_file():
        return result(
            DiagnosticStatus.MISSING_MODEL_FILES,
            "files",
            "Both the .onnx model and matching .onnx.json config are required.",
        )

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return result(
            DiagnosticStatus.INVALID_CONFIG,
            "files",
            f"Could not parse the voice config: {exc}",
        )

    if not isinstance(config, dict):
        return result(
            DiagnosticStatus.INVALID_CONFIG,
            "files",
            "The voice config must contain a JSON object.",
        )

    phoneme_type = _config_string(config, "phoneme_type")
    expected_sample_rate = _config_audio_integer(config, "sample_rate")

    if phoneme_type == "pinyin" and not _has_resource_files(models_dir / "g2pW"):
        return result(
            DiagnosticStatus.MISSING_RESOURCE,
            "preflight",
            "This voice uses pinyin, but no local g2pW resource was found.",
            phoneme_type=phoneme_type,
            expected_sample_rate=expected_sample_rate,
        )

    try:
        with _capture_piper_warnings(captured_warnings):
            try:
                backend.load_voice(voice_id)
            except Exception as exc:
                return result(
                    classify_failure(exc, phase="load"),
                    "load",
                    str(exc),
                    phoneme_type=phoneme_type,
                    expected_sample_rate=expected_sample_rate,
                )

            diagnostic_text = text or _default_diagnostic_text(language_code)
            with TemporaryDirectory(prefix="syllavox-voice-diagnostic-") as temp_dir:
                audio_path = Path(temp_dir) / "voice-check.wav"
                try:
                    backend.synthesize(
                        SynthesisRequest(
                            text=diagnostic_text,
                            request_id=new_request_id("diagnostic"),
                            voice_id=voice_id,
                            retention=AudioRetention.RETAIN,
                            output_path=audio_path,
                        )
                    )
                except Exception as exc:
                    return result(
                        classify_failure(exc, phase="synthesis"),
                        "synthesis",
                        str(exc),
                        phoneme_type=phoneme_type,
                        expected_sample_rate=expected_sample_rate,
                    )

                try:
                    audio = inspect_wav(audio_path)
                except Exception as exc:
                    return result(
                        classify_failure(exc, phase="audio_validation"),
                        "audio_validation",
                        str(exc),
                        phoneme_type=phoneme_type,
                        expected_sample_rate=expected_sample_rate,
                    )

                if (
                    expected_sample_rate is not None
                    and audio.sample_rate != expected_sample_rate
                ):
                    return result(
                        DiagnosticStatus.AUDIO_FORMAT_FAILURE,
                        "audio_validation",
                        (
                            "Generated WAV sample rate does not match the voice "
                            f"config ({audio.sample_rate} != {expected_sample_rate})."
                        ),
                        phoneme_type=phoneme_type,
                        expected_sample_rate=expected_sample_rate,
                        audio=audio,
                    )

                warning_status = (
                    DiagnosticStatus.NONFATAL_PHONEME_WARNING
                    if captured_warnings
                    else DiagnosticStatus.PASS
                )
                warning_message = (
                    "Voice produced valid WAV audio, but Piper skipped "
                    f"{len(captured_warnings)} phoneme warning(s)."
                    if captured_warnings
                    else "Voice loaded, synthesized, and produced valid WAV audio."
                )
                return result(
                    warning_status,
                    "complete",
                    warning_message,
                    phoneme_type=phoneme_type,
                    expected_sample_rate=expected_sample_rate,
                    audio=audio,
                )
    finally:
        backend.unload_voice(voice_id)


@contextmanager
def _capture_piper_warnings(messages: list[str]) -> Iterator[None]:
    """Capture Piper's warnings about phonemes omitted from an ID map."""

    class PiperWarningHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            message = record.getMessage()
            if "Missing phoneme from id map" in message:
                messages.append(message)

    handler = PiperWarningHandler()
    piper_logger = logging.getLogger("piper")
    piper_logger.addHandler(handler)
    try:
        yield
    finally:
        piper_logger.removeHandler(handler)


def inspect_wav(audio_path: Path) -> AudioDiagnostics:
    """Read and validate basic WAV metadata from a generated file."""
    with wave.open(str(audio_path), "rb") as wav_file:
        metadata = AudioDiagnostics(
            channels=wav_file.getnchannels(),
            sample_width=wav_file.getsampwidth(),
            sample_rate=wav_file.getframerate(),
            frame_count=wav_file.getnframes(),
            file_size=audio_path.stat().st_size,
        )

    if metadata.channels <= 0:
        raise wave.Error("WAV contains no audio channels")
    if metadata.sample_width <= 0:
        raise wave.Error("WAV contains no sample width")
    if metadata.sample_rate <= 0:
        raise wave.Error("WAV contains no sample rate")
    if metadata.frame_count <= 0:
        raise wave.Error("WAV contains no audio frames")

    return metadata


def _config_string(config: dict[str, Any], key: str) -> str | None:
    value = config.get(key)
    return value if isinstance(value, str) else None


def _config_audio_integer(config: dict[str, Any], key: str) -> int | None:
    audio_config = config.get("audio")
    if not isinstance(audio_config, dict):
        return None

    value = audio_config.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _has_resource_files(resource_dir: Path) -> bool:
    return resource_dir.is_dir() and any(path.is_file() for path in resource_dir.rglob("*"))


def _default_diagnostic_text(language_code: str) -> str:
    language_family = language_code.split("_", 1)[0].lower()
    return {
        "ar": "مرحبا بالعالم.",
        "bg": "Здравей, свят.",
        "ca": "Hola, món.",
        "cs": "Ahoj světe.",
        "da": "Hej verden.",
        "de": "Hallo Welt.",
        "el": "Γεια σου κόσμε.",
        "en": "Hello, world.",
        "es": "Hola, mundo.",
        "fa": "سلام دنیا.",
        "fi": "Hei maailma.",
        "fr": "Bonjour le monde.",
        "he": "שלום עולם.",
        "hi": "नमस्ते दुनिया।",
        "hu": "Helló világ.",
        "id": "Halo dunia.",
        "it": "Ciao mondo.",
        "ja": "こんにちは、世界。",
        "ko": "안녕하세요, 세계.",
        "nl": "Hallo wereld.",
        "no": "Hei verden.",
        "pl": "Witaj świecie.",
        "pt": "Olá, mundo.",
        "ro": "Salut lume.",
        "ru": "Привет, мир.",
        "sk": "Ahoj svet.",
        "sv": "Hej världen.",
        "tr": "Merhaba dünya.",
        "uk": "Привіт, світе.",
        "vi": "Xin chào thế giới.",
        "zh": "你好，世界。",
    }.get(language_family, "Hello, world.")


__all__ = [
    "classify_failure",
    "diagnose_installed_voices",
    "diagnose_voice",
    "discover_local_voice_ids",
    "inspect_wav",
]
