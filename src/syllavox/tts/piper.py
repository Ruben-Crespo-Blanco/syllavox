"""
Piper backend adapter.

Implements the TTSBackend interface using the Piper Python API.

Responsibilities:
- discover local Piper voice models
- report backend health
- load Piper voices lazily
- synthesize text into local WAV files

No subprocess or executable wrapping is used here.
"""

from __future__ import annotations

import builtins
import importlib
import json
import wave
from contextlib import contextmanager, nullcontext
from pathlib import Path
from tempfile import NamedTemporaryFile
from collections.abc import Iterator
from typing import Any

from syllavox.tts.base import (
    AudioRetention,
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    TTSBackend,
    VoiceMemoryBackend,
    VoiceInfo,
)
from syllavox.tts.errors import (
    LanguageCompatibilityError,
    SynthesisFailedError,
    VoiceNotFoundError,
)
from syllavox.logging_config import get_logger
from syllavox.tts.paths import (
    get_piper_models_dir,
    get_request_audio_path,
    get_retained_audio_path,
)


_MISSING = object()


def _is_relative_to(path: Path, root: Path) -> bool:
    """Return whether ``path`` is inside ``root`` without raising."""
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


@contextmanager
def _utf8_for_g2pw_text_files(models_dir: Path) -> Iterator[None]:
    """Apply the app's scoped compatibility settings for g2pW.

    The g2pW package bundled by ``piper-tts[zh]`` calls ``open`` without an
    encoding for its Chinese character tables and JSON resources. On Windows
    that uses the system code page instead of UTF-8, which fails as soon as a
    Chinese resource contains a byte outside that code page. It also defaults
    to two PyTorch data-loader workers, which causes a frozen Windows app to
    spawn copies of itself. Patch only the affected g2pW modules and converter
    during synthesis, then restore them immediately afterward.
    """
    module_names = ("g2pw.api", "g2pw.dataset", "g2pw.module")
    modules: list[Any] = []

    for module_name in module_names:
        try:
            modules.append(importlib.import_module(module_name))
        except ImportError:
            continue

    roots = [models_dir / "g2pW"]
    roots.extend(
        Path(module.__file__).parent
        for module in modules
        if getattr(module, "__file__", None)
    )

    original_open = builtins.open

    def open_utf8(
        file: Any,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
        closefd: bool = True,
        opener: Any = None,
    ) -> Any:
        if (
            encoding is None
            and "b" not in mode
            and isinstance(file, (str, bytes, Path))
        ):
            file_path = Path(file)
            if any(_is_relative_to(file_path, root) for root in roots):
                encoding = "utf-8"

        return original_open(
            file,
            mode,
            buffering,
            encoding,
            errors,
            newline,
            closefd,
            opener,
        )

    previous_open: list[tuple[Any, Any]] = []
    for module in modules:
        previous = module.__dict__.get("open", _MISSING)
        previous_open.append((module, previous))
        module.open = open_utf8

    converter_class = next(
        (
            getattr(module, "G2PWConverter", None)
            for module in modules
            if getattr(module, "G2PWConverter", None) is not None
        ),
        None,
    )
    original_converter_init = (
        converter_class.__init__ if converter_class is not None else None
    )

    if converter_class is not None and original_converter_init is not None:
        def init_single_process(
            converter: Any,
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            # g2pw uses ``num_workers if num_workers else config.num_workers``
            # internally, so passing 0 to its constructor does not actually
            # disable worker processes. Set the constructed converter's value
            # after the original initializer has populated it.
            result = original_converter_init(converter, *args, **kwargs)
            converter.num_workers = 0
            return result

        converter_class.__init__ = init_single_process

    try:
        yield
    finally:
        if converter_class is not None and original_converter_init is not None:
            converter_class.__init__ = original_converter_init

        for module, previous in previous_open:
            if previous is _MISSING:
                module.__dict__.pop("open", None)
            else:
                module.open = previous


def _uses_pinyin_phonemizer(voice: Any) -> bool:
    """Return whether a loaded Piper voice uses the Chinese phonemizer."""
    phoneme_type = getattr(getattr(voice, "config", None), "phoneme_type", None)
    return getattr(phoneme_type, "value", phoneme_type) == "pinyin"


def _looks_like_language_compatibility_error(error: BaseException) -> bool:
    """Recognize Piper errors caused by an unsupported language phonemizer."""
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "not a valid phoneme type",
            "unexpected phoneme type",
            "unsupported phoneme type",
        )
    )


class PiperBackend(TTSBackend, VoiceMemoryBackend):
    """
    Piper TTS backend using the Python API.

    Models are expected in:

        %LOCALAPPDATA%/Syllavox/models/piper/

    Example voice pair:

        en_US-lessac-medium.onnx
        en_US-lessac-medium.onnx.json
    """

    def __init__(
        self,
        models_dir: Path | None = None,
    ) -> None:
        self._models_dir = models_dir or get_piper_models_dir()
        self._loaded_voices: dict[str, Any] = {}
        self._logger = get_logger(__name__)

    def backend_name(self) -> str:
        return "piper"

    def health(self) -> BackendHealth:
        """
        Return backend health information.

        Healthy when:
        - Piper Python API is importable
        - model directory exists
        - at least one valid model/config pair exists

        This method must never raise.
        """
        try:
            self._import_piper_voice()
        except Exception as exc:
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details=f"Piper Python API unavailable: {exc}",
            )

        if not self._models_dir.exists():
            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details="Piper models directory does not exist.",
            )

        model_paths, invalid_count = self._discover_model_paths()
        valid_count = len(model_paths)

        if valid_count == 0:
            if invalid_count > 0:
                return BackendHealth(
                    name=self.backend_name(),
                    healthy=False,
                    details=(
                        "Invalid Piper voice files detected "
                        f"({invalid_count} missing config pair(s))."
                    ),
                )

            return BackendHealth(
                name=self.backend_name(),
                healthy=False,
                details="No Piper voices found.",
            )

        loaded_count = self.loaded_voice_count()

        details = (
            f"{valid_count} voice(s) available. "
            f"{loaded_count} loaded."
        )

        compatibility_count = sum(
            self.voice_compatibility_issue(model_path.stem) is not None
            for model_path in model_paths
        )
        if compatibility_count:
            details += (
                f" {compatibility_count} voice(s) require language "
                "compatibility attention."
            )

        if invalid_count > 0:
            details += (
                f" {invalid_count} invalid pair(s) ignored."
            )

        return BackendHealth(
            name=self.backend_name(),
            healthy=True,
            details=details,
        )

    def list_voices(self) -> list[VoiceInfo]:
        """
        Discover available Piper voices.

        A valid voice requires:
        - *.onnx
        - matching *.onnx.json
        """
        voices: list[VoiceInfo] = []

        model_paths, _ = self._discover_model_paths()

        for model_path in model_paths:
            voice = self._voice_from_model_path(model_path)

            if voice is not None:
                voices.append(voice)

        return voices
    
    def synthesize(
        self,
        request: SynthesisRequest,
    ) -> SynthesisResult:
        """
        Synthesize text into a WAV file using Piper's Python API.
        """
        voice_id = request.voice_id
        if voice_id is None:
            raise SynthesisFailedError(
                "Piper synthesis requires a resolved voice ID."
            )

        working_audio_path: Path | None = None

        try:
            audio_path, working_audio_path = self._prepare_output_paths(request)
            voice = self.load_voice(voice_id)
            self._synthesize_to_path(
                voice,
                request.text,
                working_audio_path,
            )
            self._validate_output_path(working_audio_path)

            if request.output_path is not None:
                working_audio_path.replace(audio_path)

            return SynthesisResult(
                request_id=request.request_id,
                voice_id=voice_id,
                audio_path=audio_path,
                mime_type="audio/wav",
                retention=request.retention,
            )

        except Exception as exc:
            if working_audio_path is not None:
                self._cleanup_partial_output(working_audio_path)

            if isinstance(exc, (VoiceNotFoundError, SynthesisFailedError)):
                raise

            raise SynthesisFailedError(
                f"Piper synthesis failed: {exc}"
            ) from exc

    def _prepare_output_paths(
        self,
        request: SynthesisRequest,
    ) -> tuple[Path, Path]:
        """Create the final and working paths for one synthesis request."""
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

    def _synthesize_to_path(
        self,
        voice: Any,
        text: str,
        audio_path: Path,
    ) -> None:
        """Write Piper output to a working WAV path."""
        utf8_context = (
            _utf8_for_g2pw_text_files(self._models_dir)
            if _uses_pinyin_phonemizer(voice)
            else nullcontext()
        )

        with utf8_context:
            wav_file = wave.open(str(audio_path), "wb")
            try:
                voice.synthesize_wav(text, wav_file)
            except Exception:
                try:
                    wav_file.close()
                except (OSError, wave.Error):
                    self._logger.debug(
                        "Ignoring incomplete WAV close after Piper failure",
                        exc_info=True,
                    )
                raise
            else:
                wav_file.close()

    @staticmethod
    def _validate_output_path(audio_path: Path) -> None:
        """Ensure synthesis produced a non-empty WAV container."""
        if not audio_path.exists():
            raise SynthesisFailedError(
                "Piper synthesis completed but output file was not created: "
                f"{audio_path}"
            )

        if audio_path.stat().st_size <= 44:
            raise SynthesisFailedError(
                f"Piper output file is empty or invalid: {audio_path}"
            )

    def _cleanup_partial_output(self, audio_path: Path) -> None:
        """Remove a partial synthesis file without masking the original error."""
        try:
            audio_path.unlink(missing_ok=True)
        except OSError as exc:
            self._logger.warning(
                "Failed to remove partial Piper output %s: %s",
                audio_path,
                exc,
            )

    def load_voice(
        self,
        voice_id: str,
    ) -> Any:
        """
        Load and cache a Piper voice.

        If the voice is already loaded, return the cached instance.
        """
        if voice_id in self._loaded_voices:
            return self._loaded_voices[voice_id]

        model_path = self._get_model_path(voice_id)
        config_path = self._get_config_path(model_path)

        if not model_path.exists():
            raise VoiceNotFoundError(voice_id)

        if not config_path.exists():
            raise SynthesisFailedError(
                f"Piper config file not found for voice: {voice_id}"
            )

        compatibility_issue = self.voice_compatibility_issue(voice_id)
        if compatibility_issue:
            raise LanguageCompatibilityError(compatibility_issue)

        PiperVoice = self._import_piper_voice()

        try:
            voice = PiperVoice.load(
                str(model_path),
                download_dir=str(self._models_dir),
            )

            if _uses_pinyin_phonemizer(voice):
                with _utf8_for_g2pw_text_files(self._models_dir):
                    # Creating the phonemizer here moves the expensive g2pW
                    # initialization into the explicit Load action.
                    voice.phonemize("")
        except LanguageCompatibilityError:
            raise
        except Exception as exc:
            if _looks_like_language_compatibility_error(exc):
                phoneme_type = self._read_phoneme_type(config_path)
                raise LanguageCompatibilityError(
                    "Piper could not load voice "
                    f"{voice_id} with phonemizer {phoneme_type or 'unknown'}; "
                    "the language configuration is incompatible with the "
                    f"installed Piper runtime. Original error: {exc}"
                ) from exc

            raise SynthesisFailedError(
                f"Failed to load Piper voice {voice_id}: {exc}"
            ) from exc

        self._loaded_voices[voice_id] = voice
        return voice


    def unload_voice(
        self,
        voice_id: str,
    ) -> None:
        """
        Remove a loaded voice from the in-memory cache.

        This does not delete model files from disk.
        """
        self._loaded_voices.pop(voice_id, None)

    def is_voice_loaded(
        self,
        voice_id: str,
    ) -> bool:
        """
        Return True if the voice is currently loaded in memory.
        """
        return voice_id in self._loaded_voices

    def loaded_voice_ids(self) -> list[str]:
        """
        Return voice IDs currently loaded in memory.
        """
        return sorted(self._loaded_voices.keys())

    def loaded_voice_count(self) -> int:
        """
        Return number of voices currently loaded in memory.
        """
        return len(self._loaded_voices)

    def shutdown(self) -> None:
        """Release all cached Piper voice objects at application exit."""
        self._loaded_voices.clear()


    def voice_compatibility_issue(self, voice_id: str) -> str | None:
        """Return a preflight language-compatibility issue, if one is known."""
        config_path = self._get_config_path(self._get_model_path(voice_id))

        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None

        if not isinstance(config, dict):
            return None

        phoneme_type = config.get("phoneme_type")
        if not isinstance(phoneme_type, str):
            return None

        supported_types = self._supported_phoneme_types()
        if supported_types and phoneme_type not in supported_types:
            supported_text = ", ".join(sorted(supported_types))
            return (
                f"Piper runtime does not support phonemizer '{phoneme_type}' "
                f"for voice {voice_id}. Supported phonemizers: {supported_text}."
            )

        return None

    @staticmethod
    def _supported_phoneme_types() -> set[str]:
        """Read supported phonemizers from the installed Piper runtime."""
        try:
            from piper.config import PhonemeType
        except ImportError:
            return set()

        return {
            member.value
            for member in PhonemeType
            if isinstance(getattr(member, "value", None), str)
        }

    @staticmethod
    def _read_phoneme_type(config_path: Path) -> str | None:
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None

        value = config.get("phoneme_type") if isinstance(config, dict) else None
        return value if isinstance(value, str) else None

    def _import_piper_voice(self) -> Any:
        """
        Import PiperVoice lazily so backend health can report failures cleanly.
        """
        try:
            from piper import PiperVoice
        except ImportError:
            from piper.voice import PiperVoice

        return PiperVoice

    def _discover_model_paths(self) -> tuple[list[Path], int]:
        """Return valid Piper model paths and the number of invalid pairs."""
        if not self._models_dir.exists():
            return [], 0

        valid_paths: list[Path] = []
        invalid_count = 0

        for model_path in sorted(self._models_dir.glob("*.onnx")):
            if self._get_config_path(model_path).exists():
                valid_paths.append(model_path)
            else:
                invalid_count += 1

        return valid_paths, invalid_count

    def _get_model_path(
        self,
        voice_id: str,
    ) -> Path:
        return self._models_dir / f"{voice_id}.onnx"

    def _get_config_path(
        self,
        model_path: Path,
    ) -> Path:
        return Path(f"{model_path}.json")

    def _voice_from_model_path(
        self,
        model_path: Path,
    ) -> VoiceInfo | None:
        """
        Convert a Piper model filename into backend-neutral VoiceInfo.

        Example:
            en_US-lessac-medium.onnx

        becomes:
            voice_id="en_US-lessac-medium"
            name="en_US lessac medium"
            language="en"
        """
        stem = model_path.stem

        if not stem:
            return None

        language = stem.split("_")[0]
        readable_name = stem.replace("-", " ")

        return VoiceInfo(
            voice_id=stem,
            name=readable_name,
            language=language,
            language_code=stem.split("-", 1)[0],
            quality=stem.rsplit("-", 1)[-1] if "-" in stem else None,
        )
