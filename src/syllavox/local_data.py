"""Complete removal of Syllavox-managed local application data."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .paths import get_app_base_dir


@dataclass(frozen=True)
class LocalDataCleanupReport:
    """Result of deleting the application data directory."""

    app_data_dir: Path
    removed: bool
    removed_bytes: int = 0
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether all Syllavox-managed data was removed."""
        return self.removed and self.error is None


def clear_local_data(app_data_dir: Path | None = None) -> LocalDataCleanupReport:
    """Delete settings, logs, temporary/retained audio, models, and g2pW.

    All runtime data is stored below the application data directory, so
    removing that directory also covers future Syllavox-managed data while
    leaving exported WAV files saved elsewhere untouched.
    """
    target = (app_data_dir or get_app_base_dir()).resolve()

    if not target.exists():
        return LocalDataCleanupReport(app_data_dir=target, removed=True)

    try:
        removed_bytes = _directory_size(target)
        shutil.rmtree(target)
    except OSError as exc:
        return LocalDataCleanupReport(
            app_data_dir=target,
            removed=False,
            removed_bytes=0,
            error=str(exc),
        )

    return LocalDataCleanupReport(
        app_data_dir=target,
        removed=True,
        removed_bytes=removed_bytes,
    )


def _directory_size(path: Path) -> int:
    """Return the size of regular files below ``path`` without following links."""
    total = 0
    for child in path.rglob("*"):
        if child.is_file() and not child.is_symlink():
            try:
                total += child.stat().st_size
            except OSError:
                continue
    return total


__all__ = ["LocalDataCleanupReport", "clear_local_data"]
