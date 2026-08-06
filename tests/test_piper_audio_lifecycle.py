from __future__ import annotations

import wave
from pathlib import Path

import pytest

import syllavox.tts.paths as paths_module
import syllavox.tts.piper as piper_module
from syllavox.tts.base import AudioRetention, SynthesisRequest
from syllavox.tts.errors import SynthesisFailedError
from syllavox.tts.piper import PiperBackend


class FailingVoice:
    def synthesize_wav(self, _text: str, wav_file: wave.Wave_write) -> None:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x00\x00")
        raise RuntimeError("synthetic failure")


class WorkingVoice:
    def synthesize_wav(self, _text: str, wav_file: wave.Wave_write) -> None:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x00\x00" * 100)


class UnconfiguredFailingVoice:
    def synthesize_wav(self, _text: str, _wav_file: wave.Wave_write) -> None:
        raise RuntimeError("phonemizer unavailable")


def test_piper_removes_partial_output_after_synthesis_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio_path = tmp_path / "failed.wav"
    backend = PiperBackend(models_dir=tmp_path)
    monkeypatch.setattr(
        piper_module,
        "get_request_audio_path",
        lambda _request_id: audio_path,
    )
    monkeypatch.setattr(backend, "load_voice", lambda _voice_id: FailingVoice())

    with pytest.raises(SynthesisFailedError):
        backend.synthesize(
            SynthesisRequest(
                text="Hello",
                request_id="request-1",
                voice_id="fake-voice",
            )
        )

    assert not audio_path.exists()


def test_piper_preserves_phonemizer_error_when_wav_has_no_header(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = PiperBackend(models_dir=tmp_path)
    monkeypatch.setattr(backend, "load_voice", lambda _voice_id: UnconfiguredFailingVoice())

    with pytest.raises(SynthesisFailedError, match="phonemizer unavailable"):
        backend.synthesize(
            SynthesisRequest(
                text="Hello",
                request_id="request-unconfigured",
                voice_id="fake-voice",
            )
        )


def test_piper_preserves_requested_audio_retention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio_path = tmp_path / "retained.wav"
    backend = PiperBackend(models_dir=tmp_path)
    monkeypatch.setattr(
        piper_module,
        "get_request_audio_path",
        lambda _request_id: audio_path,
    )
    monkeypatch.setattr(
        piper_module,
        "get_retained_audio_path",
        lambda _request_id: audio_path,
    )
    monkeypatch.setattr(backend, "load_voice", lambda _voice_id: WorkingVoice())

    result = backend.synthesize(
        SynthesisRequest(
            text="Hello",
            request_id="request-1",
            voice_id="fake-voice",
            retention=AudioRetention.RETAIN,
        )
    )

    assert result.retention == AudioRetention.RETAIN
    assert audio_path.exists()


def test_piper_writes_explicit_output_destination_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "export.wav"
    backend = PiperBackend(models_dir=tmp_path)
    monkeypatch.setattr(backend, "load_voice", lambda _voice_id: WorkingVoice())

    result = backend.synthesize(
        SynthesisRequest(
            text="Hello",
            request_id="request-1",
            voice_id="fake-voice",
            retention=AudioRetention.RETAIN,
            output_path=output_path,
        )
    )

    assert result.audio_path == output_path
    assert result.retention == AudioRetention.RETAIN
    assert output_path.exists()
    assert list(tmp_path.glob(".*.wav")) == []


def test_piper_export_failure_preserves_existing_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "export.wav"
    output_path.write_bytes(b"existing file")
    backend = PiperBackend(models_dir=tmp_path)
    monkeypatch.setattr(backend, "load_voice", lambda _voice_id: FailingVoice())

    with pytest.raises(SynthesisFailedError):
        backend.synthesize(
            SynthesisRequest(
                text="Hello",
                request_id="request-1",
                voice_id="fake-voice",
                retention=AudioRetention.RETAIN,
                output_path=output_path,
            )
        )

    assert output_path.read_bytes() == b"existing file"
    assert list(tmp_path.glob(".*.wav")) == []


def test_startup_cleanup_removes_only_temporary_audio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary_dir = tmp_path / "tmp"
    retained_dir = tmp_path / "audio"
    temporary_dir.mkdir()
    retained_dir.mkdir()

    temporary_path = temporary_dir / "request-1.wav"
    retained_path = retained_dir / "request-2.wav"
    temporary_path.write_bytes(b"temporary")
    retained_path.write_bytes(b"retained")

    monkeypatch.setattr(paths_module, "get_tmp_dir", lambda: temporary_dir)

    removed_count, failed_count = paths_module.cleanup_temporary_audio_files()

    assert (removed_count, failed_count) == (1, 0)
    assert not temporary_path.exists()
    assert retained_path.exists()


def test_retained_audio_uses_a_separate_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    temporary_path = paths_module.get_request_audio_path("request-1")
    retained_path = paths_module.get_retained_audio_path("request-1")

    assert temporary_path.parent.name == "tmp"
    assert retained_path.parent.name == "audio"
    assert temporary_path != retained_path


def test_g2pw_text_files_are_opened_as_utf8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_dir = tmp_path / "models"
    resource_dir = model_dir / "g2pW"
    resource_dir.mkdir(parents=True)
    resource_path = resource_dir / "POLYPHONIC_CHARS.txt"
    resource_path.write_bytes("中\tzhōng\n".encode("utf-8"))

    import g2pw.api as g2pw_api

    captured: dict[str, object] = {}

    class FakeConverter:
        num_workers = 2

    def fake_init(_converter: FakeConverter, *args: object, **kwargs: object) -> None:
        captured["args"] = args
        captured["kwargs"] = kwargs
        _converter.num_workers = 2

    monkeypatch.setattr(g2pw_api.G2PWConverter, "__init__", fake_init)

    with piper_module._utf8_for_g2pw_text_files(model_dir):
        with g2pw_api.open(resource_path) as resource_file:
            assert resource_file.encoding == "utf-8"
            assert resource_file.read() == "中\tzhōng\n"

        converter = FakeConverter()
        g2pw_api.G2PWConverter.__init__(converter)
        assert converter.num_workers == 0

    assert captured["kwargs"] == {}
    assert g2pw_api.G2PWConverter.__init__ is fake_init
