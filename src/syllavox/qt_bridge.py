"""Small Qt bridges for delivering callbacks safely to the Qt thread."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal


class QtCallbackRelay(QObject):
    """
    Relay arbitrary callback payloads through a queued Qt signal.

    The relay is created on the Qt thread. Its ``dispatch`` method may be
    called by another thread; the connected callback then runs on the Qt
    thread.
    """

    _payload_received = Signal(object)

    def __init__(self, callback: Callable[[Any], None]) -> None:
        super().__init__()
        self._payload_received.connect(
            callback,
            Qt.ConnectionType.QueuedConnection,
        )

    def dispatch(self, payload: Any) -> None:
        """Queue a payload for the callback on the owning Qt thread."""
        self._payload_received.emit(payload)
