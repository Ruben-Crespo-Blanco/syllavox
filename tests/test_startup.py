from __future__ import annotations

from pathlib import Path

import pytest

import syllavox.startup as startup


class FakeRegistry:
    HKEY_CURRENT_USER = object()
    KEY_SET_VALUE = 0x0002
    REG_SZ = 1

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.opened: list[tuple[object, str, int, int]] = []
        self.closed: list[object] = []

    def OpenKey(self, root, subkey, reserved, access):  # noqa: N802
        self.opened.append((root, subkey, reserved, access))
        return self

    def CreateKey(self, root, subkey):  # noqa: N802
        self.opened.append((root, subkey, 0, self.KEY_SET_VALUE))
        return self

    def SetValueEx(self, key, name, reserved, value_type, value):  # noqa: N802
        del key, reserved, value_type
        self.values[name] = value

    def DeleteValue(self, key, name):  # noqa: N802
        del key
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]

    def CloseKey(self, key):  # noqa: N802
        self.closed.append(key)


class MissingRunKeyRegistry(FakeRegistry):
    def OpenKey(self, root, subkey, reserved, access):  # noqa: N802
        del root, subkey, reserved, access
        raise FileNotFoundError("Run key does not exist")


def test_startup_support_is_platform_specific() -> None:
    assert startup.is_startup_supported("win32") is True
    assert startup.is_startup_supported("darwin") is True
    assert startup.is_startup_supported("linux") is False


def test_build_startup_command_quotes_executable_and_arguments() -> None:
    command = startup.build_startup_command(
        executable=Path(r"C:\Program Files\Syllavox\Syllavox.exe"),
        arguments=("--example", "value with spaces"),
    )

    assert command == (
        r'"C:\Program Files\Syllavox\Syllavox.exe" --example "value with spaces"'
    )


def test_enable_and_disable_startup_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = FakeRegistry()
    monkeypatch.setattr(startup.sys, "platform", "win32")

    startup.set_startup_enabled(
        True,
        command=r'"C:\Syllavox\Syllavox.exe"',
        registry_module=registry,
    )
    assert registry.values == {"Syllavox": r'"C:\Syllavox\Syllavox.exe"'}

    startup.set_startup_enabled(False, registry_module=registry)
    assert registry.values == {}
    assert len(registry.closed) == 2


def test_startup_setting_is_noop_when_disabled_on_unsupported_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(startup.sys, "platform", "linux")

    startup.set_startup_enabled(False)

    with pytest.raises(startup.StartupRegistrationError):
        startup.set_startup_enabled(True)


def test_disabling_startup_does_not_create_a_missing_run_key() -> None:
    registry = MissingRunKeyRegistry()

    startup.set_startup_enabled(False, registry_module=registry)

    assert registry.opened == []
    assert registry.closed == []
