"""Per-user Linux desktop startup registration.

Linux desktop environments share the freedesktop autostart convention even
though their session managers differ.  Syllavox writes one user-owned
``.desktop`` file and never requires root privileges or a system-wide service.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from .constants import PRODUCT_NAME
from .startup import StartupRegistrationError


LINUX_DESKTOP_ID = "com.ruben-crespo-blanco.syllavox"
LINUX_AUTOSTART_FILE_NAME = f"{LINUX_DESKTOP_ID}.desktop"


def get_linux_autostart_dir(
    *,
    home: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Return the current user's XDG autostart directory."""
    env = environment if environment is not None else os.environ
    config_home = env.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / "autostart"

    return (home or Path.home()) / ".config" / "autostart"


def get_linux_autostart_path(
    *,
    home: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Return Syllavox's user-owned autostart desktop-entry path."""
    return get_linux_autostart_dir(
        home=home,
        environment=environment,
    ) / LINUX_AUTOSTART_FILE_NAME


def build_linux_startup_arguments(
    *,
    executable: str | Path | None = None,
    arguments: Sequence[str] | None = None,
) -> list[str]:
    """Build direct executable arguments for a Linux desktop entry."""
    if executable is None:
        if getattr(sys, "frozen", False):
            # AppImage exposes its stable outer path through APPIMAGE while
            # sys.executable points into the temporary mounted filesystem.
            executable = (
                os.environ.get("APPIMAGE")
                or sys.argv[0]
                or sys.executable
            )
        else:
            executable = sys.executable

    if arguments is None:
        arguments = () if getattr(sys, "frozen", False) else (
            "-m",
            "syllavox.main",
        )

    return [str(executable), *(str(argument) for argument in arguments)]


def _desktop_exec_argument(argument: str) -> str:
    """Quote one Exec key argument using desktop-entry quoting rules."""
    if argument and all(
        character not in argument for character in (" ", "\t", '"', "'", "\\")
    ):
        return argument

    escaped = argument.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_linux_autostart_entry(
    *,
    executable: str | Path | None = None,
    arguments: Sequence[str] | None = None,
    icon_name: str = LINUX_DESKTOP_ID,
) -> str:
    """Return the complete user-owned autostart desktop entry."""
    command = " ".join(
        _desktop_exec_argument(argument)
        for argument in build_linux_startup_arguments(
            executable=executable,
            arguments=arguments,
        )
    )
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={PRODUCT_NAME}\n"
        "Comment=Local offline text to speech\n"
        f"Exec={command}\n"
        f"Icon={icon_name}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def set_linux_startup_enabled(
    enabled: bool,
    *,
    platform_name: str | None = None,
    home: Path | None = None,
    environment: Mapping[str, str] | None = None,
    executable: str | Path | None = None,
    arguments: Sequence[str] | None = None,
) -> None:
    """Enable or disable Syllavox for the current Linux user's session."""
    if (platform_name or sys.platform) != "linux":
        raise StartupRegistrationError(
            "Linux startup integration is available only on Linux."
        )

    path = get_linux_autostart_path(
        home=home,
        environment=environment,
    )

    if not enabled:
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise StartupRegistrationError(
                f"Could not disable {PRODUCT_NAME} on Linux startup: {exc}"
            ) from exc
        return

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(f".{path.name}.tmp")
        temporary_path.write_text(
            build_linux_autostart_entry(
                executable=executable,
                arguments=arguments,
            ),
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    except OSError as exc:
        raise StartupRegistrationError(
            f"Could not enable {PRODUCT_NAME} on Linux startup: {exc}"
        ) from exc


__all__ = [
    "LINUX_AUTOSTART_FILE_NAME",
    "LINUX_DESKTOP_ID",
    "build_linux_autostart_entry",
    "build_linux_startup_arguments",
    "get_linux_autostart_dir",
    "get_linux_autostart_path",
    "set_linux_startup_enabled",
]
