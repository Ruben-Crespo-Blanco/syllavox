"""Cleanup support for temporary audio artifacts."""

from __future__ import annotations

import logging
from collections.abc import MutableSet
from pathlib import Path


class AudioArtifactCleaner:
    """Delete temporary audio files and retry files locked by the player."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def cleanup(
        self,
        audio_path: Path,
        pending_paths: MutableSet[Path],
    ) -> None:
        """Delete one path or add it to the pending retry set."""
        try:
            audio_path.unlink(missing_ok=True)
        except OSError as exc:
            pending_paths.add(audio_path)
            self._logger.warning(
                "Could not remove temporary audio file %s; cleanup will be "
                "retried: %s",
                audio_path,
                exc,
            )

    def retry_pending(self, pending_paths: MutableSet[Path]) -> None:
        """Retry every previously locked path."""
        if not pending_paths:
            return

        paths_to_retry = tuple(pending_paths)
        pending_paths.clear()

        for audio_path in paths_to_retry:
            self.cleanup(audio_path, pending_paths)


__all__ = ["AudioArtifactCleaner"]
