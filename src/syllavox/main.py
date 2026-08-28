"""
Thin application entry point.
"""

from __future__ import annotations

import sys
import traceback

from .qt_runtime import configure_qt_dll_search_path

configure_qt_dll_search_path()

from PySide6.QtWidgets import QApplication, QMessageBox

from .app import bootstrap
from .constants import PRODUCT_NAME
from .logging_config import configure_logging, log_fatal_initialization_error


def _show_startup_failure(message: str) -> None:
    """Show a visible startup error when Qt initialized far enough."""
    application = QApplication.instance()
    if application is None:
        return

    QMessageBox.critical(
        None,
        PRODUCT_NAME,
        f"The application could not start.\n\n{message}",
    )


def main() -> int:
    try:
        return bootstrap()
    except Exception as exc:
        try:
            logger = configure_logging()
            log_fatal_initialization_error(f"{exc}", logger)
            logger.error("Unhandled exception:\n%s", traceback.format_exc())
            _show_startup_failure(str(exc))
        except Exception:
            # Last-resort fallback if logging itself fails.
            print("Fatal application error:", exc, file=sys.stderr)
            traceback.print_exc()

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
