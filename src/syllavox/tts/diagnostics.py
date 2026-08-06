"""Public compatibility facade for Piper voice diagnostics.

Reusable diagnostic logic lives in :mod:`diagnostic_core`, result models live
in :mod:`diagnostic_models`, and command-line handling lives in
:mod:`diagnostic_cli`.  This module keeps the original import path and module
entry point stable.
"""

from __future__ import annotations

from syllavox.tts.diagnostic_cli import main
from syllavox.tts.diagnostic_core import (
    classify_failure,
    diagnose_installed_voices,
    diagnose_voice,
    discover_local_voice_ids,
    inspect_wav,
)
from syllavox.tts.diagnostic_models import (
    AudioDiagnostics,
    DiagnosticStatus,
    VoiceDiagnosticReport,
    VoiceDiagnosticResult,
)


__all__ = [
    "AudioDiagnostics",
    "DiagnosticStatus",
    "VoiceDiagnosticReport",
    "VoiceDiagnosticResult",
    "classify_failure",
    "diagnose_installed_voices",
    "diagnose_voice",
    "discover_local_voice_ids",
    "inspect_wav",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
