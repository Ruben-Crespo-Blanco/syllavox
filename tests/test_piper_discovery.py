from pathlib import Path
from typing import Any

import pytest

from syllavox.tts.errors import LanguageCompatibilityError
from syllavox.tts.piper import PiperBackend


def test_piper_voice_discovery_from_fake_files(tmp_path: Path) -> None:
    model_path = tmp_path / "en_US-lessac-medium.onnx"
    config_path = tmp_path / "en_US-lessac-medium.onnx.json"

    model_path.write_bytes(b"fake model")
    config_path.write_text("{}", encoding="utf-8")

    backend = PiperBackend(models_dir=tmp_path)

    voices = backend.list_voices()

    assert len(voices) == 1
    assert voices[0].voice_id == "en_US-lessac-medium"
    assert voices[0].name == "en_US lessac medium"
    assert voices[0].language == "en"


def test_piper_ignores_model_without_config(tmp_path: Path) -> None:
    model_path = tmp_path / "en_US-lessac-medium.onnx"
    model_path.write_bytes(b"fake model")

    backend = PiperBackend(models_dir=tmp_path)

    voices = backend.list_voices()

    assert voices == []


def test_piper_health_with_missing_model_dir(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing"

    backend = PiperBackend(models_dir=missing_dir)

    health = backend.health()

    assert health.name == "piper"
    assert health.healthy is False
    assert health.details is not None


def test_piper_health_with_valid_fake_voice(tmp_path: Path) -> None:
    model_path = tmp_path / "en_US-lessac-medium.onnx"
    config_path = tmp_path / "en_US-lessac-medium.onnx.json"

    model_path.write_bytes(b"fake model")
    config_path.write_text("{}", encoding="utf-8")

    backend = PiperBackend(models_dir=tmp_path)

    health = backend.health()

    assert health.name == "piper"
    assert health.healthy is True
    assert health.details is not None
    assert "voice" in health.details


def test_piper_health_with_invalid_model_pair(tmp_path: Path) -> None:
    model_path = tmp_path / "en_US-lessac-medium.onnx"
    model_path.write_bytes(b"fake model")

    backend = PiperBackend(models_dir=tmp_path)

    health = backend.health()

    assert health.name == "piper"
    assert health.healthy is False
    assert health.details is not None


def test_piper_health_reports_import_failure(tmp_path: Path) -> None:
    backend = PiperBackend(models_dir=tmp_path)

    def fail_import():
        raise ImportError("piper unavailable")

    backend._import_piper_voice = fail_import  # type: ignore[method-assign]

    health = backend.health()

    assert health.healthy is False
    assert health.details == "Piper Python API unavailable: piper unavailable"


def test_piper_loads_chinese_resources_under_models_dir(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    model_path = tmp_path / "zh_CN-chaowen-medium.onnx"
    config_path = tmp_path / "zh_CN-chaowen-medium.onnx.json"
    model_path.write_bytes(b"fake model")
    config_path.write_text("{}", encoding="utf-8")

    calls: dict[str, Any] = {}

    class FakePiperVoice:
        @staticmethod
        def load(model: str, **kwargs: Any) -> object:
            calls["model"] = model
            calls.update(kwargs)
            return object()

    backend = PiperBackend(models_dir=tmp_path)
    monkeypatch.setattr(backend, "_import_piper_voice", lambda: FakePiperVoice)

    backend.load_voice("zh_CN-chaowen-medium")

    assert calls == {
        "model": str(model_path),
        "download_dir": str(tmp_path),
    }


def test_piper_reports_unsupported_language_phonemizer(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    model_path = tmp_path / "he_IL-test-medium.onnx"
    config_path = tmp_path / "he_IL-test-medium.onnx.json"
    model_path.write_bytes(b"fake model")
    config_path.write_text(
        '{"phoneme_type": "future-language-phonemizer"}',
        encoding="utf-8",
    )

    backend = PiperBackend(models_dir=tmp_path)
    monkeypatch.setattr(
        backend,
        "_supported_phoneme_types",
        staticmethod(lambda: {"espeak", "hebrew", "pinyin", "text"}),
    )

    issue = backend.voice_compatibility_issue("he_IL-test-medium")

    assert issue is not None
    assert "future-language-phonemizer" in issue
    with pytest.raises(LanguageCompatibilityError, match="future-language"):
        backend.load_voice("he_IL-test-medium")
