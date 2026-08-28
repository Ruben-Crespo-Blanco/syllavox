"""Make bundled PySide6 and Shiboken DLLs visible before Qt imports."""

from syllavox.qt_runtime import configure_qt_dll_search_path


configure_qt_dll_search_path()
