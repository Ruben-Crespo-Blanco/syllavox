"""Optional Sherpa-ONNX backend and local model-bundle reader.

The backend is intentionally lazy: importing Syllavox does not import the
optional native Sherpa runtime. A bundle is a directory containing a
``bundle.json`` manifest and the model files referenced by that manifest.
This keeps the default Piper installation small and makes model licensing and
redistribution decisions explicit for each bundle.
"""

from __future__ import annotations

import json
import math
import re
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from syllavox.logging_config import get_logger
from syllavox.tts.base import (
    AudioRetention,
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    TTSBackend,
    VoiceInfo,
    VoiceMemoryBackend,
)
from syllavox.tts.catalog_models import LANGUAGE_NAMES
from syllavox.tts.errors import (
    BackendUnavailableError,
    SynthesisFailedError,
    TTSBackendError,
    VoiceNotFoundError,
)
from syllavox.tts.paths import (
    get_request_audio_path,
    get_retained_audio_path,
    get_sherpa_onnx_models_dir,
)


SHERPA_ONNX_BACKEND_NAME = "sherpa-onnx"
SHERPA_VOICE_PREFIX = "sherpa-onnx:"
MANIFEST_FILENAME = "bundle.json"
SUPPORTED_MODEL_FAMILIES = frozenset(
    {"vits", "matcha", "kokoro", "kitten", "supertonic"}
)
_SAFE_BUNDLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_VOICE_ID = re.compile(
    rf"^{re.escape(SHERPA_VOICE_PREFIX)}(?P<bundle>[^#]+)#sid=(?P<sid>[0-9]+)"
    rf"(?:&lang=(?P<lang>[A-Za-z0-9_-]+))?$"
)


@dataclass(frozen=True)
class SherpaSpeaker:
    """One speaker exposed by a model bundle."""

    speaker_id: int
    name: str
    language_codes: tuple[str, ...]
    language_name: str | None = None
    country_name: str | None = None


@dataclass(frozen=True)
class SherpaModelBundle:
    """Validated manifest metadata and resolved paths for one bundle."""

    bundle_id: str
    display_name: str
    family: str
    root: Path
    model_path: Path | None
    tokens_path: Path | None
    voices_path: Path | None
    data_dir_path: Path | None
    dict_dir_path: Path | None
    lexicon_paths: tuple[Path, ...]
    rule_fst_paths: tuple[Path, ...]
    rule_far_paths: tuple[Path, ...]
    acoustic_model_path: Path | None
    vocoder_path: Path | None
    duration_predictor_path: Path | None
    text_encoder_path: Path | None
    vector_estimator_path: Path | None
    tts_json_path: Path | None
    unicode_indexer_path: Path | None
    voice_style_path: Path | None
    language_codes: tuple[str, ...]
    language_name: str | None
    country_name: str | None
    quality: str | None
    speakers: tuple[SherpaSpeaker, ...]
    sample_rate: int | None
    license_name: str | None
    license_url: str | None


class SherpaManifestError(TTSBackendError):
    """Raised when a Sherpa bundle manifest is malformed or unsafe."""


class SherpaOnnxBackend(TTSBackend, VoiceMemoryBackend):
    """CPU-first Sherpa-ONNX ``OfflineTts`` adapter.

    Supported in the v0.4 implementation:

    - VITS bundles, excluding converted Piper archives from the v0.4 catalog;
    - Matcha bundles with their acoustic model and vocoder;
    - Kokoro, including multilingual and INT8 bundles;
    - Kitten, for compact English models;
    - Supertonic multilingual bundles with speaker and language selection.

    ZipVoice and Pocket are intentionally not included: both require
    reference-audio voice cloning, which is a separate product capability from
    Syllavox's fixed-voice request contract.

    The adapter shares Syllavox's WAV artifact and voice-memory contracts with
    Piper. It caches one ``OfflineTts`` instance per bundle, so multiple
    speakers in one Kokoro bundle do not duplicate the model in memory.
    """

    def __init__(
        self,
        models_dir: Path | None = None,
        *,
        provider: str = "cpu",
        num_threads: int = 2,
        max_num_sentences: int = 1,
    ) -> None:
        self._models_dir = Path(models_dir or get_sherpa_onnx_models_dir())
        self._provider = provider
        self._num_threads = max(1, int(num_threads))
        self._max_num_sentences = max(1, int(max_num_sentences))
        self._runtime: Any | None = None
        self._loaded_bundles: dict[str, Any] = {}
        self._loaded_voice_ids: set[str] = set()
        self._logger = get_logger(__name__)

    @property
    def models_dir(self) -> Path:
        """Return the root directory containing Sherpa bundle folders."""
        return self._models_dir

    def backend_name(self) -> str:
        return SHERPA_ONNX_BACKEND_NAME

    def health(self) -> BackendHealth:
        """Report runtime and local-bundle health without loading a model."""
        try:
            runtime = self._import_runtime()
        except Exception as exc:
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details=(
                    "Sherpa-ONNX is not installed. Install the optional "
                    f"dependency with `pip install 'sherpa-onnx==1.13.6' "
                    f"'sherpa-onnx-bin==1.13.6'`: {exc}"
                ),
            )

        bundles, errors = self._discover_bundles()
        if not bundles:
            details = "No Sherpa-ONNX model bundles found."
            if errors:
                details += f" {len(errors)} manifest(s) could not be read."
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details=details,
            )

        incomplete_count = sum(
            bool(self._bundle_file_errors(bundle)) for bundle in bundles
        )
        runtime_version = getattr(runtime, "__version__", None)
        version_text = (
            f" Runtime {runtime_version}." if runtime_version else ""
        )
        details = (
            f"{len(bundles)} bundle(s) available; "
            f"{sum(len(bundle.speakers) for bundle in bundles)} voice(s) "
            f"discovered; {len(self._loaded_bundles)} bundle(s) loaded."
            f"{version_text}"
        )
        if incomplete_count:
            details += f" {incomplete_count} bundle(s) have missing files."
        if errors:
            details += f" {len(errors)} invalid manifest(s) ignored."

        return BackendHealth(
            name=self.backend_name(),
            healthy=True,
            details=details,
        )

    def list_voices(self) -> list[VoiceInfo]:
        """Return manifest speakers as stable backend-qualified voice IDs."""
        voices: list[VoiceInfo] = []
        bundles, _ = self._discover_bundles()

        for bundle in bundles:
            for speaker in bundle.speakers:
                language_code = (
                    speaker.language_codes[0]
                    if speaker.language_codes
                    else bundle.language_codes[0]
                )
                language_family = _language_family(language_code)
                language_name = (
                    speaker.language_name
                    or bundle.language_name
                    or LANGUAGE_NAMES.get(language_family)
                )
                display_name = speaker.name
                if len(bundle.speakers) > 1 or bundle.display_name:
                    display_name = f"{speaker.name} · {bundle.display_name}"

                voices.append(
                    VoiceInfo(
                        voice_id=self.voice_id(
                            bundle,
                            speaker.speaker_id,
                            language_code=(
                                language_code
                                if bundle.family == "supertonic"
                                else None
                            ),
                        ),
                        name=display_name,
                        language=language_family,
                        language_code=language_code,
                        language_name=language_name,
                        country_name=(
                            speaker.country_name or bundle.country_name
                        ),
                        quality=bundle.quality,
                    )
                )

        return sorted(
            voices,
            key=lambda voice: (
                (voice.language_name or voice.language).lower(),
                voice.name.lower(),
                voice.voice_id,
            ),
        )

    def list_bundles(self) -> list[SherpaModelBundle]:
        """Return parsed manifests, including bundles with missing model files."""
        bundles, _ = self._discover_bundles()
        return bundles

    def bundle_diagnostics(self) -> list[str]:
        """Return actionable diagnostics for invalid or incomplete bundles."""
        bundles, errors = self._discover_bundles()
        diagnostics = [f"{path}: {error}" for path, error in errors]
        for bundle in bundles:
            diagnostics.extend(
                f"{bundle.bundle_id}: {error}"
                for error in self._bundle_file_errors(bundle)
            )
        return diagnostics

    def voice_model_size(self, voice_id: str) -> int:
        """Return the complete on-disk size of the voice's model bundle."""
        bundle, _ = self._lookup_voice(voice_id)
        total = 0
        if not bundle.root.exists():
            return total

        for path in bundle.root.rglob("*"):
            if path.is_file():
                try:
                    total += path.stat().st_size
                except OSError:
                    continue
        return total

    def load_voice(self, voice_id: str) -> Any:
        """Create and cache the Sherpa ``OfflineTts`` object for a bundle."""
        bundle, speaker = self._lookup_voice(voice_id)
        if bundle.bundle_id not in self._loaded_bundles:
            self._validate_bundle_files(bundle)
            runtime = self._import_runtime()
            try:
                tts_config = self._build_tts_config(runtime, bundle)
                validate = getattr(tts_config, "validate", None)
                if callable(validate) and validate() is False:
                    raise SherpaManifestError(
                        f"Sherpa rejected the configuration for bundle "
                        f"{bundle.bundle_id}."
                    )
                self._loaded_bundles[bundle.bundle_id] = runtime.OfflineTts(
                    tts_config
                )
            except SherpaManifestError:
                raise
            except Exception as exc:
                raise SynthesisFailedError(
                    f"Failed to load Sherpa bundle {bundle.bundle_id}: {exc}"
                ) from exc

        del speaker
        self._loaded_voice_ids.add(voice_id)
        return self._loaded_bundles[bundle.bundle_id]

    def unload_voice(self, voice_id: str) -> None:
        """Release a speaker and its bundle when no speaker still uses it."""
        bundle, _ = self._lookup_voice(voice_id)
        self._loaded_voice_ids.discard(voice_id)
        if not any(
            self._voice_bundle_id(loaded_id) == bundle.bundle_id
            for loaded_id in self._loaded_voice_ids
        ):
            self._loaded_bundles.pop(bundle.bundle_id, None)

    def is_voice_loaded(self, voice_id: str) -> bool:
        return voice_id in self._loaded_voice_ids

    def loaded_voice_ids(self) -> list[str]:
        return sorted(self._loaded_voice_ids)

    def shutdown(self) -> None:
        """Release cached OfflineTts instances and speaker references."""
        self._loaded_voice_ids.clear()
        self._loaded_bundles.clear()

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Generate Sherpa PCM audio and write Syllavox's standard WAV file."""
        voice_id = request.voice_id
        if voice_id is None:
            raise SynthesisFailedError(
                "Sherpa-ONNX synthesis requires a resolved voice ID."
            )

        bundle, speaker = self._lookup_voice(voice_id)
        working_audio_path: Path | None = None
        synthesis_succeeded = False

        try:
            audio_path, working_audio_path = self._prepare_output_paths(request)
            tts = self.load_voice(voice_id)
            runtime = self._import_runtime()
            generation_config = runtime.GenerationConfig()
            generation_config.sid = speaker.speaker_id
            generation_config.speed = 1.0
            generation_config.silence_scale = 0.2
            if (
                bundle.family in {"kokoro", "supertonic"}
                and len(speaker.language_codes) == 1
            ):
                generation_config.extra = {
                    "lang": speaker.language_codes[0],
                }

            audio = tts.generate(request.text, generation_config)
            self._write_wav(
                working_audio_path,
                audio,
                expected_sample_rate=bundle.sample_rate,
                runtime=runtime,
            )
            self._validate_output_path(working_audio_path)

            if request.output_path is not None:
                working_audio_path.replace(audio_path)

            synthesis_succeeded = True
            return SynthesisResult(
                request_id=request.request_id,
                voice_id=voice_id,
                audio_path=audio_path,
                mime_type="audio/wav",
                retention=request.retention,
            )
        except (BackendUnavailableError, VoiceNotFoundError, SynthesisFailedError):
            raise
        except Exception as exc:
            raise SynthesisFailedError(
                f"Sherpa-ONNX synthesis failed for {bundle.bundle_id}: {exc}"
            ) from exc
        finally:
            if not synthesis_succeeded and working_audio_path is not None:
                self._cleanup_partial_output(working_audio_path)

    @staticmethod
    def voice_id(
        bundle: SherpaModelBundle,
        speaker_id: int,
        language_code: str | None = None,
    ) -> str:
        """Build the stable ID exposed through the API and UI."""
        voice_id = f"{SHERPA_VOICE_PREFIX}{bundle.bundle_id}#sid={speaker_id}"
        if language_code:
            voice_id += f"&lang={language_code}"
        return voice_id

    def _import_runtime(self) -> Any:
        if self._runtime is not None:
            return self._runtime

        try:
            import sherpa_onnx
        except Exception as exc:
            raise BackendUnavailableError(
                "The optional sherpa-onnx Python runtime is unavailable."
            ) from exc

        self._runtime = sherpa_onnx
        return sherpa_onnx

    def _discover_bundles(
        self,
    ) -> tuple[list[SherpaModelBundle], list[tuple[Path, str]]]:
        if not self._models_dir.exists():
            return [], []

        bundles: list[SherpaModelBundle] = []
        errors: list[tuple[Path, str]] = []
        for manifest_path in sorted(self._models_dir.rglob(MANIFEST_FILENAME)):
            try:
                bundles.append(self._read_manifest(manifest_path))
            except Exception as exc:
                errors.append((manifest_path, str(exc)))
        return bundles, errors

    def _read_manifest(self, manifest_path: Path) -> SherpaModelBundle:
        root = manifest_path.parent.resolve()
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SherpaManifestError(f"Could not parse manifest: {exc}") from exc

        if not isinstance(payload, dict):
            raise SherpaManifestError("Manifest must contain a JSON object.")

        schema_version = payload.get("schema_version", 1)
        if schema_version != 1:
            raise SherpaManifestError(
                f"Unsupported Sherpa bundle schema version: {schema_version}."
            )

        bundle_id = _required_string(payload, "bundle_id")
        if not _SAFE_BUNDLE_ID.fullmatch(bundle_id):
            raise SherpaManifestError(
                "bundle_id must contain only letters, numbers, '.', '_' or '-'."
            )

        family = _required_string(payload, "family").lower()
        if family not in SUPPORTED_MODEL_FAMILIES:
            supported = ", ".join(sorted(SUPPORTED_MODEL_FAMILIES))
            raise SherpaManifestError(
                f"Unsupported Sherpa model family '{family}'. Supported: {supported}."
            )

        files = payload.get("files", {})
        if files is None:
            files = {}
        if not isinstance(files, dict):
            raise SherpaManifestError("Manifest field 'files' must be an object.")

        def manifest_value(key: str) -> Any:
            return payload[key] if key in payload else files.get(key)

        model_path = _resolve_optional_bundle_path(
            root,
            manifest_value("model"),
            field="model",
        )
        tokens_path = _resolve_optional_bundle_path(
            root,
            manifest_value("tokens"),
            field="tokens",
        )
        voices_path = _resolve_optional_bundle_path(
            root,
            manifest_value("voices"),
            field="voices",
        )
        if family in {"kokoro", "kitten"} and voices_path is None:
            raise SherpaManifestError(
                f"The {family} family requires a voices file."
            )

        data_dir_path = _resolve_optional_bundle_path(
            root,
            manifest_value("data_dir"),
            field="data_dir",
        )
        dict_dir_path = _resolve_optional_bundle_path(
            root,
            manifest_value("dict_dir"),
            field="dict_dir",
        )

        acoustic_model_path = _resolve_optional_bundle_path(
            root,
            manifest_value("acoustic_model"),
            field="acoustic_model",
        )
        vocoder_path = _resolve_optional_bundle_path(
            root,
            manifest_value("vocoder"),
            field="vocoder",
        )
        duration_predictor_path = _resolve_optional_bundle_path(
            root,
            manifest_value("duration_predictor"),
            field="duration_predictor",
        )
        text_encoder_path = _resolve_optional_bundle_path(
            root,
            manifest_value("text_encoder"),
            field="text_encoder",
        )
        vector_estimator_path = _resolve_optional_bundle_path(
            root,
            manifest_value("vector_estimator"),
            field="vector_estimator",
        )
        tts_json_path = _resolve_optional_bundle_path(
            root,
            manifest_value("tts_json"),
            field="tts_json",
        )
        unicode_indexer_path = _resolve_optional_bundle_path(
            root,
            manifest_value("unicode_indexer"),
            field="unicode_indexer",
        )
        voice_style_path = _resolve_optional_bundle_path(
            root,
            manifest_value("voice_style"),
            field="voice_style",
        )

        if family in {"vits", "kokoro", "kitten"}:
            if model_path is None or tokens_path is None:
                raise SherpaManifestError(
                    f"The {family} family requires model and tokens files."
                )
        elif family == "matcha":
            if acoustic_model_path is None or vocoder_path is None or tokens_path is None:
                raise SherpaManifestError(
                    "The matcha family requires acoustic_model, vocoder, and tokens files."
                )
        elif family == "supertonic":
            required_supertonic_paths = (
                duration_predictor_path,
                text_encoder_path,
                vector_estimator_path,
                vocoder_path,
                tts_json_path,
                unicode_indexer_path,
                voice_style_path,
            )
            if any(path is None for path in required_supertonic_paths):
                raise SherpaManifestError(
                    "The supertonic family requires all model, metadata, and voice-style files."
                )

        lexicon_paths = _resolve_bundle_paths(
            root,
            manifest_value("lexicon") or [],
            field="lexicon",
        )
        rule_fst_paths = _resolve_bundle_paths(
            root,
            manifest_value("rule_fsts") or [],
            field="rule_fsts",
        )
        rule_far_paths = _resolve_bundle_paths(
            root,
            manifest_value("rule_fars") or [],
            field="rule_fars",
        )
        language_codes = _language_codes(payload.get("language_codes", []))
        speakers = _speakers_from_manifest(
            payload.get("speakers"),
            payload.get("speaker_count"),
            language_codes,
        )

        return SherpaModelBundle(
            bundle_id=bundle_id,
            display_name=str(payload.get("display_name") or bundle_id),
            family=family,
            root=root,
            model_path=model_path,
            tokens_path=tokens_path,
            voices_path=voices_path,
            data_dir_path=data_dir_path,
            dict_dir_path=dict_dir_path,
            lexicon_paths=lexicon_paths,
            rule_fst_paths=rule_fst_paths,
            rule_far_paths=rule_far_paths,
            acoustic_model_path=acoustic_model_path,
            vocoder_path=vocoder_path,
            duration_predictor_path=duration_predictor_path,
            text_encoder_path=text_encoder_path,
            vector_estimator_path=vector_estimator_path,
            tts_json_path=tts_json_path,
            unicode_indexer_path=unicode_indexer_path,
            voice_style_path=voice_style_path,
            language_codes=language_codes,
            language_name=_optional_string(payload, "language_name"),
            country_name=_optional_string(payload, "country_name"),
            quality=_optional_string(payload, "quality"),
            speakers=speakers,
            sample_rate=_sample_rate(payload.get("sample_rate")),
            license_name=_optional_string(payload, "license"),
            license_url=_optional_string(payload, "license_url"),
        )

    def _lookup_voice(
        self,
        voice_id: str,
    ) -> tuple[SherpaModelBundle, SherpaSpeaker]:
        match = _VOICE_ID.fullmatch(voice_id)
        if match is None:
            raise VoiceNotFoundError(voice_id)

        bundle_id = match.group("bundle")
        speaker_id = int(match.group("sid"))
        bundles, _ = self._discover_bundles()
        bundle = next(
            (candidate for candidate in bundles if candidate.bundle_id == bundle_id),
            None,
        )
        if bundle is None:
            raise VoiceNotFoundError(voice_id)

        requested_language = match.group("lang")
        speaker = next(
            (
                candidate
                for candidate in bundle.speakers
                if candidate.speaker_id == speaker_id
                and (
                    requested_language is None
                    or requested_language in candidate.language_codes
                )
            ),
            None,
        )
        if speaker is None:
            raise VoiceNotFoundError(voice_id)
        return bundle, speaker

    def _voice_bundle_id(self, voice_id: str) -> str | None:
        match = _VOICE_ID.fullmatch(voice_id)
        return match.group("bundle") if match else None

    def _bundle_file_errors(self, bundle: SherpaModelBundle) -> list[str]:
        errors: list[str] = []
        required_files: list[tuple[Path | None, str]] = []
        if bundle.family in {"vits", "kokoro", "kitten"}:
            required_files.extend(
                (
                    (bundle.model_path, "model"),
                    (bundle.tokens_path, "tokens"),
                )
            )
        if bundle.family in {"kokoro", "kitten"}:
            required_files.append((bundle.voices_path, "voices"))
        if bundle.family == "matcha":
            required_files.extend(
                (
                    (bundle.acoustic_model_path, "acoustic model"),
                    (bundle.vocoder_path, "vocoder"),
                    (bundle.tokens_path, "tokens"),
                )
            )
        if bundle.family == "supertonic":
            required_files.extend(
                (
                    (bundle.duration_predictor_path, "duration predictor"),
                    (bundle.text_encoder_path, "text encoder"),
                    (bundle.vector_estimator_path, "vector estimator"),
                    (bundle.vocoder_path, "vocoder"),
                    (bundle.tts_json_path, "tts metadata"),
                    (bundle.unicode_indexer_path, "unicode indexer"),
                    (bundle.voice_style_path, "voice style"),
                )
            )
        for path, label in required_files:
            if path is None:
                errors.append(f"missing {label} path in manifest")
            elif not path.is_file():
                errors.append(f"missing {label} file: {path.name}")
        if bundle.data_dir_path is not None and not bundle.data_dir_path.is_dir():
            errors.append(f"missing data directory: {bundle.data_dir_path.name}")
        if bundle.dict_dir_path is not None and not bundle.dict_dir_path.is_dir():
            errors.append(f"missing dictionary directory: {bundle.dict_dir_path.name}")
        for path in (
            *bundle.lexicon_paths,
            *bundle.rule_fst_paths,
            *bundle.rule_far_paths,
        ):
            if not path.is_file():
                errors.append(f"missing auxiliary file: {path.name}")
        return errors

    def _validate_bundle_files(self, bundle: SherpaModelBundle) -> None:
        errors = self._bundle_file_errors(bundle)
        if errors:
            raise SynthesisFailedError(
                f"Sherpa bundle {bundle.bundle_id} is incomplete: "
                + "; ".join(errors)
            )

    def _build_tts_config(self, runtime: Any, bundle: SherpaModelBundle) -> Any:
        def path_text(path: Path | None) -> str:
            return str(path) if path is not None else ""

        model_config = runtime.OfflineTtsModelConfig(
            vits=runtime.OfflineTtsVitsModelConfig(
                model=path_text(bundle.model_path if bundle.family == "vits" else None),
                lexicon=",".join(str(path) for path in bundle.lexicon_paths)
                if bundle.family == "vits"
                else "",
                tokens=path_text(bundle.tokens_path if bundle.family == "vits" else None),
                data_dir=path_text(bundle.data_dir_path if bundle.family == "vits" else None),
                dict_dir=path_text(bundle.dict_dir_path if bundle.family == "vits" else None),
            ),
            matcha=runtime.OfflineTtsMatchaModelConfig(
                acoustic_model=path_text(
                    bundle.acoustic_model_path
                    if bundle.family == "matcha"
                    else None
                ),
                vocoder=path_text(
                    bundle.vocoder_path if bundle.family == "matcha" else None
                ),
                lexicon=",".join(str(path) for path in bundle.lexicon_paths)
                if bundle.family == "matcha"
                else "",
                tokens=path_text(
                    bundle.tokens_path if bundle.family == "matcha" else None
                ),
                data_dir=path_text(
                    bundle.data_dir_path if bundle.family == "matcha" else None
                ),
                dict_dir=path_text(
                    bundle.dict_dir_path if bundle.family == "matcha" else None
                ),
            ),
            kokoro=runtime.OfflineTtsKokoroModelConfig(
                model=path_text(bundle.model_path if bundle.family == "kokoro" else None),
                voices=path_text(bundle.voices_path if bundle.family == "kokoro" else None),
                tokens=path_text(bundle.tokens_path if bundle.family == "kokoro" else None),
                data_dir=path_text(bundle.data_dir_path if bundle.family == "kokoro" else None),
                dict_dir=path_text(bundle.dict_dir_path if bundle.family == "kokoro" else None),
                lexicon=",".join(str(path) for path in bundle.lexicon_paths)
                if bundle.family == "kokoro"
                else "",
            ),
            kitten=runtime.OfflineTtsKittenModelConfig(
                model=path_text(bundle.model_path if bundle.family == "kitten" else None),
                voices=path_text(bundle.voices_path if bundle.family == "kitten" else None),
                tokens=path_text(bundle.tokens_path if bundle.family == "kitten" else None),
                data_dir=path_text(bundle.data_dir_path if bundle.family == "kitten" else None),
            ),
            supertonic=runtime.OfflineTtsSupertonicModelConfig(
                duration_predictor=path_text(
                    bundle.duration_predictor_path
                    if bundle.family == "supertonic"
                    else None
                ),
                text_encoder=path_text(
                    bundle.text_encoder_path
                    if bundle.family == "supertonic"
                    else None
                ),
                vector_estimator=path_text(
                    bundle.vector_estimator_path
                    if bundle.family == "supertonic"
                    else None
                ),
                vocoder=path_text(
                    bundle.vocoder_path
                    if bundle.family == "supertonic"
                    else None
                ),
                tts_json=path_text(
                    bundle.tts_json_path
                    if bundle.family == "supertonic"
                    else None
                ),
                unicode_indexer=path_text(
                    bundle.unicode_indexer_path
                    if bundle.family == "supertonic"
                    else None
                ),
                voice_style=path_text(
                    bundle.voice_style_path
                    if bundle.family == "supertonic"
                    else None
                ),
            ),
            provider=self._provider,
            debug=False,
            num_threads=self._num_threads,
        )
        return runtime.OfflineTtsConfig(
            model=model_config,
            rule_fsts=",".join(str(path) for path in bundle.rule_fst_paths),
            rule_fars=",".join(str(path) for path in bundle.rule_far_paths),
            max_num_sentences=self._max_num_sentences,
        )

    def _prepare_output_paths(
        self,
        request: SynthesisRequest,
    ) -> tuple[Path, Path]:
        if request.output_path is not None:
            audio_path = Path(request.output_path)
        elif request.retention == AudioRetention.RETAIN:
            audio_path = get_retained_audio_path(request.request_id)
        else:
            audio_path = get_request_audio_path(request.request_id)

        audio_path.parent.mkdir(parents=True, exist_ok=True)
        if request.output_path is None:
            return audio_path, audio_path

        with NamedTemporaryFile(
            prefix=f".{audio_path.stem}-",
            suffix=".wav",
            dir=audio_path.parent,
            delete=False,
        ) as temporary_file:
            working_audio_path = Path(temporary_file.name)
        return audio_path, working_audio_path

    @staticmethod
    def _write_wav(
        audio_path: Path,
        audio: Any,
        *,
        expected_sample_rate: int | None = None,
        runtime: Any | None = None,
    ) -> None:
        try:
            sample_rate = int(audio.sample_rate)
            samples = audio.samples
            sample_count = len(samples)
        except (AttributeError, TypeError, ValueError) as exc:
            raise SynthesisFailedError(
                f"Sherpa returned an invalid audio object: {exc}"
            ) from exc

        if sample_rate <= 0 or sample_count == 0:
            raise SynthesisFailedError(
                "Sherpa returned no audio samples or an invalid sample rate."
            )
        if (
            expected_sample_rate is not None
            and sample_rate != expected_sample_rate
        ):
            raise SynthesisFailedError(
                "Sherpa returned an unexpected sample rate: "
                f"{sample_rate} (expected {expected_sample_rate})."
            )

        native_write_wave = getattr(runtime, "write_wave", None)
        if callable(native_write_wave):
            try:
                write_succeeded = native_write_wave(
                    str(audio_path),
                    samples,
                    sample_rate,
                )
            except Exception as exc:
                raise SynthesisFailedError(
                    f"Sherpa failed to write its native WAV output: {exc}"
                ) from exc
            if write_succeeded is False:
                raise SynthesisFailedError(
                    "Sherpa failed to write its native WAV output."
                )
            return

        samples = list(samples)

        pcm = bytearray(len(samples) * 2)
        for index, sample in enumerate(samples):
            try:
                value = float(sample)
            except (TypeError, ValueError):
                value = 0.0
            if not math.isfinite(value):
                value = 0.0
            value = max(-1.0, min(1.0, value))
            struct.pack_into("<h", pcm, index * 2, round(value * 32767))

        with wave.open(str(audio_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm)

    @staticmethod
    def _validate_output_path(audio_path: Path) -> None:
        if not audio_path.exists() or audio_path.stat().st_size <= 44:
            raise SynthesisFailedError(
                f"Sherpa output is empty or invalid: {audio_path}"
            )

    def _cleanup_partial_output(self, audio_path: Path) -> None:
        try:
            audio_path.unlink(missing_ok=True)
        except OSError as exc:
            self._logger.warning(
                "Failed to remove partial Sherpa output %s: %s",
                audio_path,
                exc,
            )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SherpaManifestError(f"Manifest field '{key}' must be a non-empty string.")
    return value.strip()


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SherpaManifestError(f"Manifest field '{key}' must be a string.")
    return value.strip() or None


def _sample_rate(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SherpaManifestError(
            "Manifest field 'sample_rate' must be a positive integer."
        )
    return value


def _resolve_bundle_path(root: Path, value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise SherpaManifestError(f"Manifest field '{field}' must be a path string.")
    relative = Path(value)
    if relative.is_absolute():
        raise SherpaManifestError(f"Manifest field '{field}' must be relative to the bundle.")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SherpaManifestError(
            f"Manifest field '{field}' points outside the bundle directory."
        ) from exc
    return candidate


def _resolve_optional_bundle_path(
    root: Path,
    value: Any,
    *,
    field: str,
) -> Path | None:
    if value is None or value == "":
        return None
    return _resolve_bundle_path(root, value, field=field)


def _resolve_bundle_paths(
    root: Path,
    value: Any,
    *,
    field: str,
) -> tuple[Path, ...]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        raise SherpaManifestError(
            f"Manifest field '{field}' must be a path string or list."
        )
    return tuple(
        _resolve_bundle_path(root, item, field=field)
        for item in values
    )


def _language_codes(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        raise SherpaManifestError(
            "Manifest field 'language_codes' must be a string or list."
        )

    result = tuple(
        item.strip().replace("-", "_")
        for item in values
        if isinstance(item, str) and item.strip()
    )
    return result or ("und",)


def _speakers_from_manifest(
    value: Any,
    speaker_count: Any,
    language_codes: tuple[str, ...],
) -> tuple[SherpaSpeaker, ...]:
    if value is None:
        count = speaker_count if speaker_count is not None else 1
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise SherpaManifestError(
                "speaker_count must be a positive integer when speakers are omitted."
            )
        return tuple(
            SherpaSpeaker(
                speaker_id=index,
                name=f"Speaker {index}",
                language_codes=language_codes,
            )
            for index in range(count)
        )

    if not isinstance(value, list) or not value:
        raise SherpaManifestError("Manifest field 'speakers' must be a non-empty list.")

    speakers: list[SherpaSpeaker] = []
    seen_speakers: set[tuple[int, tuple[str, ...]]] = set()
    for item in value:
        if not isinstance(item, dict):
            raise SherpaManifestError("Each speaker entry must be a JSON object.")
        raw_id = item.get("id", item.get("sid"))
        if isinstance(raw_id, bool) or not isinstance(raw_id, int) or raw_id < 0:
            raise SherpaManifestError("Each speaker id must be a non-negative integer.")
        name = item.get("name", f"Speaker {raw_id}")
        if not isinstance(name, str) or not name.strip():
            raise SherpaManifestError("Each speaker name must be a non-empty string.")
        raw_codes = item.get("language_codes", item.get("language_code", language_codes))
        codes = _language_codes(raw_codes)
        speaker_key = (raw_id, codes)
        if speaker_key in seen_speakers:
            raise SherpaManifestError(
                f"Speaker id {raw_id} is duplicated for language codes {codes}."
            )
        seen_speakers.add(speaker_key)
        speakers.append(
            SherpaSpeaker(
                speaker_id=raw_id,
                name=name.strip(),
                language_codes=codes,
                language_name=(
                    item.get("language_name")
                    if isinstance(item.get("language_name"), str)
                    else None
                ),
                country_name=(
                    item.get("country_name")
                    if isinstance(item.get("country_name"), str)
                    else None
                ),
            )
        )
    return tuple(
        sorted(
            speakers,
            key=lambda speaker: (speaker.speaker_id, speaker.language_codes),
        )
    )


def _language_family(language_code: str) -> str:
    return language_code.replace("-", "_").split("_", 1)[0].lower()


__all__ = [
    "MANIFEST_FILENAME",
    "SHERPA_ONNX_BACKEND_NAME",
    "SHERPA_VOICE_PREFIX",
    "SherpaManifestError",
    "SherpaModelBundle",
    "SherpaOnnxBackend",
    "SherpaSpeaker",
    "SUPPORTED_MODEL_FAMILIES",
]
