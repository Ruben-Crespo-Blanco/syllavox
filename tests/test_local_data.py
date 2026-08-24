from __future__ import annotations

from pathlib import Path

from syllavox.local_data import clear_local_data


def test_clear_local_data_removes_all_managed_runtime_data(tmp_path: Path) -> None:
    app_data_dir = tmp_path / "Syllavox"
    (app_data_dir / "logs").mkdir(parents=True)
    (app_data_dir / "models" / "piper" / "g2pW").mkdir(parents=True)
    (app_data_dir / "tmp").mkdir()
    (app_data_dir / "audio").mkdir()
    (app_data_dir / "settings.json").write_text("{}", encoding="utf-8")
    (app_data_dir / "logs" / "app.log").write_text("log", encoding="utf-8")
    (app_data_dir / "models" / "piper" / "voice.onnx").write_bytes(b"model")
    (app_data_dir / "models" / "piper" / "g2pW" / "data.txt").write_text(
        "resource",
        encoding="utf-8",
    )
    (app_data_dir / "tmp" / "request.wav").write_bytes(b"temporary")
    (app_data_dir / "audio" / "retained.wav").write_bytes(b"retained")

    report = clear_local_data(app_data_dir)

    assert report.succeeded is True
    assert report.removed is True
    assert report.removed_bytes > 0
    assert not app_data_dir.exists()


def test_clear_local_data_is_idempotent_for_missing_data(tmp_path: Path) -> None:
    report = clear_local_data(tmp_path / "missing-Syllavox")

    assert report.succeeded is True
    assert report.removed_bytes == 0
