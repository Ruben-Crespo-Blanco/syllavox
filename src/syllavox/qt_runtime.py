"""Runtime preparation for bundled Qt bindings on Windows."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


def configure_qt_dll_search_path() -> None:
    """Register frozen PySide6 and Shiboken directories with Windows."""
    if sys.platform != "win32" or not hasattr(sys, "_MEIPASS"):
        return

    frozen_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    roots = [frozen_root]
    if frozen_root.name.lower() != "_internal":
        roots.insert(0, frozen_root / "_internal")

    handles = getattr(sys, "_syllavox_dll_directory_handles", [])
    registered = getattr(sys, "_syllavox_registered_dll_directories", set())
    for root in roots:
        for directory in (root, root / "shiboken6", root / "PySide6"):
            directory = directory.resolve()
            directory_text = os.fspath(directory)
            if not directory.is_dir() or directory_text in registered:
                continue
            handles.append(os.add_dll_directory(directory_text))
            registered.add(directory_text)
            os.environ["PATH"] = (
                directory_text + os.pathsep + os.environ.get("PATH", "")
            )

    sys._syllavox_dll_directory_handles = handles
    sys._syllavox_registered_dll_directories = registered

    # The PyInstaller bootloader establishes _internal as the process DLL
    # directory. On Windows, that can make the loader select an incompatible
    # copy of a Qt dependency before the nested PySide6 directory is checked.
    # Load the small startup Qt dependency chain by absolute path so all later
    # PySide6 extension imports reuse these exact bundled binaries.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.SetDllDirectoryW(None)

    native_handles = getattr(sys, "_syllavox_qt_native_handles", [])
    loaded_native = getattr(sys, "_syllavox_loaded_qt_native", set())
    native_libraries = (
        (frozen_root / "shiboken6", ("shiboken6.abi3.dll",)),
        (
            frozen_root / "PySide6",
            (
                "pyside6.abi3.dll",
                "Qt6Core.dll",
                "Qt6Gui.dll",
                "Qt6Network.dll",
                "Qt6Widgets.dll",
                "Qt6Multimedia.dll",
                "Qt6MultimediaWidgets.dll",
            ),
        ),
    )

    for directory, names in native_libraries:
        for name in names:
            path = (directory / name).resolve()
            path_text = os.fspath(path)
            if not path.is_file() or path_text in loaded_native:
                continue

            native_handles.append(ctypes.WinDLL(path_text, winmode=0x8))
            loaded_native.add(path_text)

    sys._syllavox_qt_native_handles = native_handles
    sys._syllavox_loaded_qt_native = loaded_native
