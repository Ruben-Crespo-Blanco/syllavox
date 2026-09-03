from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest

from syllavox.tts.catalog_client import (
    PIPER_VOICES_CATALOG_URL,
    PiperCatalogClient,
)
from syllavox.tts.catalog_models import VoiceCatalogEntry
from syllavox.tts.errors import VoiceCatalogError
from syllavox.tts.voice_storage import PiperVoiceStorage


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


def test_catalog_client_can_fetch_without_local_storage_state() -> None:
    payload = {
        "en_US-lessac-medium": {
            "name": "lessac",
            "language": {
                "code": "en_US",
                "family": "en",
                "name_english": "English",
                "country_english": "United States",
            },
            "quality": "medium",
        }
    }

    def open_url(url: str, timeout: float):
        del timeout
        assert url == PIPER_VOICES_CATALOG_URL
        return FakeResponse(json.dumps(payload).encode("utf-8"))

    entries = PiperCatalogClient(urlopen_fn=open_url).fetch_catalog()

    assert len(entries) == 1
    assert entries[0].voice_id == "en_US-lessac-medium"
    assert entries[0].installed is False


def test_catalog_client_rejects_invalid_payload() -> None:
    def open_url(url: str, timeout: float):
        del url, timeout
        return FakeResponse(b"[]")

    with pytest.raises(VoiceCatalogError, match="invalid format"):
        PiperCatalogClient(urlopen_fn=open_url).fetch_catalog()


def test_voice_storage_install_failure_leaves_no_partial_pair(
    tmp_path: Path,
) -> None:
    model_url = "https://example.test/voice.onnx"
    config_url = "https://example.test/voice.onnx.json"
    entry = VoiceCatalogEntry(
        voice_id="en_US-lessac-medium",
        name="lessac",
        language_code="en_US",
        language_name="English",
        country_name="United States",
        quality="medium",
        num_speakers=1,
        model_url=model_url,
        config_url=config_url,
    )

    def open_url(url: str, timeout: float):
        del timeout
        if url == model_url:
            return FakeResponse(b"model bytes")
        raise OSError("download unavailable")

    storage = PiperVoiceStorage(
        models_dir=tmp_path,
        urlopen_fn=open_url,
        timeout_seconds=30.0,
    )

    with pytest.raises(VoiceCatalogError, match="Download failed"):
        storage.install_voice(entry)

    assert not (tmp_path / f"{entry.voice_id}.onnx").exists()
    assert not (tmp_path / f"{entry.voice_id}.onnx.json").exists()
    assert list(tmp_path.iterdir()) == []


def test_voice_storage_rolls_back_when_second_pair_replace_fails(
    tmp_path: Path,
) -> None:
    entry = VoiceCatalogEntry(
        voice_id="en_US-lessac-medium",
        name="lessac",
        language_code="en_US",
        language_name="English",
        country_name="United States",
        quality="medium",
        num_speakers=1,
        model_url="https://example.test/voice.onnx",
        config_url="https://example.test/voice.onnx.json",
    )
    model_path = tmp_path / f"{entry.voice_id}.onnx"
    config_path = tmp_path / f"{entry.voice_id}.onnx.json"
    model_path.write_bytes(b"old model")
    config_path.write_bytes(b"old config")
    downloads = {
        entry.model_url: b"new model",
        entry.config_url: b"new config",
    }

    class FailingStorage(PiperVoiceStorage):
        replace_count = 0

        def _replace_installed_file(self, source: Path, destination: Path) -> None:
            self.replace_count += 1
            if self.replace_count == 2:
                raise OSError("simulated config replace failure")
            source.replace(destination)

    storage = FailingStorage(
        models_dir=tmp_path,
        urlopen_fn=lambda url, timeout: FakeResponse(downloads[url]),
        timeout_seconds=30.0,
    )

    with pytest.raises(VoiceCatalogError, match="config replace failure"):
        storage.install_voice(entry)

    assert model_path.read_bytes() == b"old model"
    assert config_path.read_bytes() == b"old config"


def test_voice_storage_recovers_prepared_transaction_after_restart(
    tmp_path: Path,
) -> None:
    voice_id = "en_US-lessac-medium"
    model_path = tmp_path / f"{voice_id}.onnx"
    config_path = tmp_path / f"{voice_id}.onnx.json"
    model_path.write_bytes(b"old model")
    config_path.write_bytes(b"old config")
    storage = PiperVoiceStorage(
        models_dir=tmp_path,
        urlopen_fn=lambda url, timeout: FakeResponse(b"unused"),
        timeout_seconds=30.0,
    )
    storage._begin_install_transaction(
        voice_id,
        (model_path, config_path),
    )
    replacement = tmp_path / ".replacement.onnx"
    replacement.write_bytes(b"new model")
    storage._replace_installed_file(replacement, model_path)

    PiperVoiceStorage(
        models_dir=tmp_path,
        urlopen_fn=lambda url, timeout: FakeResponse(b"unused"),
        timeout_seconds=30.0,
    )

    assert model_path.read_bytes() == b"old model"
    assert config_path.read_bytes() == b"old config"
    assert not (tmp_path / ".install-transactions").exists()
