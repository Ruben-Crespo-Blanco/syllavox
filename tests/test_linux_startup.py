from __future__ import annotations

from pathlib import Path

import pytest

import syllavox.linux_startup as linux_startup
from syllavox.startup import StartupRegistrationError


def test_linux_startup_uses_xdg_config_home_and_source_command(
    tmp_path: Path,
) -> None:
    environment = {"XDG_CONFIG_HOME": str(tmp_path / "xdg-config")}

    linux_startup.set_linux_startup_enabled(
        True,
        platform_name="linux",
        environment=environment,
        executable="/usr/bin/python3",
        arguments=("-m", "syllavox.main"),
    )

    path = linux_startup.get_linux_autostart_path(environment=environment)
    assert path == tmp_path / "xdg-config" / "autostart" / linux_startup.LINUX_AUTOSTART_FILE_NAME
    assert path.read_text(encoding="utf-8") == (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Syllavox\n"
        "Comment=Local offline text to speech\n"
        "Exec=/usr/bin/python3 -m syllavox.main\n"
        "Icon=com.ruben-crespo-blanco.syllavox\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def test_linux_startup_quotes_paths_and_can_be_disabled(tmp_path: Path) -> None:
    home = tmp_path / "home with spaces"

    linux_startup.set_linux_startup_enabled(
        True,
        platform_name="linux",
        home=home,
        environment={},
        executable="/opt/Syllavox App/Syllavox",
        arguments=(),
    )
    path = linux_startup.get_linux_autostart_path(home=home, environment={})
    assert 'Exec="/opt/Syllavox App/Syllavox"\n' in path.read_text(
        encoding="utf-8"
    )

    linux_startup.set_linux_startup_enabled(
        False,
        platform_name="linux",
        home=home,
        environment={},
    )
    assert path.exists() is False


def test_linux_startup_escapes_reserved_and_field_code_characters() -> None:
    assert linux_startup._desktop_exec_argument("100%") == "100%%"
    assert linux_startup._desktop_exec_argument("$HOME") == '"\\\\$HOME"'
    assert linux_startup._desktop_exec_argument("with&shell") == '"with&shell"'
    assert linux_startup._desktop_exec_argument("say`hello") == '"say\\\\`hello"'
    assert linux_startup._desktop_exec_argument("a\\b") == '"a\\\\\\\\b"'


@pytest.mark.parametrize(
    "reserved_character",
    (" ", '"', "'", "\\", ">", "<", "~", "|", "&", ";", "$", "*", "?", "#", "(", ")", "`"),
)
def test_linux_startup_quotes_every_exec_reserved_character(
    reserved_character: str,
) -> None:
    serialized = linux_startup._desktop_exec_argument(
        f"before{reserved_character}after"
    )

    assert serialized.startswith('"')
    assert serialized.endswith('"')


@pytest.mark.parametrize("control_character", ("\n", "\r", "\t", "\x00", "\x7f"))
def test_linux_startup_rejects_control_characters(
    control_character: str,
) -> None:
    with pytest.raises(StartupRegistrationError, match="control characters"):
        linux_startup._desktop_exec_argument(
            f"before{control_character}after"
        )


def test_linux_startup_rejects_other_platforms(tmp_path: Path) -> None:
    with pytest.raises(StartupRegistrationError, match="only on Linux"):
        linux_startup.set_linux_startup_enabled(
            True,
            platform_name="darwin",
            home=tmp_path,
            environment={},
        )


def test_linux_frozen_startup_prefers_the_stable_appimage_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(linux_startup.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        linux_startup.sys,
        "argv",
        ["/tmp/.mount-syllavox/usr/lib/syllavox/Syllavox"],
    )
    monkeypatch.setenv("APPIMAGE", "/home/example/Syllavox.AppImage")

    assert linux_startup.build_linux_startup_arguments() == [
        "/home/example/Syllavox.AppImage",
    ]
