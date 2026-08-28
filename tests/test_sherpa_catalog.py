from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest

from syllavox.tts.catalog_client import SherpaCatalogClient
from syllavox.tts.catalog_models import SherpaCatalogEntry
from syllavox.tts.errors import VoiceCatalogError
from syllavox.tts.voice_storage import SherpaVoiceStorage


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


def _archive(bundle_id: str, filenames: list[str]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:bz2") as archive:
        for filename in filenames:
            path = f"{bundle_id}/{filename}"
            if filename == "espeak-ng-data":
                info = tarfile.TarInfo(path)
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
                continue
            content = b"model data"
            info = tarfile.TarInfo(path)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return output.getvalue()


def _entry(bundle_id: str = "kitten-test") -> SherpaCatalogEntry:
    return SherpaCatalogEntry(
        bundle_id=bundle_id,
        name="Kitten test",
        family="kitten",
        language_codes=("en",),
        quality="fp16",
        num_speakers=1,
        archive_url="https://example.test/model.tar.bz2",
        model_path="model.onnx",
        tokens_path="tokens.txt",
        voices_path="voices.bin",
        data_dir_path="espeak-ng-data",
    )


def test_sherpa_catalog_excludes_converted_piper_archives() -> None:
    entries = SherpaCatalogClient().fetch_catalog()

    assert entries
    assert all(not entry.bundle_id.startswith("vits-piper-") for entry in entries)
    assert {entry.family for entry in entries} >= {
        "vits",
        "matcha",
        "kokoro",
        "kitten",
        "supertonic",
    }


def test_sherpa_catalog_preserves_multilingual_speaker_identity() -> None:
    entries = SherpaCatalogClient().fetch_catalog()
    by_id = {entry.bundle_id: entry for entry in entries}

    kokoro = by_id["kokoro-multi-lang-v1_1"]
    assert len(kokoro.speakers) == 103
    assert kokoro.speakers[0].language_codes == ("en",)
    assert kokoro.speakers[3].language_codes == ("zh",)

    supertonic = by_id["sherpa-onnx-supertonic-3-tts-int8-2026-05-11"]
    assert len(supertonic.speakers) == 310
    assert {
        speaker.language_codes[0] for speaker in supertonic.speakers
    } == set(supertonic.language_codes)
    assert supertonic.sample_rate == 44100


def test_sherpa_catalog_includes_non_piper_monolingual_entries() -> None:
    entries = {
        entry.bundle_id: entry
        for entry in SherpaCatalogClient().fetch_catalog()
    }

    expected_ids = {
        "kitten-nano-en-v0_8-fp32",
        "kitten-nano-en-v0_8-int8",
        "kitten-micro-en-v0_8",
        "kitten-mini-en-v0_8",
        "vits-inflect-en-nano-v2",
        "vits-inflect-en-micro-v2",
        "matcha-icefall-zh-en",
    }
    assert expected_ids <= entries.keys()

    kitten = entries["kitten-nano-en-v0_8-int8"]
    assert kitten.model_path == "model.int8.onnx"
    assert len(kitten.speakers) == 8
    assert kitten.sample_rate == 24000

    inflect = entries["vits-inflect-en-nano-v2"]
    assert inflect.family == "vits"
    assert inflect.language_codes == ("en",)
    assert inflect.speakers[0].name == "Inflect Nano"

    matcha = entries["matcha-icefall-zh-en"]
    assert matcha.vocoder_path == "vocos-16khz-univ.onnx"
    assert matcha.sample_rate == 16000


def test_sherpa_storage_installs_manifest_and_deletes_bundle(
    tmp_path: Path,
) -> None:
    entry = _entry()
    archive = _archive(
        entry.bundle_id,
        ["model.onnx", "tokens.txt", "voices.bin", "espeak-ng-data"],
    )

    def open_url(url: str, timeout: float):
        assert url == entry.archive_url
        assert timeout == 30.0
        return FakeResponse(archive)

    storage = SherpaVoiceStorage(
        models_dir=tmp_path,
        urlopen_fn=open_url,
        timeout_seconds=30.0,
    )

    installed = storage.install_bundle(entry)
    bundle_root = tmp_path / entry.bundle_id
    manifest = json.loads((bundle_root / "bundle.json").read_text())

    assert installed.installed is True
    assert storage.installed_bundle_ids() == [entry.bundle_id]
    assert manifest["family"] == "kitten"
    assert manifest["speaker_count"] == 1

    removed_size = storage.delete_voice_files(
        f"sherpa-onnx:{entry.bundle_id}#sid=0"
    )
    assert removed_size > 0
    assert not bundle_root.exists()


def test_sherpa_storage_rejects_archive_path_traversal(tmp_path: Path) -> None:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:bz2") as archive:
        info = tarfile.TarInfo("../escape.txt")
        info.size = 4
        archive.addfile(info, io.BytesIO(b"bad!"))

    entry = _entry()

    def open_url(url: str, timeout: float):
        del url, timeout
        return FakeResponse(output.getvalue())

    storage = SherpaVoiceStorage(tmp_path, open_url, 30.0)

    with pytest.raises(VoiceCatalogError, match="unsafe path"):
        storage.install_bundle(entry)

    assert list(tmp_path.iterdir()) == []
