"""Command-line interface for Piper voice diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from syllavox.tts.diagnostic_core import diagnose_installed_voices
from syllavox.tts.diagnostic_models import VoiceDiagnosticReport
from syllavox.tts.paths import get_piper_models_dir


def _print_report(report: VoiceDiagnosticReport) -> None:
    print(f"Models directory: {report.models_dir}")
    if not report.results:
        print("No local voice model files found.")
        return

    for item in report.results:
        audio_details = ""
        if item.audio is not None:
            audio_details = (
                f" channels={item.audio.channels}"
                f" sample_rate={item.audio.sample_rate}"
                f" frames={item.audio.frame_count}"
            )
        print(
            f"{item.status.value:24} {item.voice_id}"
            f" phase={item.phase} elapsed_ms={item.elapsed_ms}"
            f"{audio_details}\n  {item.message}"
        )


def main(argv: list[str] | None = None) -> int:
    """Run the diagnostics from the command line."""
    parser = argparse.ArgumentParser(
        description="Classify local Piper voice compatibility failures."
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=get_piper_models_dir(),
        help="Flat directory containing Piper .onnx/.onnx.json pairs.",
    )
    parser.add_argument(
        "--voice",
        action="append",
        dest="voice_ids",
        help="Check only this voice ID; may be supplied more than once.",
    )
    parser.add_argument(
        "--text",
        help="Use this text for every checked voice instead of the language default.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the text report.",
    )
    args = parser.parse_args(argv)

    report = diagnose_installed_voices(
        args.models_dir,
        voice_ids=args.voice_ids,
        text=args.text,
    )
    if args.json:
        # Keep CLI output safe on Windows consoles using a legacy code page.
        print(json.dumps(report.as_dict(), ensure_ascii=True, indent=2))
    else:
        _print_report(report)

    return 0 if report.passed else 1


__all__ = ["main"]
