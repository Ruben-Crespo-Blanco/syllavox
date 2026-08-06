from __future__ import annotations

import pytest

from syllavox.hotkey.errors import HotkeyRegistrationError
from syllavox.hotkey.parser import (
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_WIN,
    parse_hotkey,
)


def test_parser_canonicalizes_aliases_and_modifier_order() -> None:
    binding = parse_hotkey("meta+control+f10")

    assert binding.display_name == "Ctrl+Win+F10"
    assert binding.modifiers == MOD_CONTROL | MOD_WIN | MOD_NOREPEAT
    assert binding.virtual_key == 0x79


def test_parser_supports_named_keys() -> None:
    binding = parse_hotkey("ctrl+alt+space")

    assert binding.display_name == "Ctrl+Alt+Space"
    assert binding.virtual_key == 0x20


@pytest.mark.parametrize(
    "hotkey",
    [
        "",
        "Ctrl",
        "Ctrl+Alt",
        "Ctrl+Ctrl+R",
        "Ctrl+Alt+R+S",
        "Ctrl+Alt+F25",
        "Ctrl+Alt+?",
        "Ctrl++R",
    ],
)
def test_parser_rejects_invalid_hotkeys(hotkey: str) -> None:
    with pytest.raises(HotkeyRegistrationError):
        parse_hotkey(hotkey)


def test_win32_backend_keeps_parser_import_compatibility() -> None:
    from syllavox.hotkey.win32_hotkey import parse_hotkey as win32_parse_hotkey

    assert win32_parse_hotkey("Ctrl+Alt+R") == parse_hotkey("Ctrl+Alt+R")
