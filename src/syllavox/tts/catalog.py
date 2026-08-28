"""Public facades for local voice discovery and model management."""

from __future__ import annotations

from urllib.request import urlopen

from syllavox.tts.catalog_client import (
    PIPER_VOICES_BASE_URL,
    PIPER_VOICES_CATALOG_URL,
    PiperCatalogClient,
    SherpaCatalogClient,
)
from syllavox.tts.catalog_models import (
    SherpaCatalogEntry,
    VoiceCatalogEntry,
    format_language_label,
)
from syllavox.tts.voice_storage import PiperVoiceStorage, SherpaVoiceStorage


class PiperVoiceCatalog:
    """Coordinate remote catalog access with local Piper voice storage."""

    def __init__(
        self,
        models_dir,
        urlopen_fn=urlopen,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._models_dir = models_dir
        self._catalog_client = PiperCatalogClient(
            urlopen_fn=urlopen_fn,
            timeout_seconds=timeout_seconds,
        )
        self._voice_storage = PiperVoiceStorage(
            models_dir=models_dir,
            urlopen_fn=urlopen_fn,
            timeout_seconds=timeout_seconds,
        )

    @property
    def models_dir(self):
        return self._models_dir

    def fetch_catalog(self) -> list[VoiceCatalogEntry]:
        """Fetch and parse the official Piper voice catalog."""
        return self._catalog_client.fetch_catalog(
            self._voice_storage.is_voice_installed
        )

    def is_voice_installed(self, voice_id: str) -> bool:
        return self._voice_storage.is_voice_installed(voice_id)

    def installed_voice_ids(self) -> list[str]:
        return self._voice_storage.installed_voice_ids()

    def voice_model_size(self, voice_id: str) -> int:
        return self._voice_storage.voice_model_size(voice_id)

    def delete_voice_files(self, voice_id: str) -> int:
        return self._voice_storage.delete_voice_files(voice_id)

    def voice_uses_pinyin(self, voice_id: str) -> bool:
        return self._voice_storage.voice_uses_pinyin(voice_id)

    def has_installed_pinyin_voice(
        self,
        excluding_voice_id: str | None = None,
    ) -> bool:
        return self._voice_storage.has_installed_pinyin_voice(
            excluding_voice_id=excluding_voice_id
        )

    def g2pw_size(self) -> int:
        return self._voice_storage.g2pw_size()

    def delete_unused_g2pw(self) -> int:
        return self._voice_storage.delete_unused_g2pw()

    def install_voice(self, entry: VoiceCatalogEntry) -> VoiceCatalogEntry:
        return self._voice_storage.install_voice(entry)


class SherpaVoiceCatalog:
    """Coordinate the official non-Piper Sherpa catalog and local bundles."""

    supports_voice_deletion = True
    supports_resource_cleanup = False

    display_name = "Sherpa-ONNX"
    catalog_url = "https://k2-fsa.github.io/sherpa/onnx/tts/all/index.html"

    def __init__(
        self,
        backend,
        models_dir,
        urlopen_fn=urlopen,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._backend = backend
        self._models_dir = models_dir
        self._catalog_client = SherpaCatalogClient()
        self._voice_storage = SherpaVoiceStorage(
            models_dir=models_dir,
            urlopen_fn=urlopen_fn,
            timeout_seconds=timeout_seconds,
        )

    @property
    def models_dir(self):
        return self._models_dir

    def voice_model_size(self, voice_id: str) -> int:
        return self._backend.voice_model_size(voice_id)

    def fetch_catalog(self) -> list[SherpaCatalogEntry]:
        return self._catalog_client.fetch_catalog(
            self._voice_storage.is_bundle_installed
        )

    def installed_catalog_ids(self) -> set[str]:
        return set(self._voice_storage.installed_bundle_ids())

    def install_voice(self, entry: SherpaCatalogEntry) -> SherpaCatalogEntry:
        return self._voice_storage.install_bundle(entry)

    def delete_voice_files(self, voice_id: str) -> int:
        return self._voice_storage.delete_voice_files(voice_id)

    def voice_ids_for_resource(
        self,
        voice_id: str,
        voice_ids: list[str],
    ) -> list[str]:
        bundle_id = SherpaVoiceStorage.bundle_id_from_voice_id(voice_id)
        return [
            candidate
            for candidate in voice_ids
            if SherpaVoiceStorage.bundle_id_from_voice_id(candidate)
            == bundle_id
        ]

    def deletion_description(self, voice_id: str) -> str:
        del voice_id
        return (
            "This removes the complete Sherpa-ONNX model bundle and its "
            "downloaded runtime resources from disk."
        )

    def g2pw_size(self) -> int:
        return 0

    def has_installed_pinyin_voice(
        self,
        excluding_voice_id: str | None = None,
    ) -> bool:
        del excluding_voice_id
        return False

    def delete_unused_g2pw(self) -> int:
        return 0


__all__ = [
    "PIPER_VOICES_BASE_URL",
    "PIPER_VOICES_CATALOG_URL",
    "PiperVoiceCatalog",
    "SherpaCatalogEntry",
    "SherpaVoiceCatalog",
    "VoiceCatalogEntry",
    "format_language_label",
]
