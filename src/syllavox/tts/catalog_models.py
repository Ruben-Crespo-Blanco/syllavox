"""Data models and display formatting for Piper voice catalog entries."""

from __future__ import annotations

from dataclasses import dataclass


LANGUAGE_NAMES = {
    "af": "Afrikaans",
    "am": "Amharic",
    "ar": "Arabic",
    "az": "Azerbaijani",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "ca": "Catalan",
    "cs": "Czech",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "eu": "Basque",
    "es": "Spanish",
    "et": "Estonian",
    "fa": "Farsi",
    "fi": "Finnish",
    "fr": "French",
    "fil": "Filipino",
    "gu": "Gujarati",
    "hu": "Hungarian",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "id": "Indonesian",
    "is": "Icelandic",
    "it": "Italian",
    "ja": "Japanese",
    "ka": "Georgian",
    "kk": "Kazakh",
    "kn": "Kannada",
    "ko": "Korean",
    "ku": "Kurdish",
    "lb": "Luxembourgish",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "ms": "Malay",
    "ml": "Malayalam",
    "mr": "Marathi",
    "my": "Burmese",
    "ne": "Nepali",
    "nl": "Dutch",
    "no": "Norwegian",
    "pa": "Punjabi",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sq": "Albanian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sr": "Serbian",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "uz": "Uzbek",
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


@dataclass(frozen=True)
class SherpaSpeakerCatalogEntry:
    """Speaker metadata used to build an installed Sherpa bundle manifest."""

    speaker_id: int
    name: str
    language_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SherpaCatalogEntry:
    """One curated, non-Piper Sherpa-ONNX model archive."""

    bundle_id: str
    name: str
    family: str
    language_codes: tuple[str, ...]
    quality: str
    num_speakers: int | None
    archive_url: str
    model_path: str | None = None
    tokens_path: str | None = None
    voices_path: str | None = None
    data_dir_path: str | None = None
    dict_dir_path: str | None = None
    lexicon_paths: tuple[str, ...] = ()
    rule_fst_paths: tuple[str, ...] = ()
    rule_far_paths: tuple[str, ...] = ()
    acoustic_model_path: str | None = None
    vocoder_path: str | None = None
    duration_predictor_path: str | None = None
    text_encoder_path: str | None = None
    vector_estimator_path: str | None = None
    tts_json_path: str | None = None
    unicode_indexer_path: str | None = None
    voice_style_path: str | None = None
    resource_urls: tuple[tuple[str, str], ...] = ()
    speakers: tuple[SherpaSpeakerCatalogEntry, ...] = ()
    sample_rate: int | None = None
    language_name: str | None = None
    country_name: str | None = None
    license_name: str | None = None
    license_url: str | None = None
    installed: bool = False

    @property
    def voice_id(self) -> str:
        """Return the catalog ID used by the generic catalog widget."""
        return self.bundle_id

    @property
    def language_code(self) -> str:
        """Return the primary language code for generic UI compatibility."""
        return self.language_codes[0] if self.language_codes else "und"

    @property
    def language_label(self) -> str:
        """Return readable labels for single- and multi-language archives."""
        codes = self.language_codes or ("und",)
        names = [LANGUAGE_NAMES.get(code.split("_", 1)[0], code.upper()) for code in codes]
        readable = self.language_name or " + ".join(names)
        code_label = ", ".join(codes)
        if self.country_name:
            return f"{readable} — {self.country_name} ({code_label})"
        return f"{readable} ({code_label})"

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.quality})"


__all__ = [
    "LANGUAGE_NAMES",
    "SherpaCatalogEntry",
    "SherpaSpeakerCatalogEntry",
    "VoiceCatalogEntry",
    "format_language_label",
]
