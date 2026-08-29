"""
Application path resolution utilities.

Responsible for:
- resolving OS-specific directories
- providing canonical paths for config and logs
- ensuring required directories exist on first run
"""

from pathlib import Path

from .constants import (
    APP_NAME,
    SETTINGS_FILE_NAME,
    LOGS_DIR_NAME,
)
from .platform_paths import get_platform_data_root


def get_local_appdata_dir() -> Path:
    """
    Resolve the platform's local application-data root.

    The historical function name is retained for compatibility with existing
    callers. Platform selection is isolated in ``platform_paths``.
    """
    return get_platform_data_root()


def get_app_base_dir() -> Path:
    """
    Base application directory: the platform's local Syllavox data directory.
    """
    return get_local_appdata_dir() / APP_NAME


def get_settings_file_path() -> Path:
    """
    Full path to settings.json.
    """
    return get_app_base_dir() / SETTINGS_FILE_NAME


def get_logs_dir() -> Path:
    """
    Logs directory path.
    """
    return get_app_base_dir() / LOGS_DIR_NAME


def ensure_app_directories() -> None:
    """
    Ensure required directories exist.

    Creates:
    - base app directory
    - logs directory

    Safe to call multiple times.
    """
    base_dir = get_app_base_dir()
    logs_dir = get_logs_dir()

    base_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
