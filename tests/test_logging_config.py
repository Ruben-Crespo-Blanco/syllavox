import logging
from pathlib import Path

from syllavox.logging_config import (
    LOG_BACKUP_COUNT,
    LOG_FILE_NAME,
    LOG_MAX_BYTES,
    configure_logging,
    get_log_file_path,
    get_logger,
    log_fatal_initialization_error,
    log_shutdown,
    log_startup,
)
from syllavox.paths import get_logs_dir


def _reset_syllavox_logger() -> None:
    """
    Remove existing syllavox handlers so logging tests can run deterministically.

    This is needed because configure_logging() intentionally avoids adding
    duplicate handlers after the first call.
    """
    logger = logging.getLogger("syllavox")

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    logger.setLevel(logging.NOTSET)
    logger.propagate = True


def test_get_log_file_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert get_log_file_path() == get_logs_dir() / LOG_FILE_NAME


def test_configure_logging_creates_log_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _reset_syllavox_logger()

    logger = configure_logging()
    logger.info("test log entry")

    log_file = get_log_file_path()

    assert log_file.exists()

    contents = log_file.read_text(encoding="utf-8")
    assert "Logging initialized" in contents
    assert "test log entry" in contents


def test_configure_logging_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _reset_syllavox_logger()

    logger_a = configure_logging()
    logger_b = configure_logging()

    assert logger_a is logger_b
    assert len(logger_a.handlers) == 1


def test_get_logger_returns_package_logger() -> None:
    logger = get_logger()
    assert logger.name == "syllavox"


def test_get_logger_returns_child_logger() -> None:
    logger = get_logger("settings")
    assert logger.name == "syllavox.settings"


def test_logging_helpers_write_expected_messages(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _reset_syllavox_logger()

    logger = configure_logging()

    log_startup(logger)
    log_fatal_initialization_error("fatal example", logger)
    log_shutdown(logger)

    contents = get_log_file_path().read_text(encoding="utf-8")

    assert "Application startup" in contents
    assert "Fatal initialization error: fatal example" in contents
    assert "Application shutdown" in contents


def test_logging_rotation_constants_are_reasonable() -> None:
    assert LOG_MAX_BYTES > 0
    assert LOG_MAX_BYTES <= 5 * 1024 * 1024
    assert LOG_BACKUP_COUNT >= 1
