"""Data models and display formatting for Piper voice catalog entries."""

from __future__ import annotations

from dataclasses import dataclass


LANGUAGE_NAMES = {
    "ar": "Arabic",
    "bg": "Bulgarian",
    "ca": "Catalan",
    "cs": "Czech",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "fa": "Farsi",
    "fi": "Finnish",
    "fr": "French",
    "hu": "Hungarian",
    "he": "Hebrew",
    "hi": "Hindi",
    "id": "Indonesian",
    "is": "Icelandic",
    "it": "Italian",
    "ja": "Japanese",
    "ka": "Georgian",
    "kk": "Kazakh",
    "ko": "Korean",
    "lb": "Luxembourgish",
    "lv": "Latvian",
    "ml": "Malayalam",
    "ne": "Nepali",
    "nl": "Dutch",
    "no": "Norwegian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sr": "Serbian",
    "sv": "Swedish",
    "sw": "Swahili",
    "te": "Telugu",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
    "zh": "Chinese",
}


def format_language_label(
    language_code: str,
    language_name: str | None = None,
    country_name: str | None = None,
) -> str:
    """Return a readable locale label while preserving its exact code."""
    family = language_code.replace("-", "_").split("_", 1)[0].lower()
    readable_language = language_name or LANGUAGE_NAMES.get(family, family.upper())

    if country_name:
        return f"{readable_language} \u2014 {country_name} ({language_code})"

    return f"{readable_language} ({language_code})"


@dataclass(frozen=True)
class VoiceCatalogEntry:
    """Metadata for one Piper voice in the official catalog."""

    voice_id: str
    name: str
    language_code: str
    language_name: str
    country_name: str | None
    quality: str
    num_speakers: int | None
    model_url: str
    config_url: str
    installed: bool = False

    @property
    def language_label(self) -> str:
        return format_language_label(
            self.language_code,
            language_name=self.language_name,
            country_name=self.country_name,
        )

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.quality})"


__all__ = ["VoiceCatalogEntry", "format_language_label"]
