import os
from pathlib import Path

import syllavox.platform_paths as platform_paths
from syllavox.constants import APP_NAME, LOGS_DIR_NAME, SETTINGS_FILE_NAME
from syllavox.paths import (
    ensure_app_directories,
    get_app_base_dir,
    get_local_appdata_dir,
    get_logs_dir,
    get_settings_file_path,
)
from syllavox.tts.paths import get_sherpa_onnx_models_dir


def test_get_local_appdata_dir_uses_localappdata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(platform_paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert get_local_appdata_dir() == tmp_path


def test_get_local_appdata_dir_falls_back_to_home(monkeypatch) -> None:
    monkeypatch.setattr(platform_paths.sys, "platform", "win32")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert get_local_appdata_dir() == Path.home() / "AppData" / "Local"


def test_platform_data_root_supports_macos_layout(tmp_path: Path) -> None:
    assert platform_paths.get_platform_data_root(
        platform_name="darwin",
        environment={},
        home=tmp_path,
    ) == tmp_path / "Library" / "Application Support"


def test_platform_data_root_supports_xdg_layout(tmp_path: Path) -> None:
    assert platform_paths.get_platform_data_root(
        platform_name="linux",
        environment={},
        home=tmp_path,
    ) == tmp_path / ".local" / "share"


def test_platform_data_root_honors_xdg_data_home(tmp_path: Path) -> None:
    xdg_data_home = tmp_path / "xdg-data"

    assert platform_paths.get_platform_data_root(
        platform_name="linux",
        environment={"XDG_DATA_HOME": str(xdg_data_home)},
        home=tmp_path,
    ) == xdg_data_home


def test_platform_data_root_honors_explicit_override(tmp_path: Path) -> None:
    override = tmp_path / "managed-data"

    assert platform_paths.get_platform_data_root(
        platform_name="darwin",
        environment={"SYLLAVOX_DATA_DIR": str(override)},
        home=tmp_path,
    ) == override


def test_app_base_dir_is_under_localappdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(platform_paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    expected = tmp_path / APP_NAME

    assert get_app_base_dir() == expected


def test_settings_file_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(platform_paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    expected = tmp_path / APP_NAME / SETTINGS_FILE_NAME

    assert get_settings_file_path() == expected


def test_logs_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(platform_paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    expected = tmp_path / APP_NAME / LOGS_DIR_NAME

    assert get_logs_dir() == expected


def test_sherpa_models_dir_is_backend_specific(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(platform_paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert get_sherpa_onnx_models_dir() == (
        tmp_path / APP_NAME / "models" / "sherpa-onnx"
    )


def test_ensure_app_directories_creates_base_and_logs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(platform_paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    ensure_app_directories()

    assert get_app_base_dir().exists()
    assert get_app_base_dir().is_dir()

    assert get_logs_dir().exists()
    assert get_logs_dir().is_dir()
