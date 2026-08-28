"""Download and exercise the curated non-Piper Sherpa-ONNX model bundles."""

from __future__ import annotations

import argparse
import time
import wave
from pathlib import Path
from urllib.request import urlopen

from syllavox.request_ids import new_request_id
from syllavox.tts.base import AudioRetention, SynthesisRequest
from syllavox.tts.catalog_models import SherpaCatalogEntry
from syllavox.tts.sherpa_catalog import get_sherpa_catalog_entries
from syllavox.tts.sherpa_onnx import SherpaOnnxBackend
from syllavox.tts.voice_storage import SherpaVoiceStorage


_LANGUAGE_SAMPLES = {
    "ar": "هذا اختبار لتحويل النص إلى كلام في سيلافوكس.",
    "bg": "Това е тест за преобразуване на текст в реч в Syllavox.",
    "cs": "Toto je test převodu textu na řeč v aplikaci Syllavox.",
    "da": "Dette er en test af tekst til tale i Syllavox.",
    "de": "Dies ist ein Test der Sprachsynthese in Syllavox.",
    "el": "Αυτή είναι μια δοκιμή σύνθεσης ομιλίας στο Syllavox.",
    "en": "This is a Syllavox Sherpa-ONNX smoke test.",
    "es": "Esta es una prueba de síntesis de voz en Syllavox.",
    "et": "See on Syllavoxi kõnesünteesi test.",
    "fi": "Tämä on Syllavoxin puhesynteesitesti.",
    "fr": "Ceci est un test de synthèse vocale dans Syllavox.",
    "hi": "यह Syllavox में वाक् संश्लेषण का परीक्षण है।",
    "hr": "Ovo je test sinteze govora u Syllavoxu.",
    "hu": "Ez a Syllavox beszédszintézis-tesztje.",
    "id": "Ini adalah uji sintesis ucapan di Syllavox.",
    "it": "Questo è un test di sintesi vocale in Syllavox.",
    "ja": "これはSyllavoxの音声合成テストです。",
    "ko": "이것은 Syllavox 음성 합성 테스트입니다.",
    "lt": "Tai yra Syllavox kalbos sintezės testas.",
    "lv": "Šis ir Syllavox runas sintēzes tests.",
    "nl": "Dit is een test van tekst-naar-spraak in Syllavox.",
    "pl": "To jest test syntezy mowy w Syllavox.",
    "pt": "Este é um teste de síntese de voz no Syllavox.",
    "ro": "Acesta este un test de sinteză vocală în Syllavox.",
    "ru": "Это тест синтеза речи в Syllavox.",
    "sk": "Toto je test syntézy reči v aplikácii Syllavox.",
    "sl": "To je preizkus sinteze govora v Syllavoxu.",
    "sv": "Det här är ett test av talsyntes i Syllavox.",
    "tr": "Bu, Syllavox'ta bir konuşma sentezi testidir.",
    "uk": "Це тест синтезу мовлення у Syllavox.",
    "vi": "Đây là bài kiểm tra tổng hợp giọng nói trong Syllavox.",
    "zh": "这是一个语音合成测试。",
}


def _default_models_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "build" / "sherpa-real-smoke"


def _voices_for_entry(
    backend: SherpaOnnxBackend,
    entry: SherpaCatalogEntry,
) -> list[str]:
    prefix = f"sherpa-onnx:{entry.bundle_id}#sid="
    voices = [voice for voice in backend.list_voices() if voice.voice_id.startswith(prefix)]
    if not voices:
        return []

    selected: list[str] = []
    seen_languages: set[str] = set()
    for voice in voices:
        language_code = voice.language_code or "en"
        if language_code not in seen_languages:
            selected.append(voice.voice_id)
            seen_languages.add(language_code)
    return selected


def _sample_for_voice(voice_id: str, language_code: str | None) -> str:
    del voice_id
    language = (language_code or "en").split("_", 1)[0]
    return _LANGUAGE_SAMPLES.get(language, _LANGUAGE_SAMPLES["en"])


def _test_voice(
    backend: SherpaOnnxBackend,
    voice_id: str,
    language_code: str | None,
    output_path: Path,
) -> tuple[float, float, float, int]:
    load_started = time.perf_counter()
    backend.load_voice(voice_id)
    load_seconds = time.perf_counter() - load_started

    request = SynthesisRequest(
        text=_sample_for_voice(voice_id, language_code),
        request_id=new_request_id("sherpa-smoke"),
        voice_id=voice_id,
        retention=AudioRetention.RETAIN,
        output_path=output_path,
    )
    synth_started = time.perf_counter()
    result = backend.synthesize(request)
    synth_seconds = time.perf_counter() - synth_started

    with wave.open(str(result.audio_path), "rb") as wav_file:
        if wav_file.getnchannels() != 1:
            raise RuntimeError("output is not mono")
        if wav_file.getsampwidth() != 2:
            raise RuntimeError("output is not 16-bit PCM")
        if wav_file.getnframes() <= 0:
            raise RuntimeError("output has no audio frames")
        audio_duration = wav_file.getnframes() / wav_file.getframerate()
        wav_bytes = result.audio_path.stat().st_size

    backend.unload_voice(voice_id)
    return load_seconds, synth_seconds, audio_duration, wav_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=_default_models_dir(),
        help="Directory where real model bundles are downloaded.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=2,
        help="Sherpa CPU inference threads (default: 2).",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep generated WAV files under the model directory.",
    )
    args = parser.parse_args(argv)

    entries = get_sherpa_catalog_entries()
    if any(entry.family == "piper" for entry in entries):
        raise RuntimeError("The smoke-test catalog must not include Piper bundles.")

    args.models_dir.mkdir(parents=True, exist_ok=True)
    storage = SherpaVoiceStorage(
        models_dir=args.models_dir,
        urlopen_fn=urlopen,
        timeout_seconds=180.0,
    )
    backend = SherpaOnnxBackend(
        models_dir=args.models_dir,
        num_threads=args.threads,
    )

    failures: list[str] = []
    passed = 0
    total = 0
    output_dir = args.models_dir / "smoke-output"
    output_dir.mkdir(exist_ok=True)

    print(f"Models directory: {args.models_dir}", flush=True)
    print(f"Sherpa bundles: {len(entries)}", flush=True)

    for entry in entries:
        print(f"\n[{entry.bundle_id}] installing or reusing bundle", flush=True)
        try:
            if not storage.is_bundle_installed(entry.bundle_id):
                storage.install_bundle(entry)
            else:
                print("  already installed", flush=True)
        except Exception as exc:
            failures.append(f"{entry.bundle_id}: install failed: {exc}")
            print(f"  FAIL install: {exc}", flush=True)
            continue

        voices = _voices_for_entry(backend, entry)
        if not voices:
            failures.append(f"{entry.bundle_id}: no voices discovered")
            print("  FAIL: no voices discovered", flush=True)
            continue

        voice_lookup = {voice.voice_id: voice for voice in backend.list_voices()}
        print(f"  testing {len(voices)} representative voice(s)", flush=True)
        for index, voice_id in enumerate(voices, start=1):
            total += 1
            voice = voice_lookup[voice_id]
            output_path = output_dir / f"{entry.bundle_id}-{index}.wav"
            started = time.perf_counter()
            try:
                load_seconds, synth_seconds, duration, wav_bytes = _test_voice(
                    backend,
                    voice_id,
                    voice.language_code,
                    output_path,
                )
                passed += 1
                rtf = synth_seconds / duration if duration else float("inf")
                print(
                    f"  PASS {voice_id} | load={load_seconds:.2f}s "
                    f"synth={synth_seconds:.2f}s duration={duration:.2f}s "
                    f"rtf={rtf:.2f} wav={wav_bytes}B",
                    flush=True,
                )
            except Exception as exc:
                failures.append(f"{voice_id}: inference failed: {exc}")
                print(
                    f"  FAIL {voice_id} after {time.perf_counter() - started:.2f}s: {exc}",
                    flush=True,
                )
            finally:
                if not args.keep_audio:
                    output_path.unlink(missing_ok=True)

    print(f"\nResult: {passed}/{total} representative inference checks passed.")
    if failures:
        print("Failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
