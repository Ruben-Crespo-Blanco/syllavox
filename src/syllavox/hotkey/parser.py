"""Validation and canonicalization of user-facing hotkey strings."""

from __future__ import annotations

from dataclasses import dataclass

from syllavox.hotkey.errors import HotkeyRegistrationError


# These values are kept here so parsing remains independent from ctypes and
# Qt. The Win32 backend consumes the resulting binding directly.
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


# Windows virtual-key values for non-alphanumeric keys.
NAMED_VIRTUAL_KEYS: dict[str, int] = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
}

MODIFIER_VALUES: dict[str, int] = {
    "ALT": MOD_ALT,
    "CTRL": MOD_CONTROL,
    "CONTROL": MOD_CONTROL,
    "SHIFT": MOD_SHIFT,
    "WIN": MOD_WIN,
    "WINDOWS": MOD_WIN,
    "META": MOD_WIN,
}


@dataclass(frozen=True)
class HotkeyBinding:
    """Parsed and canonicalized hotkey description."""

    display_name: str
    modifiers: int
    virtual_key: int


def parse_hotkey(hotkey: str) -> HotkeyBinding:
    """Parse a user-facing hotkey string into a canonical binding."""
    if not isinstance(hotkey, str) or not hotkey.strip():
        raise HotkeyRegistrationError("Hotkey cannot be empty.")

    raw_parts = [part.strip() for part in hotkey.split("+")]

    if any(not part for part in raw_parts):
        raise HotkeyRegistrationError(
            f"Invalid hotkey format: {hotkey!r}"
        )

    modifiers = MOD_NOREPEAT
    modifier_names: list[str] = []
    virtual_key: int | None = None
    key_name: str | None = None

    for raw_part in raw_parts:
        part = raw_part.upper()

        if part in MODIFIER_VALUES:
            modifier_value = MODIFIER_VALUES[part]

            if modifiers & modifier_value:
                raise HotkeyRegistrationError(
                    f"Duplicate hotkey modifier: {raw_part}"
                )

            modifiers |= modifier_value
            modifier_names.append(_canonical_modifier_name(part))
            continue

        if virtual_key is not None:
            raise HotkeyRegistrationError(
                "A hotkey must contain exactly one non-modifier key."
            )

        virtual_key = _parse_virtual_key(part)
        key_name = _canonical_key_name(part)

    if virtual_key is None or key_name is None:
        raise HotkeyRegistrationError(
            "A hotkey must contain one non-modifier key."
        )

    if not modifier_names:
        raise HotkeyRegistrationError(
            "Global hotkeys must include at least one modifier."
        )

    canonical_parts = _sort_modifier_names(modifier_names)
    canonical_parts.append(key_name)

    return HotkeyBinding(
        display_name="+".join(canonical_parts),
        modifiers=modifiers,
        virtual_key=virtual_key,
    )


def _parse_virtual_key(key_name: str) -> int:
    if len(key_name) == 1 and "A" <= key_name <= "Z":
        return ord(key_name)

    if len(key_name) == 1 and "0" <= key_name <= "9":
        return ord(key_name)

    if key_name.startswith("F") and key_name[1:].isdigit():
        function_number = int(key_name[1:])

        if 1 <= function_number <= 24:
            return 0x70 + function_number - 1

    if key_name in NAMED_VIRTUAL_KEYS:
        return NAMED_VIRTUAL_KEYS[key_name]

    raise HotkeyRegistrationError(
        f"Unsupported hotkey key: {key_name}"
    )


def _canonical_modifier_name(name: str) -> str:
    if name in {"CTRL", "CONTROL"}:
        return "Ctrl"

    if name == "ALT":
        return "Alt"

    if name == "SHIFT":
        return "Shift"

    if name in {"WIN", "WINDOWS", "META"}:
        return "Win"

    raise HotkeyRegistrationError(
        f"Unsupported hotkey modifier: {name}"
    )


def _sort_modifier_names(names: list[str]) -> list[str]:
    order = {
        "Ctrl": 0,
        "Alt": 1,
        "Shift": 2,
        "Win": 3,
    }

    return sorted(set(names), key=lambda name: order[name])


def _canonical_key_name(name: str) -> str:
    if len(name) == 1:
        return name

    if name.startswith("F") and name[1:].isdigit():
        return name

    aliases = {
        "RETURN": "Enter",
        "ENTER": "Enter",
        "ESC": "Escape",
        "ESCAPE": "Escape",
        "SPACE": "Space",
        "TAB": "Tab",
        "BACKSPACE": "Backspace",
        "PAGEUP": "PageUp",
        "PAGEDOWN": "PageDown",
        "HOME": "Home",
        "END": "End",
        "LEFT": "Left",
        "RIGHT": "Right",
        "UP": "Up",
        "DOWN": "Down",
        "INSERT": "Insert",
        "DELETE": "Delete",
    }

    return aliases.get(name, name.title())


def hotkey_hint(platform_name: str | None = None) -> str:
    """Return the platform-appropriate hint for the shared hotkey syntax."""
    import sys

    current_platform = platform_name or sys.platform
    if current_platform == "darwin":
        return (
            "Use Ctrl, Alt (Option), Shift, or Meta (Command) plus one "
            "supported key."
        )

    return "Use Ctrl, Alt, Shift, or Win plus one supported key."


__all__ = [
    "HotkeyBinding",
    "MOD_ALT",
    "MOD_CONTROL",
    "MOD_NOREPEAT",
    "MOD_SHIFT",
    "MOD_WIN",
    "MODIFIER_VALUES",
    "NAMED_VIRTUAL_KEYS",
    "hotkey_hint",
    "parse_hotkey",
]
