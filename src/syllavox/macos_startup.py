"""Per-user startup registration for macOS.

macOS 13+ can manage the main application through ``SMAppService``. A
LaunchAgent fallback keeps source checkouts and older macOS environments
usable without making Service Management a hard import for Windows builds.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .constants import PRODUCT_NAME
from .startup import StartupRegistrationError


LAUNCH_AGENT_LABEL = "com.ruben-crespo-blanco.syllavox"
LAUNCH_AGENT_PLIST_NAME = f"{LAUNCH_AGENT_LABEL}.plist"
LAUNCHCTL_PATH = "/bin/launchctl"


def get_launch_agent_path(home: Path | None = None) -> Path:
    """Return Syllavox's owned per-user LaunchAgent plist path."""
    home_dir = home or Path.home()
    return home_dir / "Library" / "LaunchAgents" / LAUNCH_AGENT_PLIST_NAME


def build_macos_startup_arguments(
    *,
    executable: str | Path | None = None,
    arguments: Sequence[str] | None = None,
) -> list[str]:
    """Build direct executable arguments for a LaunchAgent plist."""
    if executable is None:
        executable = sys.executable

    if arguments is None:
        arguments = () if getattr(sys, "frozen", False) else (
            "-m",
            "syllavox.main",
        )

    return [str(executable), *(str(argument) for argument in arguments)]


def set_macos_startup_enabled(
    enabled: bool,
    *,
    platform_name: str | None = None,
    home: Path | None = None,
    executable: str | Path | None = None,
    arguments: Sequence[str] | None = None,
    runner: Callable[..., Any] | None = None,
    service_management: Any | None = None,
    use_service_management: bool | None = None,
) -> None:
    """Enable or disable Syllavox for the current macOS user."""
    if (platform_name or sys.platform) != "darwin":
        raise StartupRegistrationError(
            "macOS startup integration is available only on macOS."
        )

    if use_service_management is not False and getattr(sys, "frozen", False):
        service_module = (
            service_management
            if service_management is not None
            else _load_service_management()
        )
        if service_module is not None:
            _set_with_service_management(enabled, service_module)
            return

    _set_with_launch_agent(
        enabled,
        home=home,
        executable=executable,
        arguments=arguments,
        runner=runner,
    )


def _load_service_management() -> Any | None:
    try:
        import ServiceManagement
    except ImportError:
        return None
    return ServiceManagement


def _set_with_service_management(enabled: bool, module: Any) -> None:
    """Use Apple's main-app login-item API when the bundled bridge exists."""
    service_class = getattr(module, "SMAppService", None)
    if service_class is None:
        return _set_with_launch_agent(
            enabled,
            home=None,
            executable=None,
            arguments=None,
            runner=None,
        )

    factory = getattr(service_class, "mainAppService", None)
    service = factory() if callable(factory) else factory
    if service is None:
        raise StartupRegistrationError(
            "macOS main-app login-item service is unavailable."
        )

    method_name = (
        "registerAndReturnError_"
        if enabled
        else "unregisterAndReturnError_"
    )
    method = getattr(service, method_name, None)
    if not callable(method):
        raise StartupRegistrationError(
            "macOS main-app login-item registration is unavailable."
        )

    try:
        result = method(None)
    except Exception as exc:
        raise StartupRegistrationError(
            f"Could not {'enable' if enabled else 'disable'} Syllavox on macOS startup: {exc}"
        ) from exc

    success, error = _service_result(result)
    if success:
        return

    error_text = str(error or "the system rejected the request")
    lowered = error_text.lower()
    if enabled and "already" in lowered and "register" in lowered:
        return
    if not enabled and (
        "not registered" in lowered or "not found" in lowered
    ):
        return

    raise StartupRegistrationError(
        f"Could not {'enable' if enabled else 'disable'} Syllavox on macOS startup: "
        f"{error_text}"
    )


def _service_result(result: Any) -> tuple[bool, Any | None]:
    if isinstance(result, tuple):
        if not result:
            return False, None
        return bool(result[0]), result[1] if len(result) > 1 else None
    return bool(result), None


def _set_with_launch_agent(
    enabled: bool,
    *,
    home: Path | None,
    executable: str | Path | None,
    arguments: Sequence[str] | None,
    runner: Callable[..., Any] | None,
) -> None:
    path = get_launch_agent_path(home)
    launchctl_runner = runner or subprocess.run
    uid = str(os.getuid())

    _bootout_existing(path, uid, launchctl_runner)

    if not enabled:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise StartupRegistrationError(
                f"Could not disable {PRODUCT_NAME} on macOS startup: {exc}"
            ) from exc
        return

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            plistlib.dump(
                {
                    "Label": LAUNCH_AGENT_LABEL,
                    "ProgramArguments": build_macos_startup_arguments(
                        executable=executable,
                        arguments=arguments,
                    ),
                    "RunAtLoad": True,
                    "KeepAlive": False,
                    "ProcessType": "Interactive",
                    "LimitLoadToSessionType": "Aqua",
                },
                handle,
            )
    except OSError as exc:
        raise StartupRegistrationError(
            f"Could not enable {PRODUCT_NAME} on macOS startup: {exc}"
        ) from exc


def _bootout_existing(
    path: Path,
    uid: str,
    runner: Callable[..., Any],
) -> None:
    try:
        runner(
            [LAUNCHCTL_PATH, "bootout", f"gui/{uid}", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # The agent is normally not loaded before the first enable/disable.
        # A missing agent is therefore a successful no-op for bootout.
        return
    except OSError as exc:
        raise StartupRegistrationError(
            f"Could not update {PRODUCT_NAME} on macOS startup: {exc}"
        ) from exc


__all__ = [
    "LAUNCH_AGENT_LABEL",
    "LAUNCH_AGENT_PLIST_NAME",
    "build_macos_startup_arguments",
    "get_launch_agent_path",
    "set_macos_startup_enabled",
]
