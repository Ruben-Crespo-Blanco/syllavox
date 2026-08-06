from __future__ import annotations

import wave
import logging
from pathlib import Path

from syllavox.tts.base import AudioRetention, SynthesisRequest
from syllavox.tts.diagnostics import (
    DiagnosticStatus,
    classify_failure,
    diagnose_voice,
    discover_local_voice_ids,
    inspect_wav,
)
from syllavox.tts.errors import SynthesisFailedError


class FakeDiagnosticBackend:
    def __init__(self, models_dir: Path, synthesis_error: Exception | None = None):
        self.models_dir = models_dir
        self.synthesis_error = synthesis_error
        self.loaded: set[str] = set()

    def load_voice(self, voice_id: str) -> None:
        self.loaded.add(voice_id)

    def unload_voice(self, voice_id: str) -> None:
        self.loaded.discard(voice_id)

    def synthesize(self, request: SynthesisRequest) -> None:
        if self.synthesis_error is not None:
            raise self.synthesis_error

        assert request.output_path is not None
        with wave.open(str(request.output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x00\x00" * 20)


class WarningDiagnosticBackend(FakeDiagnosticBackend):
    def synthesize(self, request: SynthesisRequest) -> None:
        logging.getLogger("piper.phoneme_ids").warning(
            "Missing phoneme from id map: %s",
            "\\u0303",
        )
        super().synthesize(request)


def _write_voice(
    models_dir: Path,
    voice_id: str = "en_US-test-medium",
    config: str = '{"phoneme_type": "espeak", "audio": {"sample_rate": 22050}}',
) -> None:
    (models_dir / f"{voice_id}.onnx").write_bytes(b"model")
    (models_dir / f"{voice_id}.onnx.json").write_text(config, encoding="utf-8")


def test_discover_local_voice_ids_includes_partial_pairs(tmp_path: Path) -> None:
    _write_voice(tmp_path)
    (tmp_path / "orphan.onnx").write_bytes(b"model")
    (tmp_path / "config-only.onnx.json").write_text("{}", encoding="utf-8")

    assert discover_local_voice_ids(tmp_path) == [
        "config-only",
        "en_US-test-medium",
        "orphan",
    ]


def test_diagnose_voice_passes_and_releases_loaded_voice(tmp_path: Path) -> None:
    _write_voice(tmp_path)
    backend = FakeDiagnosticBackend(tmp_path)

    result = diagnose_voice(backend, "en_US-test-medium")

    assert result.status == DiagnosticStatus.PASS
    assert result.audio is not None
    assert result.audio.channels == 1
    assert result.audio.sample_rate == 22050
    assert backend.loaded == set()


def test_diagnose_voice_classifies_missing_files(tmp_path: Path) -> None:
    backend = FakeDiagnosticBackend(tmp_path)

    result = diagnose_voice(backend, "en_US-missing-medium")

    assert result.status == DiagnosticStatus.MISSING_MODEL_FILES
    assert result.phase == "files"


def test_diagnose_voice_classifies_missing_pinyin_resource(tmp_path: Path) -> None:
    _write_voice(
        tmp_path,
        voice_id="zh_CN-test-medium",
        config='{"phoneme_type": "pinyin", "audio": {"sample_rate": 22050}}',
    )
    backend = FakeDiagnosticBackend(tmp_path)

    result = diagnose_voice(backend, "zh_CN-test-medium")

    assert result.status == DiagnosticStatus.MISSING_RESOURCE
    assert result.phase == "preflight"
    assert backend.loaded == set()


def test_diagnose_voice_classifies_channels_error(tmp_path: Path) -> None:
    _write_voice(tmp_path)
    backend = FakeDiagnosticBackend(
        tmp_path,
        synthesis_error=SynthesisFailedError(
            "Piper synthesis failed: # channels not specified"
        ),
    )

    result = diagnose_voice(backend, "en_US-test-medium")

    assert result.status == DiagnosticStatus.AUDIO_FORMAT_FAILURE
    assert result.phase == "synthesis"


def test_diagnose_voice_reports_nonfatal_phoneme_warning(tmp_path: Path) -> None:
    _write_voice(tmp_path)
    backend = WarningDiagnosticBackend(tmp_path)

    result = diagnose_voice(backend, "en_US-test-medium")

    assert result.status == DiagnosticStatus.NONFATAL_PHONEME_WARNING
    assert result.passed is False
    assert result.warnings == ("Missing phoneme from id map: \\u0303",)


def test_inspect_wav_rejects_audio_with_no_frames(tmp_path: Path) -> None:
    audio_path = tmp_path / "empty.wav"
    with wave.open(str(audio_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)

    try:
        inspect_wav(audio_path)
    except wave.Error as exc:
        assert "frames" in str(exc)
    else:
        raise AssertionError("Expected an empty WAV to fail validation")


def test_classify_failure_distinguishes_dependency_and_model_errors() -> None:
    assert (
        classify_failure(
            ImportError("No module named 'g2pw'"),
            phase="load",
        )
        == DiagnosticStatus.DEPENDENCY_FAILURE
    )
    assert (
        classify_failure(
            RuntimeError("Invalid ONNX model graph"),
            phase="load",
        )
        == DiagnosticStatus.MODEL_FAILURE
    )
