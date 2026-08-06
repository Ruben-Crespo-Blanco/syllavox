"""
System tray application wrapper for Epic A.

Owns:
- tray icon
- tray menu
- open window behavior
- clean quit behavior
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from syllavox.constants import PRODUCT_NAME
from syllavox.logging_config import get_logger
from syllavox.qt_bridge import QtCallbackRelay
from syllavox.state import StateManager, StateSnapshot
from syllavox.tray.menu import TrayMenu
from syllavox.tray.window import MainWindow


class TrayApp(QObject):
    def __init__(
        self,
        qt_app: QApplication,
        main_window: MainWindow,
        state_manager: StateManager,
    ) -> None:
        super().__init__()

        self._qt_app = qt_app
        self._main_window = main_window
        self._state_manager = state_manager
        self._state_relay = QtCallbackRelay(self._on_state_changed)
        self._state_manager.add_listener(self._state_relay.dispatch)
        self._logger = get_logger(__name__)

        self._tray_icon = QSystemTrayIcon()
        self._tray_icon.setIcon(self._create_icon())
        self._tray_icon.setToolTip(self._get_tooltip())

        self._menu = TrayMenu(
            state_manager=self._state_manager,
            open_window_callback=self.open_window,
            quit_callback=self.quit,
        )

        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

        self._logger.info("Tray app initialized")

    @property
    def tray_icon(self) -> QSystemTrayIcon:
        return self._tray_icon

    def open_window(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()
        self._logger.info("Tray action: open window")

    def refresh(self) -> None:
        self._tray_icon.setToolTip(self._get_tooltip())
        self._menu.refresh()
        self._main_window.refresh_state_display()

    def quit(self) -> None:
        self._logger.info("Tray action: quit")
        self._main_window.close()
        self._tray_icon.hide()
        self._qt_app.quit()

    def show_warning(
        self,
        title: str,
        message: str,
    ) -> None:
        """
        Show a non-blocking warning notification.

        If the desktop environment does not support tray messages,
        this call silently does nothing.
        """
        self._show_message(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Warning,
        )

    def show_information(
        self,
        title: str,
        message: str,
    ) -> None:
        """Show a non-blocking informational notification."""
        self._show_message(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
        )

    def _show_message(self, title: str, message: str, icon) -> None:
        self._tray_icon.showMessage(
            title,
            message,
            icon,
            5000,
        )

    def _get_tooltip(self) -> str:
        return f"{PRODUCT_NAME} - {self._state_manager.state.value.upper()}"

    def _create_icon(self) -> QIcon:
        """
        Create the tray icon.

        Prefer the bundled Syllavox icon. If the asset is unavailable, fall
        back to a theme icon and then a standard Qt icon so the app still
        launches predictably.
        """
        bundled_icon_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "tray_icon.png"
        )
        if bundled_icon_path.is_file():
            icon = QIcon(str(bundled_icon_path))
            if not icon.isNull():
                return icon

            self._logger.warning(
                "Bundled Syllavox tray icon could not be loaded: %s",
                bundled_icon_path,
            )

        icon = QIcon.fromTheme("audio-volume-high")

        if not icon.isNull():
            return icon

        self._logger.warning("Theme tray icon missing; using fallback Qt icon")

        fallback_icon = self._qt_app.style().standardIcon(
            self._qt_app.style().StandardPixmap.SP_ComputerIcon
        )

        if fallback_icon.isNull():
            self._logger.warning("Fallback Qt tray icon is also null")

        return fallback_icon

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        Open the window on double-click.
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_window()
    
    def _on_state_changed(self, snapshot: StateSnapshot) -> None:
        self._logger.info(
            "State changed: %s error=%s",
            snapshot.state.value,
            snapshot.error_message,
            )
        self.refresh()
