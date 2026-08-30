"""Generate the registered SAPI COM wrappers before a frozen build."""

from __future__ import annotations

import sys


def main() -> int:
    if sys.platform != "win32":
        raise RuntimeError("SAPI wrappers can only be prepared on Windows.")

    try:
        from comtypes.client import CreateObject
    except ImportError as exc:
        raise RuntimeError(
            "SAPI packaging requires comtypes. Install the 'sapi' extra."
        ) from exc

    # comtypes generates the registered SAPI typelib wrappers on the first
    # normal CreateObject call. The generated files are collected by the
    # PyInstaller spec so the frozen app does not depend on runtime code
    # generation or write access to its _internal directory.
    voice = CreateObject("SAPI.SpVoice")
    count = int(voice.GetVoices().Count)
    print(f"Prepared SAPI COM wrappers; {count} voice token(s) visible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
