"""Tray menu construction for the desktop application."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from syllavox.state import StateManager


class TrayMenu(QMenu):
    """
    System tray context menu.

    This menu owns only tray actions. It does not own the app lifecycle.
    """

    def __init__(
        self,
        state_manager: StateManager,
        open_window_callback,
        quit_callback,
    ) -> None:
        super().__init__()

        self._state_manager = state_manager
        self._open_window_callback = open_window_callback
        self._quit_callback = quit_callback

        self.open_action = QAction("Open", self)
        self.status_action = QAction(self._get_status_text(), self)
        self.status_action.setEnabled(False)

        self.quit_action = QAction("Quit", self)

        self.open_action.triggered.connect(self._open_window_callback)
        self.quit_action.triggered.connect(self._quit_callback)

        self.addAction(self.open_action)
        self.addAction(self.status_action)
        self.addSeparator()
        self.addAction(self.quit_action)

    def refresh(self) -> None:
        self.status_action.setText(self._get_status_text())

    def _get_status_text(self) -> str:
        return f"Status: {self._state_manager.state.value.upper()}"
