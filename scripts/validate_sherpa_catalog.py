"""Validate and optionally smoke-test Syllavox's curated Sherpa voices.

The default mode checks catalog metadata without downloading model files. The
``--synthesize`` mode exercises installed bundles and writes a short WAV for
each selected v0.4.2 voice, recording basic runtime measurements.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import wave
from pathlib import Path

from syllavox.tts.catalog_client import SherpaCatalogClient
from syllavox.tts.catalog_models import SherpaCatalogEntry
from syllavox.tts.paths import get_sherpa_onnx_models_dir


V042_MIMIC3_BUNDLES = (
    "vits-mimic3-af_ZA-google-nwu_low",
    "vits-mimic3-bn-multi_low",
    "vits-mimic3-gu_IN-cmu-indic_low",
    "vits-mimic3-tn_ZA-google-nwu_low",
)

SAMPLE_TEXT = {
    "af": "Hallo, dit is 'n toets van die Afrikaanse stem.",
    "bn": "নমস্কার, এটি বাংলা কণ্ঠের একটি পরীক্ষা।",
    "gu": "નમસ્તે, આ ગુજરાતી અવાજની એક ચકાસણી છે.",
    "tn": "Dumela, seno ke teko ya lentswe la Setswana.",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models-dir",
        type=Path,
        help="Sherpa bundle directory; defaults to Syllavox's local path.",
    )
    parser.add_argument(
        "--bundle",
        action="append",
        dest="bundles",
        choices=V042_MIMIC3_BUNDLES,
        help="Validate one v0.4.2 bundle; may be repeated.",
    )
    parser.add_argument(
        "--synthesize",
        action="store_true",
        help="Synthesize a short sample from each installed selected bundle.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for smoke-test WAV files (required with --synthesize).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a table.",
    )
    return parser.parse_args()


def _catalog_entries() -> dict[str, SherpaCatalogEntry]:
    return {
        entry.bundle_id: entry
        for entry in SherpaCatalogClient().fetch_catalog()
    }


def _metadata_result(entry: SherpaCatalogEntry) -> dict[str, object]:
    missing: list[str] = []
    if entry.family != "vits":
        missing.append("family=vits")
    if not entry.model_path:
        missing.append("model_path")
    if not entry.tokens_path:
        missing.append("tokens_path")
    if not entry.data_dir_path:
        missing.append("data_dir_path")
    if not entry.language_name:
        missing.append("language_name")
    if not entry.source_url:
        missing.append("source_url")
    if not entry.license_name or not entry.license_url:
        missing.append("license metadata")
    if not entry.archive_sha256 or not re.fullmatch(
        r"[0-9a-fA-F]{64}", entry.archive_sha256
    ):
        missing.append("archive_sha256")
    return {
        "bundle_id": entry.bundle_id,
        "language": entry.language_label,
        "speakers": entry.num_speakers,
        "status": "ok" if not missing else "invalid",
        "details": missing,
    }


def _smoke_test(
    entry: SherpaCatalogEntry,
    models_dir: Path,
    output_dir: Path,
) -> dict[str, object]:
    from syllavox.tts.base import AudioRetention, SynthesisRequest
    from syllavox.tts.sherpa_onnx import SherpaOnnxBackend

    bundle_dir = models_dir / entry.bundle_id
    result: dict[str, object] = {
        "bundle_id": entry.bundle_id,
        "language": entry.language_label,
    }
    if not (bundle_dir / "bundle.json").is_file():
        result.update({"status": "not-installed", "details": []})
        return result

    backend = SherpaOnnxBackend(models_dir=models_dir)
    voices = [
        voice
        for voice in backend.list_voices()
        if voice.voice_id.startswith(f"sherpa-onnx:{entry.bundle_id}#sid=")
    ]
    if not voices:
        result.update({"status": "no-voices", "details": backend.bundle_diagnostics()})
        return result

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{entry.bundle_id}.wav"
    request = SynthesisRequest(
        text=SAMPLE_TEXT.get(entry.language_code, "This is a voice test."),
        request_id=f"validation-{entry.bundle_id}",
        voice_id=voices[0].voice_id,
        retention=AudioRetention.RETAIN,
        output_path=output_path,
    )
    started = time.perf_counter()
    try:
        backend.synthesize(request)
    except Exception as exc:
        result.update({"status": "failed", "details": [str(exc)]})
        return result
    elapsed = time.perf_counter() - started

    with wave.open(str(output_path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        frames = wav_file.getnframes()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
    duration = frames / sample_rate if sample_rate else 0.0
    if channels != 1 or sample_width != 2 or not output_path.is_file():
        result.update(
            {
                "status": "failed",
                "details": [
                    "Expected a mono, 16-bit WAV output from the Sherpa backend."
                ],
            }
        )
        backend.shutdown()
        return result

    result.update(
        {
            "status": "ok",
            "voice_id": voices[0].voice_id,
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width": sample_width,
            "duration_seconds": round(duration, 3),
            "elapsed_seconds": round(elapsed, 3),
            "real_time_factor": round(elapsed / duration, 3) if duration else None,
            "output": str(output_path),
        }
    )
    backend.shutdown()
    return result


def main() -> int:
    args = _parse_args()
    entries = _catalog_entries()
    selected_ids = args.bundles or list(V042_MIMIC3_BUNDLES)
    results = []
    exit_code = 0

    for bundle_id in selected_ids:
        entry = entries.get(bundle_id)
        if entry is None:
            results.append(
                {
                    "bundle_id": bundle_id,
                    "status": "missing-from-catalog",
                    "details": [],
                }
            )
            exit_code = 1
            continue

        metadata = _metadata_result(entry)
        results.append(metadata)
        if metadata["status"] != "ok":
            exit_code = 1

        if args.synthesize:
            if args.output_dir is None:
                print("--output-dir is required with --synthesize", file=sys.stderr)
                return 2
            smoke = _smoke_test(
                entry,
                args.models_dir or get_sherpa_onnx_models_dir(),
                args.output_dir,
            )
            results.append(smoke)
            if smoke["status"] != "ok":
                exit_code = 1

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results:
            details = ", ".join(str(item) for item in result.get("details", []))
            print(
                f"{result['status']:>20}  {result['bundle_id']}"
                + (f"  ({details})" if details else "")
            )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
