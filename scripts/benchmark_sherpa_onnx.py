"""Measure one local Sherpa-ONNX bundle through the Syllavox adapter."""

from __future__ import annotations

import argparse
import tempfile
import time
import wave
from pathlib import Path

from syllavox.request_ids import new_request_id
from syllavox.tts.base import AudioRetention, SynthesisRequest
from syllavox.tts.paths import get_sherpa_onnx_models_dir
from syllavox.tts.sherpa_onnx import SherpaOnnxBackend


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=get_sherpa_onnx_models_dir(),
        help="Root directory containing Sherpa bundle folders.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=2,
        help="Sherpa CPU inference threads (default: 2).",
    )
    parser.add_argument("--voice", help="Backend-qualified voice ID to test.")
    parser.add_argument(
        "--text",
        default="This is a Syllavox Sherpa-ONNX benchmark.",
        help="Text to synthesize.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(tempfile.gettempdir()) / "syllavox-sherpa-benchmark.wav",
        help="WAV output path.",
    )
    args = parser.parse_args(argv)

    backend = SherpaOnnxBackend(
        models_dir=args.models_dir,
        num_threads=args.threads,
    )
    health = backend.health()
    print(f"Backend: {health.name}")
    print(f"Health: {health.healthy} ({health.details})")
    if not health.healthy:
        return 1

    voices = backend.list_voices()
    if not voices:
        print("No Sherpa voices were found.")
        for diagnostic in backend.bundle_diagnostics():
            print(f"  {diagnostic}")
        return 1

    voice_id = args.voice or voices[0].voice_id
    if voice_id not in {voice.voice_id for voice in voices}:
        print(f"Voice not found: {voice_id}")
        return 1

    load_started = time.perf_counter()
    backend.load_voice(voice_id)
    cold_load_seconds = time.perf_counter() - load_started

    request = SynthesisRequest(
        text=args.text,
        request_id=new_request_id("sherpa-benchmark"),
        voice_id=voice_id,
        retention=AudioRetention.RETAIN,
        output_path=args.output,
    )
    synth_started = time.perf_counter()
    result = backend.synthesize(request)
    synth_seconds = time.perf_counter() - synth_started

    with wave.open(str(result.audio_path), "rb") as wav_file:
        audio_duration = wav_file.getnframes() / wav_file.getframerate()

    bundle_size = backend.voice_model_size(voice_id)
    rtf = synth_seconds / audio_duration if audio_duration else float("inf")
    print(f"Voice: {voice_id}")
    print(f"Threads: {args.threads}")
    print(f"Cold load seconds: {cold_load_seconds:.3f}")
    print(f"Warm synthesis seconds: {synth_seconds:.3f}")
    print(f"Audio duration seconds: {audio_duration:.3f}")
    print(f"Real-time factor: {rtf:.3f}")
    print(f"WAV bytes: {result.audio_path.stat().st_size}")
    print(f"Bundle bytes: {bundle_size}")
    backend.unload_voice(voice_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
