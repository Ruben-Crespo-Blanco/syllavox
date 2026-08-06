from __future__ import annotations

import logging
from pathlib import Path

from syllavox.audio.artifacts import AudioArtifactCleaner


def test_cleaner_removes_temporary_audio_file(tmp_path: Path) -> None:
    audio_path = tmp_path / "temporary.wav"
    audio_path.write_bytes(b"fake wav")
    pending_paths: set[Path] = set()
    cleaner = AudioArtifactCleaner(logging.getLogger("tests.audio_artifacts"))

    cleaner.cleanup(audio_path, pending_paths)

    assert not audio_path.exists()
    assert pending_paths == set()


def test_cleaner_retries_locked_audio_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audio_path = tmp_path / "locked.wav"
    audio_path.write_bytes(b"fake wav")
    pending_paths: set[Path] = set()
    cleaner = AudioArtifactCleaner(logging.getLogger("tests.audio_artifacts"))

    original_unlink = Path.unlink
    attempts = 0

    def fail_once(path: Path, missing_ok: bool = False) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("file is locked")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_once)
    cleaner.cleanup(audio_path, pending_paths)

    assert audio_path in pending_paths

    cleaner.retry_pending(pending_paths)

    assert not audio_path.exists()
    assert pending_paths == set()
