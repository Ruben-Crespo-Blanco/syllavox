"""Curated non-Piper model catalog for the Sherpa-ONNX backend."""

from __future__ import annotations

from syllavox.tts.catalog_models import (
    SherpaCatalogEntry,
    SherpaSpeakerCatalogEntry,
)


SHERPA_TTS_RELEASE_BASE_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models"
)
SHERPA_VOCODER_RELEASE_BASE_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models"
)
SHERPA_TTS_CATALOG_URL = (
    "https://k2-fsa.github.io/sherpa/onnx/tts/all/index.html"
)


_SUPERTONIC_LANGUAGES = (
    "en",
    "ko",
    "ja",
    "ar",
    "bg",
    "cs",
    "da",
    "de",
    "el",
    "es",
    "et",
    "fi",
    "fr",
    "hi",
    "hr",
    "hu",
    "id",
    "it",
    "lt",
    "lv",
    "nl",
    "pl",
    "pt",
    "ro",
    "ru",
    "sk",
    "sl",
    "sv",
    "tr",
    "uk",
    "vi",
)


def _archive_url(bundle_id: str) -> str:
    return f"{SHERPA_TTS_RELEASE_BASE_URL}/{bundle_id}.tar.bz2"


def _supertonic_speakers() -> tuple[SherpaSpeakerCatalogEntry, ...]:
    return tuple(
        SherpaSpeakerCatalogEntry(
            speaker_id=speaker_id,
            name=f"Speaker {speaker_id}",
            language_codes=(language_code,),
        )
        for language_code in _SUPERTONIC_LANGUAGES
        for speaker_id in range(10)
    )


_KOKORO_V1_1_SPEAKER_NAMES = (
    "af_maple",
    "af_sol",
    "bf_vale",
    "zf_001",
    "zf_002",
    "zf_003",
    "zf_004",
    "zf_005",
    "zf_006",
    "zf_007",
    "zf_008",
    "zf_017",
    "zf_018",
    "zf_019",
    "zf_021",
    "zf_022",
    "zf_023",
    "zf_024",
    "zf_026",
    "zf_027",
    "zf_028",
    "zf_032",
    "zf_036",
    "zf_038",
    "zf_039",
    "zf_040",
    "zf_042",
    "zf_043",
    "zf_044",
    "zf_046",
    "zf_047",
    "zf_048",
    "zf_049",
    "zf_051",
    "zf_059",
    "zf_060",
    "zf_067",
    "zf_070",
    "zf_071",
    "zf_072",
    "zf_073",
    "zf_074",
    "zf_075",
    "zf_076",
    "zf_077",
    "zf_078",
    "zf_079",
    "zf_083",
    "zf_084",
    "zf_085",
    "zf_086",
    "zf_087",
    "zf_088",
    "zf_090",
    "zf_092",
    "zf_093",
    "zf_094",
    "zf_099",
    "zm_009",
    "zm_010",
    "zm_011",
    "zm_012",
    "zm_013",
    "zm_014",
    "zm_015",
    "zm_016",
    "zm_020",
    "zm_025",
    "zm_029",
    "zm_030",
    "zm_031",
    "zm_033",
    "zm_034",
    "zm_035",
    "zm_037",
    "zm_041",
    "zm_045",
    "zm_050",
    "zm_052",
    "zm_053",
    "zm_054",
    "zm_055",
    "zm_056",
    "zm_057",
    "zm_058",
    "zm_061",
    "zm_062",
    "zm_063",
    "zm_064",
    "zm_065",
    "zm_066",
    "zm_068",
    "zm_069",
    "zm_080",
    "zm_081",
    "zm_082",
    "zm_089",
    "zm_091",
    "zm_095",
    "zm_096",
    "zm_097",
    "zm_098",
    "zm_100",
)


_KOKORO_V1_0_SPEAKER_NAMES = (
    "af_alloy",
    "af_aoede",
    "af_bella",
    "af_heart",
    "af_jessica",
    "af_kore",
    "af_nicole",
    "af_nova",
    "af_river",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_michael",
    "am_onyx",
    "am_puck",
    "am_santa",
    "bf_alice",
    "bf_emma",
    "bf_isabella",
    "bf_lily",
    "bm_daniel",
    "bm_fable",
    "bm_george",
    "bm_lewis",
    "ef_dora",
    "em_alex",
    "ff_siwis",
    "hf_alpha",
    "hf_beta",
    "hm_omega",
    "hm_psi",
    "if_sara",
    "im_nicola",
    "jf_alpha",
    "jf_gongitsune",
    "jf_nezumi",
    "jf_tebukuro",
    "jm_kumo",
    "pf_dora",
    "pm_alex",
    "pm_santa",
    "zf_xiaobei",
    "zf_xiaoni",
    "zf_xiaoxiao",
    "zf_xiaoyi",
    "zm_yunjian",
    "zm_yunxi",
    "zm_yunxia",
    "zm_yunyang",
)


_KOKORO_V0_19_SPEAKER_NAMES = (
    "af",
    "af_bella",
    "af_nicole",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_michael",
    "bf_emma",
    "bf_isabella",
    "bm_george",
    "bm_lewis",
)


_KITTEN_V0_8_SPEAKER_NAMES = (
    "expr-voice-2-m",
    "expr-voice-2-f",
    "expr-voice-3-m",
    "expr-voice-3-f",
    "expr-voice-4-m",
    "expr-voice-4-f",
    "expr-voice-5-m",
    "expr-voice-5-f",
)


def _kokoro_speakers(
    names: tuple[str, ...],
    first_chinese_id: int,
) -> tuple[SherpaSpeakerCatalogEntry, ...]:
    return tuple(
        SherpaSpeakerCatalogEntry(
            speaker_id=speaker_id,
            name=name,
            language_codes=(
                ("zh",) if speaker_id >= first_chinese_id else ("en",)
            ),
        )
        for speaker_id, name in enumerate(names)
    )


def _named_speakers(
    names: tuple[str, ...],
    language_codes: tuple[str, ...],
) -> tuple[SherpaSpeakerCatalogEntry, ...]:
    return tuple(
        SherpaSpeakerCatalogEntry(
            speaker_id=speaker_id,
            name=name,
            language_codes=language_codes,
        )
        for speaker_id, name in enumerate(names)
    )


def _mimic3_speakers(
    count: int,
    language_code: str,
) -> tuple[SherpaSpeakerCatalogEntry, ...]:
    """Expose Mimic3's fixed speaker IDs with stable neutral labels."""
    return tuple(
        SherpaSpeakerCatalogEntry(
            speaker_id=speaker_id,
            name=f"Mimic3 speaker {speaker_id}",
            language_codes=(language_code,),
        )
        for speaker_id in range(count)
    )


def get_sherpa_catalog_entries() -> tuple[SherpaCatalogEntry, ...]:
    """Return the v0.4 fixed-speaker Sherpa model catalog.

    Converted Piper archives are intentionally omitted. Piper remains the
    broad catalog for those voices, while this list focuses on model families
    that add value through Sherpa's native runtime.
    """
    return (
        SherpaCatalogEntry(
            bundle_id="kokoro-int8-multi-lang-v1_1",
            name="Kokoro multilingual v1.1 INT8",
            family="kokoro",
            language_codes=("en", "zh"),
            quality="int8",
            num_speakers=103,
            archive_url=_archive_url("kokoro-int8-multi-lang-v1_1"),
            model_path="model.int8.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            lexicon_paths=("lexicon-us-en.txt", "lexicon-zh.txt"),
            rule_fst_paths=("phone-zh.fst", "date-zh.fst", "number-zh.fst"),
            speakers=_kokoro_speakers(_KOKORO_V1_1_SPEAKER_NAMES, 3),
            sample_rate=24000,
            license_name="Kokoro model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kokoro.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kokoro-multi-lang-v1_1",
            name="Kokoro multilingual v1.1",
            family="kokoro",
            language_codes=("en", "zh"),
            quality="full precision",
            num_speakers=103,
            archive_url=_archive_url("kokoro-multi-lang-v1_1"),
            model_path="model.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            lexicon_paths=("lexicon-us-en.txt", "lexicon-zh.txt"),
            rule_fst_paths=("phone-zh.fst", "date-zh.fst", "number-zh.fst"),
            speakers=_kokoro_speakers(_KOKORO_V1_1_SPEAKER_NAMES, 3),
            sample_rate=24000,
            license_name="Kokoro model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kokoro.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kokoro-multi-lang-v1_0",
            name="Kokoro multilingual v1.0",
            family="kokoro",
            language_codes=("en", "zh"),
            quality="standard",
            num_speakers=53,
            archive_url=_archive_url("kokoro-multi-lang-v1_0"),
            model_path="model.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            dict_dir_path="dict",
            lexicon_paths=(
                "lexicon-gb-en.txt",
                "lexicon-us-en.txt",
                "lexicon-zh.txt",
            ),
            rule_fst_paths=("phone-zh.fst", "date-zh.fst", "number-zh.fst"),
            speakers=_kokoro_speakers(_KOKORO_V1_0_SPEAKER_NAMES, 45),
            sample_rate=24000,
            license_name="Kokoro model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kokoro.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kokoro-en-v0_19",
            name="Kokoro English v0.19",
            family="kokoro",
            language_codes=("en",),
            quality="standard",
            num_speakers=11,
            archive_url=_archive_url("kokoro-en-v0_19"),
            model_path="model.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            speakers=_kokoro_speakers(_KOKORO_V0_19_SPEAKER_NAMES, 11),
            sample_rate=24000,
            license_name="Kokoro model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kokoro.html",
        ),
        SherpaCatalogEntry(
            bundle_id="matcha-icefall-en_US-ljspeech",
            name="Matcha English LJSpeech",
            family="matcha",
            language_codes=("en_US",),
            quality="standard",
            num_speakers=1,
            archive_url=_archive_url("matcha-icefall-en_US-ljspeech"),
            tokens_path="tokens.txt",
            data_dir_path="espeak-ng-data",
            acoustic_model_path="model-steps-3.onnx",
            vocoder_path="vocos-22khz-univ.onnx",
            resource_urls=(
                (
                    "vocoder",
                    f"{SHERPA_VOCODER_RELEASE_BASE_URL}/vocos-22khz-univ.onnx",
                ),
            ),
            sample_rate=22050,
            license_name="LJ Speech dataset/model terms; review before use",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/matcha.html",
        ),
        SherpaCatalogEntry(
            bundle_id="matcha-icefall-zh-baker",
            name="Matcha Chinese Baker",
            family="matcha",
            language_codes=("zh",),
            quality="standard",
            num_speakers=1,
            archive_url=_archive_url("matcha-icefall-zh-baker"),
            tokens_path="tokens.txt",
            lexicon_paths=("lexicon.txt",),
            rule_fst_paths=("phone.fst", "date.fst", "number.fst"),
            acoustic_model_path="model-steps-3.onnx",
            vocoder_path="vocos-22khz-univ.onnx",
            resource_urls=(
                (
                    "vocoder",
                    f"{SHERPA_VOCODER_RELEASE_BASE_URL}/vocos-22khz-univ.onnx",
                ),
            ),
            sample_rate=22050,
            license_name="Baker dataset is non-commercial; review all terms",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/matcha.html",
        ),
        SherpaCatalogEntry(
            bundle_id="matcha-icefall-zh-en",
            name="Matcha Chinese + English",
            family="matcha",
            language_codes=("zh", "en"),
            quality="standard",
            num_speakers=1,
            archive_url=_archive_url("matcha-icefall-zh-en"),
            tokens_path="tokens.txt",
            data_dir_path="espeak-ng-data",
            lexicon_paths=("lexicon.txt",),
            rule_fst_paths=("phone-zh.fst", "date-zh.fst", "number-zh.fst"),
            acoustic_model_path="model-steps-3.onnx",
            vocoder_path="vocos-16khz-univ.onnx",
            resource_urls=(
                (
                    "vocoder",
                    f"{SHERPA_VOCODER_RELEASE_BASE_URL}/vocos-16khz-univ.onnx",
                ),
            ),
            sample_rate=16000,
            license_name="Matcha Chinese + English model terms; review before use",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/all/Chinese-English/matcha-icefall-zh-en.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kitten-nano-en-v0_1-fp16",
            name="KittenTTS Nano English v0.1",
            family="kitten",
            language_codes=("en",),
            quality="fp16",
            num_speakers=8,
            archive_url=_archive_url("kitten-nano-en-v0_1-fp16"),
            model_path="model.fp16.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            license_name="KittenTTS model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kitten.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kitten-nano-en-v0_2-fp16",
            name="KittenTTS Nano English v0.2",
            family="kitten",
            language_codes=("en",),
            quality="fp16",
            num_speakers=8,
            archive_url=_archive_url("kitten-nano-en-v0_2-fp16"),
            model_path="model.fp16.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            license_name="KittenTTS model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kitten.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kitten-mini-en-v0_1-fp16",
            name="KittenTTS Mini English v0.1",
            family="kitten",
            language_codes=("en",),
            quality="fp16",
            num_speakers=8,
            archive_url=_archive_url("kitten-mini-en-v0_1-fp16"),
            model_path="model.fp16.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            license_name="KittenTTS model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kitten.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kitten-nano-en-v0_8-fp32",
            name="KittenTTS Nano English v0.8 FP32",
            family="kitten",
            language_codes=("en",),
            quality="fp32",
            num_speakers=8,
            archive_url=_archive_url("kitten-nano-en-v0_8-fp32"),
            model_path="model.fp32.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            speakers=_named_speakers(_KITTEN_V0_8_SPEAKER_NAMES, ("en",)),
            sample_rate=24000,
            license_name="KittenTTS model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/all/English/kitten-nano-en-v0_8-fp32.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kitten-nano-en-v0_8-int8",
            name="KittenTTS Nano English v0.8 INT8",
            family="kitten",
            language_codes=("en",),
            quality="int8",
            num_speakers=8,
            archive_url=_archive_url("kitten-nano-en-v0_8-int8"),
            model_path="model.int8.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            speakers=_named_speakers(_KITTEN_V0_8_SPEAKER_NAMES, ("en",)),
            sample_rate=24000,
            license_name="KittenTTS model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/all/English/kitten-nano-en-v0_8-int8.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kitten-micro-en-v0_8",
            name="KittenTTS Micro English v0.8",
            family="kitten",
            language_codes=("en",),
            quality="standard",
            num_speakers=8,
            archive_url=_archive_url("kitten-micro-en-v0_8"),
            model_path="model.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            speakers=_named_speakers(_KITTEN_V0_8_SPEAKER_NAMES, ("en",)),
            sample_rate=24000,
            license_name="KittenTTS model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/all/English/kitten-micro-en-v0_8.html",
        ),
        SherpaCatalogEntry(
            bundle_id="kitten-mini-en-v0_8",
            name="KittenTTS Mini English v0.8",
            family="kitten",
            language_codes=("en",),
            quality="standard",
            num_speakers=8,
            archive_url=_archive_url("kitten-mini-en-v0_8"),
            model_path="model.onnx",
            tokens_path="tokens.txt",
            voices_path="voices.bin",
            data_dir_path="espeak-ng-data",
            speakers=_named_speakers(_KITTEN_V0_8_SPEAKER_NAMES, ("en",)),
            sample_rate=24000,
            license_name="KittenTTS model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/all/English/kitten-mini-en-v0_8.html",
        ),
        SherpaCatalogEntry(
            bundle_id="vits-inflect-en-nano-v2",
            name="Inflect English Nano v2",
            family="vits",
            language_codes=("en",),
            quality="standard",
            num_speakers=1,
            archive_url=_archive_url("vits-inflect-en-nano-v2"),
            model_path="model.onnx",
            tokens_path="tokens.txt",
            data_dir_path="espeak-ng-data",
            speakers=_named_speakers(("Inflect Nano",), ("en",)),
            sample_rate=24000,
            license_name="Inflect model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/all/English/vits-inflect-en-nano-v2.html",
        ),
        SherpaCatalogEntry(
            bundle_id="vits-inflect-en-micro-v2",
            name="Inflect English Micro v2",
            family="vits",
            language_codes=("en",),
            quality="standard",
            num_speakers=1,
            archive_url=_archive_url("vits-inflect-en-micro-v2"),
            model_path="model.onnx",
            tokens_path="tokens.txt",
            data_dir_path="espeak-ng-data",
            speakers=_named_speakers(("Inflect Micro",), ("en",)),
            sample_rate=24000,
            license_name="Inflect model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/all/English/vits-inflect-en-micro-v2.html",
        ),
        SherpaCatalogEntry(
            bundle_id="vits-melo-tts-zh_en",
            name="MeloTTS Chinese + English",
            family="vits",
            language_codes=("zh", "en"),
            quality="standard",
            num_speakers=1,
            archive_url=_archive_url("vits-melo-tts-zh_en"),
            model_path="model.onnx",
            tokens_path="tokens.txt",
            lexicon_paths=("lexicon.txt",),
            rule_fst_paths=("phone.fst", "date.fst", "number.fst"),
            sample_rate=44100,
            license_name="MeloTTS model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html",
        ),
        SherpaCatalogEntry(
            bundle_id="vits-mimic3-af_ZA-google-nwu_low",
            name="Mimic3 Afrikaans (Google NWU)",
            family="vits",
            language_codes=("af",),
            quality="low",
            num_speakers=9,
            archive_url=_archive_url("vits-mimic3-af_ZA-google-nwu_low"),
            model_path="af_ZA-google-nwu_low.onnx",
            tokens_path="tokens.txt",
            data_dir_path="espeak-ng-data",
            speakers=_mimic3_speakers(9, "af"),
            sample_rate=22050,
            language_name="Afrikaans",
            country_name="South Africa",
            source_url=(
                "https://huggingface.co/csukuangfj/"
                "vits-mimic3-af_ZA-google-nwu_low"
            ),
            license_name=(
                "CC BY-SA 4.0 voice repository; dataset terms apply"
            ),
            license_url="https://github.com/MycroftAI/mimic3-voices/blob/master/LICENSE",
            archive_sha256=(
                "a4d2649d4b5e72e04d981c843e419b41d76845eec297a9c06f73bdd44e79ac1f"
            ),
        ),
        SherpaCatalogEntry(
            bundle_id="vits-mimic3-bn-multi_low",
            name="Mimic3 Bengali multi-speaker",
            family="vits",
            language_codes=("bn",),
            quality="low",
            num_speakers=16,
            archive_url=_archive_url("vits-mimic3-bn-multi_low"),
            model_path="bn-multi_low.onnx",
            tokens_path="tokens.txt",
            data_dir_path="espeak-ng-data",
            speakers=_mimic3_speakers(16, "bn"),
            sample_rate=22050,
            language_name="Bengali",
            country_name="Bangladesh",
            source_url=(
                "https://huggingface.co/csukuangfj/"
                "vits-mimic3-bn-multi_low"
            ),
            license_name=(
                "CC BY-SA 4.0 voice repository; CMU Indic and dataset terms apply"
            ),
            license_url="https://github.com/MycroftAI/mimic3-voices/blob/master/LICENSE",
            archive_sha256=(
                "a921a622e9dac5e0ad4bfe9f4a02b6d15fe6797532213718305e06312b7a0ae3"
            ),
        ),
        SherpaCatalogEntry(
            bundle_id="vits-mimic3-gu_IN-cmu-indic_low",
            name="Mimic3 Gujarati (CMU Indic)",
            family="vits",
            language_codes=("gu",),
            quality="low",
            num_speakers=3,
            archive_url=_archive_url("vits-mimic3-gu_IN-cmu-indic_low"),
            model_path="gu_IN-cmu-indic_low.onnx",
            tokens_path="tokens.txt",
            data_dir_path="espeak-ng-data",
            speakers=_mimic3_speakers(3, "gu"),
            sample_rate=22050,
            language_name="Gujarati",
            country_name="India",
            source_url=(
                "https://huggingface.co/csukuangfj/"
                "vits-mimic3-gu_IN-cmu-indic_low"
            ),
            license_name=(
                "CC BY-SA 4.0 voice repository; CMU Indic and dataset terms apply"
            ),
            license_url="https://github.com/MycroftAI/mimic3-voices/blob/master/LICENSE",
            archive_sha256=(
                "ed6849f311bac71cc9f76b33d32412671ca201ea4b3b575f7b28d67e26eac6ae"
            ),
        ),
        SherpaCatalogEntry(
            bundle_id="vits-mimic3-tn_ZA-google-nwu_low",
            name="Mimic3 Tswana (Google NWU)",
            family="vits",
            language_codes=("tn",),
            quality="low",
            num_speakers=26,
            archive_url=_archive_url("vits-mimic3-tn_ZA-google-nwu_low"),
            model_path="tn_ZA-google-nwu_low.onnx",
            tokens_path="tokens.txt",
            data_dir_path="espeak-ng-data",
            speakers=_mimic3_speakers(26, "tn"),
            sample_rate=22050,
            language_name="Tswana",
            country_name="South Africa",
            source_url=(
                "https://huggingface.co/csukuangfj/"
                "vits-mimic3-tn_ZA-google-nwu_low"
            ),
            license_name=(
                "CC BY-SA 4.0 voice repository; dataset terms apply"
            ),
            license_url="https://github.com/MycroftAI/mimic3-voices/blob/master/LICENSE",
            archive_sha256=(
                "7f43753eb4d3c4b17ff43c8764d2fb90204ba5e8247ee4023cfe9e0ac40816d3"
            ),
        ),
        SherpaCatalogEntry(
            bundle_id="sherpa-onnx-supertonic-3-tts-int8-2026-05-11",
            name="Supertonic 3 multilingual",
            family="supertonic",
            language_codes=_SUPERTONIC_LANGUAGES,
            quality="int8",
            num_speakers=10,
            archive_url=_archive_url(
                "sherpa-onnx-supertonic-3-tts-int8-2026-05-11"
            ),
            duration_predictor_path="duration_predictor.int8.onnx",
            text_encoder_path="text_encoder.int8.onnx",
            vector_estimator_path="vector_estimator.int8.onnx",
            vocoder_path="vocoder.int8.onnx",
            tts_json_path="tts.json",
            unicode_indexer_path="unicode_indexer.bin",
            voice_style_path="voice.bin",
            speakers=_supertonic_speakers(),
            # The current Supertonic 3 release emits 44.1 kHz PCM.  Keep this
            # explicit because Syllavox validates the runtime output rate.
            sample_rate=44100,
            license_name="Supertonic model terms; review before use or redistribution",
            license_url="https://k2-fsa.github.io/sherpa/onnx/tts/supertonic.html",
        ),
    )


__all__ = [
    "SHERPA_TTS_CATALOG_URL",
    "SHERPA_TTS_RELEASE_BASE_URL",
    "SHERPA_VOCODER_RELEASE_BASE_URL",
    "get_sherpa_catalog_entries",
]
