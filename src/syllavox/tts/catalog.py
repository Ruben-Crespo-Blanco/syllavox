"""Public facade for Piper voice discovery and local model management."""

from __future__ import annotations

from urllib.request import urlopen

from syllavox.tts.catalog_client import (
    PIPER_VOICES_BASE_URL,
    PIPER_VOICES_CATALOG_URL,
    PiperCatalogClient,
)
from syllavox.tts.catalog_models import VoiceCatalogEntry, format_language_label
from syllavox.tts.voice_storage import PiperVoiceStorage


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


__all__ = [
    "PIPER_VOICES_BASE_URL",
    "PIPER_VOICES_CATALOG_URL",
    "PiperVoiceCatalog",
    "VoiceCatalogEntry",
    "format_language_label",
]
