"""Local Piper model storage, installation, and cleanup operations."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from syllavox.tts.catalog_models import SherpaCatalogEntry, VoiceCatalogEntry
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
        self._recover_install_transactions()

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
        """Download and transactionally install a Piper model/config pair."""
        self._validate_voice_id(entry.voice_id)
        self._models_dir.mkdir(parents=True, exist_ok=True)
        transaction_dir: Path | None = None

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

                destinations = self._voice_paths(entry.voice_id)
                transaction_dir = self._begin_install_transaction(
                    entry.voice_id,
                    destinations,
                )
                self._replace_installed_file(model_temp_path, destinations[0])
                self._replace_installed_file(config_temp_path, destinations[1])
                self._write_transaction_manifest(
                    transaction_dir,
                    entry.voice_id,
                    destinations,
                    phase="committed",
                )
                committed_transaction_dir = transaction_dir
                transaction_dir = None
                try:
                    self._remove_transaction_dir(committed_transaction_dir)
                except OSError:
                    # A committed journal is harmless and will be cleaned on
                    # the next storage initialization.
                    pass

        except Exception as exc:
            if transaction_dir is not None:
                try:
                    self._recover_transaction(transaction_dir)
                except Exception as rollback_exc:
                    raise VoiceCatalogError(
                        f"Could not install Piper voice {entry.voice_id}; "
                        f"rollback also failed: {rollback_exc}"
                    ) from exc
            if isinstance(exc, VoiceCatalogError):
                raise

            raise VoiceCatalogError(
                f"Could not install Piper voice {entry.voice_id}: {exc}"
            ) from exc

        return replace(entry, installed=True)

    def _begin_install_transaction(
        self,
        voice_id: str,
        destinations: tuple[Path, Path],
    ) -> Path:
        transaction_dir = self._transaction_dir(voice_id)
        if transaction_dir.exists():
            self._recover_transaction(transaction_dir)
        transaction_dir.mkdir(parents=True)

        for destination, backup_name in zip(
            destinations,
            ("model.backup", "config.backup"),
        ):
            if destination.is_file():
                shutil.copy2(destination, transaction_dir / backup_name)

        self._write_transaction_manifest(
            transaction_dir,
            voice_id,
            destinations,
            phase="prepared",
        )
        return transaction_dir

    def _write_transaction_manifest(
        self,
        transaction_dir: Path,
        voice_id: str,
        destinations: tuple[Path, Path],
        *,
        phase: str,
    ) -> None:
        manifest_path = transaction_dir / "transaction.json"
        temporary_path = transaction_dir / ".transaction.json.tmp"
        payload = {
            "version": 1,
            "voice_id": voice_id,
            "phase": phase,
            "model_existed": (transaction_dir / "model.backup").is_file(),
            "config_existed": (transaction_dir / "config.backup").is_file(),
            "model_name": destinations[0].name,
            "config_name": destinations[1].name,
        }
        try:
            with temporary_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, manifest_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _recover_install_transactions(self) -> None:
        transaction_root = self._transaction_root()
        if not transaction_root.is_dir():
            return

        try:
            for transaction_dir in transaction_root.iterdir():
                if transaction_dir.is_dir():
                    self._recover_transaction(transaction_dir)
            transaction_root.rmdir()
        except OSError as exc:
            raise VoiceCatalogError(
                f"Could not recover an interrupted Piper voice install: {exc}"
            ) from exc

    def _recover_transaction(self, transaction_dir: Path) -> None:
        manifest_path = transaction_dir / "transaction.json"
        if not manifest_path.is_file():
            self._remove_transaction_dir(transaction_dir)
            return

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("phase") == "committed":
                self._remove_transaction_dir(transaction_dir)
                return

            voice_id = str(manifest["voice_id"])
            self._validate_voice_id(voice_id)
            destinations = self._voice_paths(voice_id)
            expected_names = (
                manifest.get("model_name"),
                manifest.get("config_name"),
            )
            if expected_names != tuple(path.name for path in destinations):
                raise VoiceCatalogError(
                    "The interrupted Piper install manifest is invalid."
                )

            for destination, backup_name, existed_key in zip(
                destinations,
                ("model.backup", "config.backup"),
                ("model_existed", "config_existed"),
            ):
                backup_path = transaction_dir / backup_name
                if bool(manifest.get(existed_key)):
                    if not backup_path.is_file():
                        raise VoiceCatalogError(
                            "The interrupted Piper install backup is incomplete."
                        )
                    restore_path = destination.with_name(
                        f".{destination.name}.restore"
                    )
                    try:
                        shutil.copy2(backup_path, restore_path)
                        os.replace(restore_path, destination)
                    finally:
                        restore_path.unlink(missing_ok=True)
                else:
                    destination.unlink(missing_ok=True)

            self._remove_transaction_dir(transaction_dir)
        except (
            OSError,
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise VoiceCatalogError(
                f"Could not recover Piper install transaction: {exc}"
            ) from exc

    def _transaction_root(self) -> Path:
        return self._models_dir / ".install-transactions"

    def _transaction_dir(self, voice_id: str) -> Path:
        digest = hashlib.sha256(voice_id.encode("utf-8")).hexdigest()
        return self._transaction_root() / digest

    @staticmethod
    def _remove_transaction_dir(transaction_dir: Path) -> None:
        try:
            shutil.rmtree(transaction_dir)
        except FileNotFoundError:
            return

    @staticmethod
    def _replace_installed_file(source: Path, destination: Path) -> None:
        os.replace(source, destination)

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
            or "/" in voice_id
            or "\\" in voice_id
            or Path(voice_id).name != voice_id
            or voice_id in {".", ".."}
        ):
            raise VoiceCatalogError("The selected Piper voice ID is invalid.")


class SherpaVoiceStorage:
    """Download, validate, install, and delete Sherpa model bundles."""

    def __init__(
        self,
        models_dir: Path,
        urlopen_fn: UrlOpen,
        timeout_seconds: float,
    ) -> None:
        self._models_dir = Path(models_dir)
        self._urlopen = urlopen_fn
        self._timeout_seconds = timeout_seconds

    @property
    def models_dir(self) -> Path:
        return self._models_dir

    def is_bundle_installed(self, bundle_id: str) -> bool:
        root = self._bundle_root(bundle_id)
        return root.is_dir() and (root / "bundle.json").is_file()

    def installed_bundle_ids(self) -> list[str]:
        if not self._models_dir.is_dir():
            return []

        return sorted(
            path.name
            for path in self._models_dir.iterdir()
            if path.is_dir() and (path / "bundle.json").is_file()
        )

    def install_bundle(self, entry: SherpaCatalogEntry) -> SherpaCatalogEntry:
        """Install an archive and any external resources atomically."""
        self._validate_bundle_id(entry.bundle_id)
        self._models_dir.mkdir(parents=True, exist_ok=True)
        install_root = self._bundle_root(entry.bundle_id)
        if install_root.exists():
            raise VoiceCatalogError(
                f"Sherpa bundle {entry.bundle_id} is already installed."
            )

        try:
            with tempfile.TemporaryDirectory(
                prefix=f".{entry.bundle_id}.",
                dir=self._models_dir,
            ) as temporary_dir:
                temporary_root = Path(temporary_dir)
                archive_path = temporary_root / "model.tar.bz2"
                extracted_root = temporary_root / "extracted"
                extracted_root.mkdir()

                self._download_file(
                    entry.archive_url,
                    archive_path,
                    expected_sha256=entry.archive_sha256,
                )
                self._safe_extract(archive_path, extracted_root)
                bundle_root = self._find_bundle_root(
                    extracted_root,
                    entry.bundle_id,
                )

                for resource_key, resource_url in entry.resource_urls:
                    resource_path = self._resource_path(entry, resource_key)
                    self._download_file(
                        resource_url,
                        bundle_root / resource_path,
                    )

                self._validate_entry_files(bundle_root, entry)
                manifest_path = bundle_root / "bundle.json"
                manifest_path.write_text(
                    json.dumps(
                        self._manifest_payload(entry),
                        indent=2,
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                shutil.move(str(bundle_root), str(install_root))
        except Exception as exc:
            if isinstance(exc, VoiceCatalogError):
                raise

            raise VoiceCatalogError(
                f"Could not install Sherpa bundle {entry.bundle_id}: {exc}"
            ) from exc

        return replace(entry, installed=True)

    def delete_voice_files(self, voice_id: str) -> int:
        """Delete the complete bundle associated with a backend voice ID."""
        bundle_id = self.bundle_id_from_voice_id(voice_id)
        bundle_root = self._bundle_root(bundle_id)
        removed_size = self._directory_size(bundle_root)

        if not bundle_root.exists():
            return 0

        try:
            shutil.rmtree(bundle_root)
        except OSError as exc:
            raise VoiceCatalogError(
                f"Could not delete Sherpa bundle {bundle_id}: {exc}"
            ) from exc

        return removed_size

    @staticmethod
    def bundle_id_from_voice_id(voice_id: str) -> str:
        prefix = "sherpa-onnx:"
        marker = "#sid="
        if not isinstance(voice_id, str) or not voice_id.startswith(prefix):
            raise VoiceCatalogError("The selected Sherpa voice ID is invalid.")

        bundle_id = voice_id[len(prefix):].split(marker, 1)[0]
        SherpaVoiceStorage._validate_bundle_id(bundle_id)
        return bundle_id

    def _bundle_root(self, bundle_id: str) -> Path:
        self._validate_bundle_id(bundle_id)
        return self._models_dir / bundle_id

    def _download_file(
        self,
        url: str,
        destination: Path,
        *,
        expected_sha256: str | None = None,
    ) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_destination = destination.with_name(
            f".{destination.name}.partial"
        )
        try:
            with self._urlopen(url, timeout=self._timeout_seconds) as response:
                with temporary_destination.open("wb") as output_file:
                    shutil.copyfileobj(response, output_file)
            if temporary_destination.stat().st_size == 0:
                raise VoiceCatalogError(f"Downloaded file is empty: {url}")
            if expected_sha256 is not None:
                if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
                    raise VoiceCatalogError(
                        f"The catalog checksum for {url} is invalid."
                    )
                actual_sha256 = _sha256_file(temporary_destination)
                if actual_sha256.lower() != expected_sha256.lower():
                    raise VoiceCatalogError(
                        f"Checksum mismatch for {url}: expected "
                        f"{expected_sha256}, got {actual_sha256}."
                    )
            temporary_destination.replace(destination)
        except Exception as exc:
            temporary_destination.unlink(missing_ok=True)
            if isinstance(exc, VoiceCatalogError):
                raise
            raise VoiceCatalogError(f"Download failed for {url}: {exc}") from exc

    @staticmethod
    def _safe_extract(archive_path: Path, destination: Path) -> None:
        destination_root = destination.resolve()
        try:
            with tarfile.open(archive_path, mode="r:*") as archive:
                for member in archive.getmembers():
                    member_path = Path(member.name)
                    if (
                        member_path.is_absolute()
                        or bool(member_path.drive)
                        or ".." in member_path.parts
                        or member.issym()
                        or member.islnk()
                    ):
                        raise VoiceCatalogError(
                            "The Sherpa archive contains an unsafe path or link."
                        )

                    target = (destination / member_path).resolve()
                    try:
                        target.relative_to(destination_root)
                    except ValueError as exc:
                        raise VoiceCatalogError(
                            "The Sherpa archive contains a path outside its extraction directory."
                        ) from exc

                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    if not member.isfile():
                        raise VoiceCatalogError(
                            "The Sherpa archive contains an unsupported entry."
                        )

                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is None:
                        raise VoiceCatalogError(
                            f"Could not read archive member {member.name}."
                        )
                    with source, target.open("wb") as output_file:
                        shutil.copyfileobj(source, output_file)
        except tarfile.TarError as exc:
            raise VoiceCatalogError(f"The Sherpa archive is invalid: {exc}") from exc

    @staticmethod
    def _find_bundle_root(extracted_root: Path, bundle_id: str) -> Path:
        expected_root = extracted_root / bundle_id
        if expected_root.is_dir():
            return expected_root

        children = list(extracted_root.iterdir())
        if len(children) == 1 and children[0].is_dir():
            return children[0]
        return extracted_root

    @staticmethod
    def _resource_path(entry: SherpaCatalogEntry, resource_key: str) -> str:
        if resource_key == "vocoder" and entry.vocoder_path:
            return entry.vocoder_path
        raise VoiceCatalogError(
            f"Sherpa catalog entry {entry.bundle_id} has an unknown resource '{resource_key}'."
        )

    @staticmethod
    def _validate_entry_files(
        bundle_root: Path,
        entry: SherpaCatalogEntry,
    ) -> None:
        paths = [
            entry.model_path,
            entry.tokens_path,
            entry.voices_path,
            entry.data_dir_path,
            entry.dict_dir_path,
            *entry.lexicon_paths,
            *entry.rule_fst_paths,
            *entry.rule_far_paths,
            entry.acoustic_model_path,
            entry.vocoder_path,
            entry.duration_predictor_path,
            entry.text_encoder_path,
            entry.vector_estimator_path,
            entry.tts_json_path,
            entry.unicode_indexer_path,
            entry.voice_style_path,
        ]
        missing = [
            path
            for path in paths
            if path and not (bundle_root / path).exists()
        ]
        if missing:
            raise VoiceCatalogError(
                f"Sherpa archive {entry.bundle_id} is missing: "
                + ", ".join(missing)
            )

    @staticmethod
    def _manifest_payload(entry: SherpaCatalogEntry) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "bundle_id": entry.bundle_id,
            "display_name": entry.name,
            "family": entry.family,
            "language_codes": list(entry.language_codes),
            "language_name": entry.language_name,
            "country_name": entry.country_name,
            "quality": entry.quality,
            "sample_rate": entry.sample_rate,
            "source_url": entry.source_url,
            "license": entry.license_name,
            "license_url": entry.license_url,
        }
        if entry.archive_sha256:
            payload["archive_sha256"] = entry.archive_sha256

        field_map = {
            "model": entry.model_path,
            "tokens": entry.tokens_path,
            "voices": entry.voices_path,
            "data_dir": entry.data_dir_path,
            "dict_dir": entry.dict_dir_path,
            "acoustic_model": entry.acoustic_model_path,
            "vocoder": entry.vocoder_path,
            "duration_predictor": entry.duration_predictor_path,
            "text_encoder": entry.text_encoder_path,
            "vector_estimator": entry.vector_estimator_path,
            "tts_json": entry.tts_json_path,
            "unicode_indexer": entry.unicode_indexer_path,
            "voice_style": entry.voice_style_path,
        }
        payload.update(
            {
                key: value
                for key, value in field_map.items()
                if value is not None
            }
        )
        if entry.lexicon_paths:
            payload["lexicon"] = list(entry.lexicon_paths)
        if entry.rule_fst_paths:
            payload["rule_fsts"] = list(entry.rule_fst_paths)
        if entry.rule_far_paths:
            payload["rule_fars"] = list(entry.rule_far_paths)
        if entry.speakers:
            payload["speakers"] = [
                {
                    "id": speaker.speaker_id,
                    "name": speaker.name,
                    "language_codes": list(speaker.language_codes),
                }
                for speaker in entry.speakers
            ]
        elif entry.num_speakers is not None:
            payload["speaker_count"] = entry.num_speakers
        return payload

    @staticmethod
    def _directory_size(directory: Path) -> int:
        if not directory.exists():
            return 0
        total = 0
        for path in directory.rglob("*"):
            if path.is_file():
                try:
                    total += path.stat().st_size
                except OSError:
                    continue
        return total

    @staticmethod
    def _validate_bundle_id(bundle_id: str) -> None:
        if (
            not bundle_id
            or Path(bundle_id).name != bundle_id
            or bundle_id in {".", ".."}
            or any(character in bundle_id for character in ('/', '\\', ':'))
        ):
            raise VoiceCatalogError("The selected Sherpa bundle ID is invalid.")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["PiperVoiceStorage", "SherpaVoiceStorage"]
