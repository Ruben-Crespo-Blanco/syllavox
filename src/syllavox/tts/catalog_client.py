"""Remote Piper voice-catalog retrieval and metadata parsing."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import urlopen

from syllavox.tts.catalog_models import (
    LANGUAGE_NAMES,
    VoiceCatalogEntry,
)
from syllavox.tts.errors import VoiceCatalogError

PIPER_VOICES_CATALOG_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "voices.json?download=true"
)
PIPER_VOICES_BASE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main"
)

UrlOpen = Callable[..., Any]
InstalledVoiceCheck = Callable[[str], bool]


class PiperCatalogClient:
    """Fetch and parse the official Piper voice catalog."""

    def __init__(
        self,
        urlopen_fn: UrlOpen = urlopen,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._urlopen = urlopen_fn
        self._timeout_seconds = timeout_seconds

    def fetch_catalog(
        self,
        is_voice_installed: InstalledVoiceCheck | None = None,
    ) -> list[VoiceCatalogEntry]:
        """Fetch usable catalog entries and optionally mark local voices."""
        try:
            payload = self._read_url(PIPER_VOICES_CATALOG_URL)
            raw_catalog = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise VoiceCatalogError(
                f"Could not load the Piper voice catalog: {exc}"
            ) from exc

        if not isinstance(raw_catalog, dict):
            raise VoiceCatalogError(
                "The Piper voice catalog has an invalid format."
            )

        entries: list[VoiceCatalogEntry] = []

        for voice_id, raw_entry in raw_catalog.items():
            if not isinstance(raw_entry, dict):
                continue

            try:
                entry = self._parse_entry(str(voice_id), raw_entry)
            except (KeyError, TypeError, ValueError):
                continue

            if is_voice_installed is not None:
                entry = replace(
                    entry,
                    installed=is_voice_installed(entry.voice_id),
                )

            entries.append(entry)

        if not entries:
            raise VoiceCatalogError(
                "The Piper voice catalog contains no usable voices."
            )

        return sorted(
            entries,
            key=lambda entry: (
                entry.language_label.lower(),
                entry.name.lower(),
                entry.quality.lower(),
                entry.voice_id,
            ),
        )

    def _read_url(self, url: str) -> bytes:
        with self._urlopen(url, timeout=self._timeout_seconds) as response:
            return response.read()

    def _parse_entry(
        self,
        voice_id: str,
        raw_entry: dict[str, Any],
    ) -> VoiceCatalogEntry:
        language_data = raw_entry.get("language")
        if not isinstance(language_data, dict):
            language_data = {}

        language_code = str(
            language_data.get("code")
            or voice_id.split("-", 1)[0]
        )
        language_family = str(
            language_data.get("family")
            or language_code.split("_", 1)[0]
        )
        voice_name = str(raw_entry.get("name") or self._voice_name(voice_id))
        quality = str(raw_entry.get("quality") or self._voice_quality(voice_id))

        if not language_code or not voice_name or not quality:
            raise ValueError("Incomplete voice catalog entry")

        model_filename = f"{voice_id}.onnx"
        config_filename = f"{model_filename}.json"
        base_url = "/".join(
            [
                PIPER_VOICES_BASE_URL,
                quote(language_family, safe=""),
                quote(language_code, safe=""),
                quote(voice_name, safe=""),
                quote(quality, safe=""),
            ]
        )

        return VoiceCatalogEntry(
            voice_id=voice_id,
            name=voice_name,
            language_code=language_code,
            language_name=str(
                language_data.get("name_english")
                or LANGUAGE_NAMES.get(
                    language_family,
                    language_family.upper(),
                )
            ),
            country_name=(
                str(language_data["country_english"])
                if language_data.get("country_english")
                else None
            ),
            quality=quality,
            num_speakers=(
                int(raw_entry["num_speakers"])
                if raw_entry.get("num_speakers") is not None
                else None
            ),
            model_url=f"{base_url}/{model_filename}?download=true",
            config_url=f"{base_url}/{config_filename}?download=true",
        )

    @staticmethod
    def _voice_name(voice_id: str) -> str:
        parts = voice_id.split("-", 2)
        return parts[1] if len(parts) > 1 else voice_id

    @staticmethod
    def _voice_quality(voice_id: str) -> str:
        parts = voice_id.rsplit("-", 1)
        return parts[1] if len(parts) > 1 else "unknown"


__all__ = [
    "PIPER_VOICES_BASE_URL",
    "PIPER_VOICES_CATALOG_URL",
    "PiperCatalogClient",
]
