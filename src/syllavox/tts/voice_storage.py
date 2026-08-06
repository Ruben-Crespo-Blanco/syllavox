"""Local Piper model storage, installation, and cleanup operations."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from syllavox.tts.catalog_models import VoiceCatalogEntry
from syllavox.tts.errors import VoiceCatalogError

UrlOpen = Callable[..., Any]


class PiperVoiceStorage:
    """Manage Piper model files and their shared language resources."""

    def __init__(
        self,
        models_dir: Path,
        urlopen_fn: UrlOpen,
        timeout_seconds: float,
    ) -> None:
        self._models_dir = models_dir
        self._urlopen = urlopen_fn
        self._timeout_seconds = timeout_seconds

    @property
    def models_dir(self) -> Path:
        return self._models_dir

    def is_voice_installed(self, voice_id: str) -> bool:
        """Return whether both model files required by Piper are present."""
        model_path, config_path = self._voice_paths(voice_id)
        return model_path.is_file() and config_path.is_file()

    def installed_voice_ids(self) -> list[str]:
        """Return voice IDs represented by local Piper model files."""
        return sorted(path.stem for path in self._models_dir.glob("*.onnx"))

    def voice_model_size(self, voice_id: str) -> int:
        """Return the combined size of a voice model and its config."""
        return self._paths_size(self._voice_paths(voice_id))

    def delete_voice_files(self, voice_id: str) -> int:
        """Delete a voice's model pair and return the bytes removed."""
        paths = self._voice_paths(voice_id)
        removed_size = self._paths_size(paths)

        try:
            for path in paths:
                path.unlink(missing_ok=True)
        except OSError as exc:
            raise VoiceCatalogError(
                f"Could not delete Piper voice {voice_id}: {exc}"
            ) from exc

        return removed_size

    def voice_uses_pinyin(self, voice_id: str) -> bool:
        """Return whether a local voice requires Piper's Chinese phonemizer."""
        config_path = self._voice_paths(voice_id)[1]

        try:
            with config_path.open("r", encoding="utf-8") as config_file:
                config = json.load(config_file)
        except (OSError, json.JSONDecodeError):
            return False

        return isinstance(config, dict) and config.get("phoneme_type") == "pinyin"

    def has_installed_pinyin_voice(
        self,
        excluding_voice_id: str | None = None,
    ) -> bool:
        """Return whether any installed voice still requires g2pW."""
        return any(
            voice_id != excluding_voice_id
            and self.is_voice_installed(voice_id)
            and self.voice_uses_pinyin(voice_id)
            for voice_id in self.installed_voice_ids()
        )

    def g2pw_size(self) -> int:
        """Return the size of the shared Chinese phonemization resource."""
        resource_dir = self._models_dir / "g2pW"
        if not resource_dir.exists():
            return 0

        return sum(
            path.stat().st_size
            for path in resource_dir.rglob("*")
            if path.is_file()
        )

    def delete_unused_g2pw(self) -> int:
        """Delete g2pW only when no installed voice still requires it."""
        if self.has_installed_pinyin_voice():
            raise VoiceCatalogError(
                "The Chinese phonemization resource is still required by an "
                "installed voice."
            )

        resource_dir = self._models_dir / "g2pW"
        removed_size = self.g2pw_size()

        if not resource_dir.exists():
            return 0

        try:
            shutil.rmtree(resource_dir)
        except OSError as exc:
            raise VoiceCatalogError(
                f"Could not delete unused Chinese phonemization data: {exc}"
            ) from exc

        return removed_size

    def install_voice(self, entry: VoiceCatalogEntry) -> VoiceCatalogEntry:
        """Download one selected voice atomically into the model directory."""
        self._validate_voice_id(entry.voice_id)
        self._models_dir.mkdir(parents=True, exist_ok=True)

        try:
            with tempfile.TemporaryDirectory(
                prefix=f".{entry.voice_id}.",
                dir=self._models_dir,
            ) as temporary_dir:
                temporary_path = Path(temporary_dir)
                model_temp_path = temporary_path / f"{entry.voice_id}.onnx"
                config_temp_path = temporary_path / f"{entry.voice_id}.onnx.json"

                self._download_file(entry.model_url, model_temp_path)
                self._download_file(entry.config_url, config_temp_path)

                model_temp_path.replace(self._models_dir / model_temp_path.name)
                config_temp_path.replace(self._models_dir / config_temp_path.name)

        except Exception as exc:
            if isinstance(exc, VoiceCatalogError):
                raise

            raise VoiceCatalogError(
                f"Could not install Piper voice {entry.voice_id}: {exc}"
            ) from exc

        return replace(entry, installed=True)

    def _download_file(self, url: str, destination: Path) -> None:
        try:
            with self._urlopen(url, timeout=self._timeout_seconds) as response:
                with destination.open("wb") as output_file:
                    shutil.copyfileobj(response, output_file)
        except Exception as exc:
            raise VoiceCatalogError(f"Download failed for {url}: {exc}") from exc

    def _voice_paths(self, voice_id: str) -> tuple[Path, Path]:
        self._validate_voice_id(voice_id)
        model_path = self._models_dir / f"{voice_id}.onnx"
        return model_path, Path(f"{model_path}.json")

    @staticmethod
    def _paths_size(paths: tuple[Path, Path]) -> int:
        total_size = 0
        for path in paths:
            try:
                total_size += path.stat().st_size
            except FileNotFoundError:
                continue

        return total_size

    @staticmethod
    def _validate_voice_id(voice_id: str) -> None:
        if (
            not voice_id
            or Path(voice_id).name != voice_id
            or voice_id in {".", ".."}
        ):
            raise VoiceCatalogError("The selected Piper voice ID is invalid.")


__all__ = ["PiperVoiceStorage"]
