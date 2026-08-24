"""
Application logging configuration.

Responsible for:
- creating the local logs directory
- configuring a rotating file logger
- optionally enabling console logging in development
- exposing a stable logger factory for the rest of the application

No telemetry or remote logging is implemented here.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .paths import ensure_app_directories, get_logs_dir

LOG_FILE_NAME = "app.log"
LOG_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
LOG_BACKUP_COUNT = 5

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_log_file_path() -> Path:
    """
    Return the canonical log file path.

    Expected location:
    %LOCALAPPDATA%\\Syllavox\\logs\\app.log
    """
    return get_logs_dir() / LOG_FILE_NAME


def _is_console_logging_enabled() -> bool:
    """
    Enable console logging only in development.

    Controlled by environment variable:
    SYLLAVOX_CONSOLE_LOG=1
    """
    return os.getenv("SYLLAVOX_CONSOLE_LOG", "").strip() == "1"


def configure_logging() -> logging.Logger:
    """
    Configure application-wide logging.

    Creates:
    - logs directory if missing
    - rotating file handler
    - optional console handler for development

    Returns:
        The root application logger for the package namespace.
    """
    ensure_app_directories()

    log_file_path = get_log_file_path()
    logger = logging.getLogger("syllavox")

    # Prevent duplicate handlers if configure_logging() is called more than once.
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )

    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if _is_console_logging_enabled():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.info("Logging initialized. Log file: %s", log_file_path)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return an application logger.

    Examples:
        get_logger() -> 'syllavox'
        get_logger(__name__) -> 'syllavox.settings'
        get_logger("settings") -> 'syllavox.settings'
    """
    base_name = "syllavox"

    if name is None or name == "":
        return logging.getLogger(base_name)

    if name.startswith(base_name):
        return logging.getLogger(name)

    return logging.getLogger(f"{base_name}.{name}")


def shutdown_logging() -> None:
    """Flush and close Syllavox file/console handlers.

    This is used before privacy cleanup so Windows does not keep the log file
    open while the application data directory is being removed.
    """
    logger = logging.getLogger("syllavox")

    for handler in list(logger.handlers):
        try:
            handler.flush()
        finally:
            handler.close()
            logger.removeHandler(handler)


def log_startup(logger: logging.Logger | None = None) -> None:
    """
    Log application startup.
    """
    active_logger = logger or get_logger()
    active_logger.info("Application startup")


def log_shutdown(logger: logging.Logger | None = None) -> None:
    """
    Log application shutdown.
    """
    active_logger = logger or get_logger()
    active_logger.info("Application shutdown")


def log_fatal_initialization_error(
    message: str,
    logger: logging.Logger | None = None,
) -> None:
    """
    Log a fatal initialization error.
    """
    active_logger = logger or get_logger()
    active_logger.error("Fatal initialization error: %s", message)
