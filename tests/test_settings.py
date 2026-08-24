import json
from pathlib import Path

from syllavox.constants import CURRENT_CONFIG_SCHEMA_VERSION, DEFAULT_MAX_TEXT_LENGTH
from syllavox.settings import SettingsManager, get_default_settings


def test_first_run_default_creation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    settings_path = tmp_path / "settings.json"
    manager = SettingsManager(settings_path=settings_path)

    result = manager.load()

    assert result.created_default_file is True
    assert result.recovered_from_corruption is False
    assert result.repaired_missing_keys is False

    assert settings_path.exists()

    with settings_path.open("r", encoding="utf-8") as handle:
        saved = json.load(handle)

    assert saved == get_default_settings()
    assert result.settings == get_default_settings()


def test_successful_save_and_reload(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    settings_path = tmp_path / "settings.json"
    manager = SettingsManager(settings_path=settings_path)

    manager.load()

    updated = manager.settings
    updated["window"]["width"] = 900
    updated["window"]["height"] = 500
    updated["ui"]["start_minimized_to_tray"] = False
    updated["tts"]["voice_id"] = "en_US-test"
    manager.update(updated)

    new_manager = SettingsManager(settings_path=settings_path)
    result = new_manager.load()

    assert result.created_default_file is False
    assert result.recovered_from_corruption is False
    assert result.repaired_missing_keys is False

    assert result.settings["window"]["width"] == 900
    assert result.settings["window"]["height"] == 500
    assert result.settings["ui"]["start_minimized_to_tray"] is False
    assert result.settings["tts"]["voice_id"] == "en_US-test"


def test_missing_keys_are_repaired(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    settings_path = tmp_path / "settings.json"

    incomplete = {
        "version": CURRENT_CONFIG_SCHEMA_VERSION,
        "window": {
            "width": 800,
        },
        "tts": {
            "backend": "piper",
        },
    }

    with settings_path.open("w", encoding="utf-8") as handle:
        json.dump(incomplete, handle)

    manager = SettingsManager(settings_path=settings_path)
    result = manager.load()

    assert result.repaired_missing_keys is True
    assert result.recovered_from_corruption is False

    repaired = result.settings
    assert repaired["window"]["width"] == 800
    assert repaired["window"]["height"] == 720
    assert repaired["window"]["remember_position"] is True
    assert repaired["ui"]["start_minimized_to_tray"] is True
    assert repaired["hotkey"]["enabled"] is True
    assert repaired["hotkey"]["action"] == "speak_clipboard"
    assert repaired["tts"]["backend"] == "piper"
    assert repaired["tts"]["voice_id"] is None
    assert repaired["tts"]["max_text_length"] == DEFAULT_MAX_TEXT_LENGTH
    assert repaired["playback"]["volume"] == 1.0
    assert repaired["playback"]["rate"] == 1.0

    with settings_path.open("r", encoding="utf-8") as handle:
        rewritten = json.load(handle)

    assert rewritten == repaired


def test_unknown_future_keys_are_preserved(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    settings_path = tmp_path / "settings.json"

    custom = get_default_settings()
    custom["future_feature"] = {"enabled": True}
    custom["tts"]["future_backend_option"] = "x"

    with settings_path.open("w", encoding="utf-8") as handle:
        json.dump(custom, handle)

    manager = SettingsManager(settings_path=settings_path)
    result = manager.load()

    assert result.repaired_missing_keys is False
    assert result.settings["future_feature"] == {"enabled": True}
    assert result.settings["tts"]["future_backend_option"] == "x"


def test_corrupt_json_recovery(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{ invalid json", encoding="utf-8")

    manager = SettingsManager(settings_path=settings_path)
    result = manager.load()

    assert result.recovered_from_corruption is True
    assert result.backup_path is not None
    assert result.backup_path.exists()
    assert result.backup_path.read_text(encoding="utf-8") == "{ invalid json"

    assert settings_path.exists()

    with settings_path.open("r", encoding="utf-8") as handle:
        saved = json.load(handle)

    assert saved == get_default_settings()
    assert result.settings == get_default_settings()


def test_non_dict_json_recovery(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    settings_path = tmp_path / "settings.json"
    settings_path.write_text('["not", "a", "dict"]', encoding="utf-8")

    manager = SettingsManager(settings_path=settings_path)
    result = manager.load()

    assert result.recovered_from_corruption is True
    assert result.backup_path is not None
    assert result.backup_path.exists()
    assert result.settings == get_default_settings()
