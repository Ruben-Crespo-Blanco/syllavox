"""
Application settings management.

Responsible for:
- loading and saving settings
- repairing missing keys using the canonical settings schema
- recovering safely from corrupt JSON files

This module is independent of the GUI.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import ensure_app_directories, get_settings_file_path
from .settings_schema import get_default_settings, merge_with_defaults


def _backup_corrupt_file(path: Path) -> Path:
    """
    Rename a corrupt settings file to a timestamped backup path.

    Returns the backup path.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.stem}.corrupt_{timestamp}{path.suffix}")
    path.replace(backup_path)
    return backup_path


@dataclass
class SettingsLoadResult:
    settings: dict[str, Any]
    created_default_file: bool = False
    repaired_missing_keys: bool = False
    recovered_from_corruption: bool = False
    backup_path: Path | None = None


class SettingsManager:
    """
    Persistent settings manager.

    Features:
    - first-run default file creation
    - load/save support
    - repair of missing keys by merging with defaults
    - safe recovery from corrupt JSON
    """

    def __init__(self, settings_path: Path | None = None) -> None:
        self._settings_path = settings_path or get_settings_file_path()
        self._settings: dict[str, Any] | None = None

    @property
    def settings(self) -> dict[str, Any]:
        if self._settings is None:
            raise RuntimeError("Settings have not been loaded yet.")
        return self._settings

    def load(self) -> SettingsLoadResult:
        """
        Load settings from disk.

        Behavior:
        - creates default settings automatically on first run
        - repairs missing keys by merging with defaults
        - preserves unknown/future-facing keys
        - recovers from corrupt JSON by backing up the bad file and restoring defaults
        """
        ensure_app_directories()
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        defaults = get_default_settings()

        if not self._settings_path.exists():
            self._settings = defaults
            self.save()
            return SettingsLoadResult(
                settings=copy.deepcopy(self._settings),
                created_default_file=True,
            )

        try:
            with self._settings_path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return self._recover_from_corruption(defaults)

        if not isinstance(loaded, dict):
            return self._recover_from_corruption(defaults)

        merged = merge_with_defaults(defaults, loaded)
        repaired_missing_keys = merged != loaded

        self._settings = merged

        # Rewrite repaired settings to disk so the file stays valid and complete.
        if repaired_missing_keys:
            self.save()

        return SettingsLoadResult(
            settings=copy.deepcopy(self._settings),
            repaired_missing_keys=repaired_missing_keys,
        )

    def _recover_from_corruption(
        self,
        defaults: dict[str, Any],
    ) -> SettingsLoadResult:
        """Back up an invalid file and restore the current defaults."""
        backup_path = _backup_corrupt_file(self._settings_path)
        self._settings = defaults
        self.save()
        return SettingsLoadResult(
            settings=copy.deepcopy(self._settings),
            recovered_from_corruption=True,
            backup_path=backup_path,
        )

    def save(self) -> None:
        """
        Save current settings to disk.

        Creates parent directories if needed.
        """
        ensure_app_directories()
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)

        if self._settings is None:
            self._settings = get_default_settings()

        with self._settings_path.open("w", encoding="utf-8") as handle:
            json.dump(self._settings, handle, indent=2, ensure_ascii=False)

    def update(self, new_settings: dict[str, Any]) -> None:
        """
        Replace current settings with the provided structure and save it.
        """
        self._settings = copy.deepcopy(new_settings)
        self.save()
