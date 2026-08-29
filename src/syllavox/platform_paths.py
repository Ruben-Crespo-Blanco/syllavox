"""Platform-aware application data-root selection.

The application keeps one stable Syllavox directory below the host's local
user-data root. The root selection is isolated here so macOS and Linux can
adopt their native conventions without changing settings, model, logging, or
audio callers.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from .constants import APP_NAME


def get_platform_data_root(
    *,
    platform_name: str | None = None,
    environment: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return the per-user data root used by Syllavox.

    ``SYLLAVOX_DATA_DIR`` is an explicit override for tests and managed
    deployments. It is intentionally checked before platform defaults.

    Windows uses ``LOCALAPPDATA``. macOS uses ``~/Library/Application Support``
    and Linux/Unix uses ``XDG_DATA_HOME`` or ``~/.local/share``. The returned
    path is the parent directory; callers append ``APP_NAME``.
    """
    current_platform = platform_name or sys.platform
    env = environment if environment is not None else os.environ
    home_dir = home or Path.home()

    override = env.get("SYLLAVOX_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if current_platform == "win32":
        local_appdata = env.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata)
        return home_dir / "AppData" / "Local"

    if current_platform == "darwin":
        return home_dir / "Library" / "Application Support"

    xdg_data_home = env.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser()

    return home_dir / ".local" / "share"


def get_platform_app_dir(**kwargs: object) -> Path:
    """Return the complete per-user Syllavox data directory."""
    return get_platform_data_root(**kwargs) / APP_NAME


__all__ = ["get_platform_app_dir", "get_platform_data_root"]
