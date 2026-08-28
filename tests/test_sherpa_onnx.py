from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import pytest

from syllavox.tts.base import AudioRetention, SynthesisRequest
from syllavox.tts.errors import (
    SynthesisFailedError,
    VoiceNotFoundError,
)
import syllavox.tts.sherpa_onnx as sherpa_module
from syllavox.tts.sherpa_onnx import SherpaOnnxBackend


def _write_bundle(
    models_dir: Path,
    *,
    bundle_id: str = "kokoro-test",
    family: str = "kokoro",
    language_codes: list[str] | None = None,
    complete: bool = True,
) -> Path:
    bundle_dir = models_dir / bundle_id
    bundle_dir.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "bundle_id": bundle_id,
        "display_name": "Kokoro test bundle",
        "family": family,
        "model": "model.onnx",
        "tokens": "tokens.txt",
        "data_dir": "espeak-ng-data",
        "language_codes": language_codes or ["he_IL"],
        "quality": "int8",
        "speakers": [{"id": 18, "name": "Test speaker"}],
    }
    if family in {"kokoro", "kitten"}:
        manifest["voices"] = "voices.bin"
    (bundle_dir / "bundle.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    if complete:
        for filename in ("model.onnx", "tokens.txt", "voices.bin"):
            if family == "vits" and filename == "voices.bin":
                continue
            (bundle_dir / filename).write_bytes(b"test model data")
        (bundle_dir / "espeak-ng-data").mkdir()
        (bundle_dir / "espeak-ng-data" / "phsource").write_text(
            "test",
            encoding="utf-8",
        )
    return bundle_dir


class _FakeAudio:
    sample_rate = 22050
    samples = [0.0, 0.25, -0.25, 0.0]


class _FakeTts:
    def __init__(self, config) -> None:
        self.config = config
        self.generated_text: str | None = None
        self.generated_sid: int | None = None
        self.generated_extra = None

    def generate(self, text, generation_config):
        self.generated_text = text
        self.generated_sid = generation_config.sid
        self.generated_extra = getattr(generation_config, "extra", None)
        return _FakeAudio()


class _FakeModelConfig:
    def __init__(self, **kwargs) -> None:
        self.values = kwargs


class _FakeRuntime:
    __version__ = "1.13.6-test"
    OfflineTtsVitsModelConfig = _FakeModelConfig
    OfflineTtsMatchaModelConfig = _FakeModelConfig
    OfflineTtsKokoroModelConfig = _FakeModelConfig
    OfflineTtsKittenModelConfig = _FakeModelConfig
    OfflineTtsSupertonicModelConfig = _FakeModelConfig

    class OfflineTtsModelConfig(_FakeModelConfig):
        pass

    class OfflineTtsConfig(_FakeModelConfig):
        def validate(self):
            return True

    class GenerationConfig:
        sid = 0
        speed = 1.0
        silence_scale = 0.2

    OfflineTts = _FakeTts


class _FakeNativeRuntime(_FakeRuntime):
    native_write_calls = 0

    @classmethod
    def write_wave(cls, filename, samples, sample_rate):
        cls.native_write_calls += 1
        with wave.open(str(filename), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * len(samples))
        return True


def test_health_reports_missing_optional_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", None)

    health = SherpaOnnxBackend(models_dir=tmp_path).health()

    assert health.healthy is False
    assert "not installed" in (health.details or "")


def test_manifest_exposes_clear_language_and_stable_speaker_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeRuntime)
    _write_bundle(tmp_path)
    backend = SherpaOnnxBackend(models_dir=tmp_path)

    voices = backend.list_voices()

    assert len(voices) == 1
    assert voices[0].voice_id == "sherpa-onnx:kokoro-test#sid=18"
    assert voices[0].language_code == "he_IL"
    assert voices[0].language_name == "Hebrew"
    assert "Kokoro test bundle" in voices[0].name


def test_incomplete_bundle_has_actionable_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeRuntime)
    _write_bundle(tmp_path, complete=False)
    backend = SherpaOnnxBackend(models_dir=tmp_path)

    health = backend.health()
    diagnostics = backend.bundle_diagnostics()

    assert health.healthy is True
    assert "missing model file" in " ".join(diagnostics)
    with pytest.raises(SynthesisFailedError, match="incomplete"):
        backend.load_voice("sherpa-onnx:kokoro-test#sid=18")


def test_synthesis_uses_one_cached_bundle_and_writes_standard_wav(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeRuntime)
    models_dir = tmp_path / "models"
    _write_bundle(models_dir)
    backend = SherpaOnnxBackend(models_dir=models_dir)
    output_path = tmp_path / "output.wav"
    request = SynthesisRequest(
        text="שלום עולם",
        request_id="request-1",
        voice_id="sherpa-onnx:kokoro-test#sid=18",
        retention=AudioRetention.RETAIN,
        output_path=output_path,
    )

    result = backend.synthesize(request)

    assert result.audio_path == output_path
    assert output_path.exists()
    assert backend.is_voice_loaded(request.voice_id)
    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 22050
        assert wav_file.getnframes() == 4

    backend.unload_voice(request.voice_id)
    assert backend.loaded_voice_ids() == []


def test_temporary_synthesis_keeps_audio_for_the_player(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeRuntime)
    _write_bundle(tmp_path)
    monkeypatch.setattr(
        sherpa_module,
        "get_request_audio_path",
        lambda request_id: tmp_path / f"{request_id}.wav",
    )
    backend = SherpaOnnxBackend(models_dir=tmp_path)

    result = backend.synthesize(
        SynthesisRequest(
            text="Hello",
            request_id="temporary-request",
            voice_id="sherpa-onnx:kokoro-test#sid=18",
        )
    )

    assert result.audio_path.exists()
    result.audio_path.unlink()


def test_synthesis_uses_native_runtime_wave_writer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeNativeRuntime)
    _write_bundle(tmp_path)
    backend = SherpaOnnxBackend(models_dir=tmp_path)
    output_path = tmp_path / "native-output.wav"

    backend.synthesize(
        SynthesisRequest(
            text="Hello",
            request_id="native-request",
            voice_id="sherpa-onnx:kokoro-test#sid=18",
            retention=AudioRetention.RETAIN,
            output_path=output_path,
        )
    )

    assert _FakeNativeRuntime.native_write_calls == 1
    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getframerate() == 22050
        assert wav_file.getnframes() == 4


def test_invalid_voice_id_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeRuntime)
    backend = SherpaOnnxBackend(models_dir=tmp_path)

    with pytest.raises(VoiceNotFoundError):
        backend.load_voice("not-a-sherpa-voice")


def test_supertonic_exposes_language_qualified_speakers_and_extra(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeRuntime)
    bundle_dir = tmp_path / "supertonic-test"
    bundle_dir.mkdir()
    manifest = {
        "schema_version": 1,
        "bundle_id": "supertonic-test",
        "display_name": "Supertonic test bundle",
        "family": "supertonic",
        "duration_predictor": "duration_predictor.onnx",
        "text_encoder": "text_encoder.onnx",
        "vector_estimator": "vector_estimator.onnx",
        "vocoder": "vocoder.onnx",
        "tts_json": "tts.json",
        "unicode_indexer": "unicode_indexer.bin",
        "voice_style": "voice.bin",
        "language_codes": ["en", "fr"],
        "sample_rate": 22050,
        "speakers": [
            {"id": 0, "name": "Speaker 0", "language_codes": ["en"]},
            {"id": 0, "name": "Speaker 0", "language_codes": ["fr"]},
        ],
    }
    (bundle_dir / "bundle.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    for filename in (
        "duration_predictor.onnx",
        "text_encoder.onnx",
        "vector_estimator.onnx",
        "vocoder.onnx",
        "tts.json",
        "unicode_indexer.bin",
        "voice.bin",
    ):
        (bundle_dir / filename).write_bytes(b"test model data")

    backend = SherpaOnnxBackend(models_dir=tmp_path)
    voices = backend.list_voices()

    assert [voice.voice_id for voice in voices] == [
        "sherpa-onnx:supertonic-test#sid=0&lang=en",
        "sherpa-onnx:supertonic-test#sid=0&lang=fr",
    ]
    assert [voice.language_name for voice in voices] == ["English", "French"]

    backend.synthesize(
        SynthesisRequest(
            text="Hello",
            request_id="supertonic-request",
            voice_id="sherpa-onnx:supertonic-test#sid=0&lang=fr",
            retention=AudioRetention.RETAIN,
            output_path=tmp_path / "supertonic.wav",
        )
    )
    tts = backend._loaded_bundles["supertonic-test"]
    assert tts.generated_extra == {"lang": "fr"}
