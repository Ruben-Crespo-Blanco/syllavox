from __future__ import annotations

from pathlib import Path
import subprocess

import syllavox.macos_startup as macos_startup


def test_macos_launch_agent_contains_direct_startup_command(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        del kwargs
        calls.append(command)
        raise subprocess.CalledProcessError(5, command)

    monkeypatch.setattr(macos_startup.sys, "platform", "darwin")
    monkeypatch.setattr(macos_startup.os, "getuid", lambda: 501, raising=False)

    macos_startup.set_macos_startup_enabled(
        True,
        home=tmp_path,
        executable="/Applications/Syllavox.app/Contents/MacOS/Syllavox",
        arguments=(),
        runner=runner,
        use_service_management=False,
    )

    plist_path = macos_startup.get_launch_agent_path(tmp_path)
    assert plist_path.is_file()
    import plistlib

    plist = plistlib.loads(plist_path.read_bytes())
    assert plist["Label"] == macos_startup.LAUNCH_AGENT_LABEL
    assert plist["ProgramArguments"] == [
        "/Applications/Syllavox.app/Contents/MacOS/Syllavox",
    ]
    assert plist["RunAtLoad"] is True
    assert calls == [
        [
            macos_startup.LAUNCHCTL_PATH,
            "bootout",
            "gui/501",
            str(plist_path),
        ]
    ]

    macos_startup.set_macos_startup_enabled(
        False,
        home=tmp_path,
        runner=runner,
        use_service_management=False,
    )
    assert plist_path.exists() is False
    assert len(calls) == 2


def test_macos_startup_rejects_other_platforms(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(macos_startup.sys, "platform", "linux")

    try:
        macos_startup.set_macos_startup_enabled(
            False,
            home=tmp_path,
            use_service_management=False,
        )
    except Exception as exc:
        assert "only on macOS" in str(exc)
    else:
        raise AssertionError("non-macOS startup registration should fail")
