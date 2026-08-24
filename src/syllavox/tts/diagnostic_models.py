"""Data models for Piper voice compatibility diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class DiagnosticStatus(str, Enum):
    """Stable categories used by the compatibility diagnostic."""

    PASS = "pass"
    INVALID_VOICE_ID = "invalid_voice_id"
    MISSING_MODEL_FILES = "missing_model_files"
    INVALID_CONFIG = "invalid_config"
    MISSING_RESOURCE = "missing_resource"
    LANGUAGE_COMPATIBILITY_FAILURE = "language_compatibility_failure"
    DEPENDENCY_FAILURE = "dependency_failure"
    MODEL_FAILURE = "model_failure"
    LOAD_FAILURE = "load_failure"
    SYNTHESIS_FAILURE = "synthesis_failure"
    AUDIO_FORMAT_FAILURE = "audio_format_failure"
    NONFATAL_PHONEME_WARNING = "nonfatal_phoneme_warning"
    UNKNOWN_FAILURE = "unknown_failure"


@dataclass(frozen=True)
class AudioDiagnostics:
    """Relevant metadata read from a generated WAV file."""

    channels: int
    sample_width: int
    sample_rate: int
    frame_count: int
    file_size: int


@dataclass(frozen=True)
class VoiceDiagnosticResult:
    """Result of checking one installed or partially installed voice."""

    voice_id: str
    language_code: str
    phoneme_type: str | None
    status: DiagnosticStatus
    phase: str
    message: str
    elapsed_ms: int
    expected_sample_rate: int | None = None
    audio: AudioDiagnostics | None = None
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        """Return whether the voice passed every diagnostic stage."""
        return self.status == DiagnosticStatus.PASS

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the result."""
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass(frozen=True)
class VoiceDiagnosticReport:
    """Results for one diagnostic run."""

    models_dir: Path
    results: tuple[VoiceDiagnosticResult, ...]

    @property
    def passed(self) -> bool:
        """Return whether all checked voices passed."""
        return bool(self.results) and all(result.passed for result in self.results)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable report."""
        return {
            "models_dir": str(self.models_dir),
            "passed": self.passed,
            "results": [result.as_dict() for result in self.results],
        }


__all__ = [
    "AudioDiagnostics",
    "DiagnosticStatus",
    "VoiceDiagnosticReport",
    "VoiceDiagnosticResult",
]
