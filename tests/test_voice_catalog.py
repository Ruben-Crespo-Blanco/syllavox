from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest

from syllavox.tts.catalog import (
    PIPER_VOICES_CATALOG_URL,
    PiperVoiceCatalog,
    format_language_label,
)
from syllavox.tts.errors import VoiceCatalogError


@pytest.mark.parametrize(
    ("language_code", "language_name"),
    [
        ("he_IL", "Hebrew"),
        ("bg_BG", "Bulgarian"),
        ("ja_JP", "Japanese"),
        ("ko_KR", "Korean"),
    ],
)
def test_language_labels_use_readable_names_for_supported_families(
    language_code: str,
    language_name: str,
) -> None:
    assert format_language_label(language_code) == (
        f"{language_name} ({language_code})"
    )


def test_language_labels_accept_hyphenated_locale_codes() -> None:
    assert format_language_label("he-IL") == "Hebrew (he-IL)"


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


def test_catalog_parses_locales_and_marks_installed_voices(
    tmp_path: Path,
) -> None:
    catalog_payload = {
        "en_US-lessac-medium": {
            "name": "lessac",
            "language": {
                "code": "en_US",
                "family": "en",
                "name_english": "English",
                "country_english": "United States",
            },
            "quality": "medium",
            "num_speakers": 1,
        },
        "es_ES-davefx-medium": {
            "name": "davefx",
            "language": {
                "code": "es_ES",
                "family": "es",
                "name_english": "Spanish",
                "country_english": "Spain",
            },
            "quality": "medium",
        },
    }

    (tmp_path / "en_US-lessac-medium.onnx").write_bytes(b"model")
    (tmp_path / "en_US-lessac-medium.onnx.json").write_text("{}")

    def open_url(url: str, timeout: float):
        del timeout
        assert url == PIPER_VOICES_CATALOG_URL
        return FakeResponse(json.dumps(catalog_payload).encode("utf-8"))

    catalog = PiperVoiceCatalog(tmp_path, urlopen_fn=open_url)
    entries = catalog.fetch_catalog()

    assert [entry.voice_id for entry in entries] == [
        "en_US-lessac-medium",
        "es_ES-davefx-medium",
    ]
    assert entries[0].language_label == "English — United States (en_US)"
    assert entries[0].installed is True
    assert entries[1].installed is False
    assert entries[1].display_name == "davefx (medium)"


def test_catalog_installs_model_and_config_as_a_pair(tmp_path: Path) -> None:
    model_url = "https://example.test/en_US-lessac-medium.onnx"
    config_url = "https://example.test/en_US-lessac-medium.onnx.json"
    downloads = {
        model_url: b"model bytes",
        config_url: b'{"audio": {}}',
    }

    def open_url(url: str, timeout: float):
        del timeout
        return FakeResponse(downloads[url])

    from syllavox.tts.catalog import VoiceCatalogEntry

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

    catalog = PiperVoiceCatalog(tmp_path, urlopen_fn=open_url)
    installed = catalog.install_voice(entry)

    assert installed.installed is True
    assert (tmp_path / "en_US-lessac-medium.onnx").read_bytes() == b"model bytes"
    assert (tmp_path / "en_US-lessac-medium.onnx.json").read_bytes() == (
        b'{"audio": {}}'
    )


def test_catalog_reports_size_and_deletes_voice_pair(tmp_path: Path) -> None:
    model_path = tmp_path / "en_US-lessac-medium.onnx"
    config_path = tmp_path / "en_US-lessac-medium.onnx.json"
    model_path.write_bytes(b"model")
    config_path.write_bytes(b"config")

    catalog = PiperVoiceCatalog(tmp_path)

    assert catalog.installed_voice_ids() == ["en_US-lessac-medium"]
    assert catalog.voice_model_size("en_US-lessac-medium") == 11
    assert catalog.delete_voice_files("en_US-lessac-medium") == 11
    assert not model_path.exists()
    assert not config_path.exists()


def test_catalog_rejects_voice_path_traversal(tmp_path: Path) -> None:
    catalog = PiperVoiceCatalog(tmp_path)

    with pytest.raises(VoiceCatalogError):
        catalog.delete_voice_files("..\\outside")


def test_catalog_removes_unused_g2pw_only_after_last_pinyin_voice(
    tmp_path: Path,
) -> None:
    voice_id = "zh_CN-chaowen-medium"
    (tmp_path / f"{voice_id}.onnx").write_bytes(b"model")
    (tmp_path / f"{voice_id}.onnx.json").write_text(
        '{"phoneme_type": "pinyin"}',
        encoding="utf-8",
    )
    resource_dir = tmp_path / "g2pW"
    resource_dir.mkdir()
    (resource_dir / "resource.bin").write_bytes(b"resource")

    catalog = PiperVoiceCatalog(tmp_path)

    with pytest.raises(VoiceCatalogError):
        catalog.delete_unused_g2pw()

    catalog.delete_voice_files(voice_id)
    assert catalog.delete_unused_g2pw() == len(b"resource")
    assert not resource_dir.exists()
