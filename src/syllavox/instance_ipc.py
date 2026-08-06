"""Local IPC used to focus the already-running Syllavox instance."""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


INSTANCE_SERVER_NAME = "Syllavox-ipc-v1"
INSTANCE_SHOW_COMMAND = b"show"


class InstanceIpcServer(QObject):
    """Receive commands from secondary launches in the Qt main thread."""

    show_requested = Signal()

    def __init__(
        self,
        server_name: str = INSTANCE_SERVER_NAME,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._server_name = server_name
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._handle_new_connection)
        self._sockets: list[QLocalSocket] = []

    @property
    def is_listening(self) -> bool:
        """Return whether the IPC endpoint is currently listening."""
        return self._server.isListening()

    def start(self) -> None:
        """Start listening, removing only a stale endpoint if necessary."""
        if self._server.isListening():
            return

        QLocalServer.removeServer(self._server_name)
        if not self._server.listen(self._server_name):
            raise RuntimeError(
                "Could not start single-instance IPC server: "
                f"{self._server.errorString()}"
            )

    def stop(self) -> None:
        """Stop listening and release the local endpoint."""
        self._server.close()

        for socket in list(self._sockets):
            socket.disconnectFromServer()
            socket.deleteLater()

        self._sockets.clear()
        QLocalServer.removeServer(self._server_name)

    def _handle_new_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue

            self._sockets.append(socket)
            socket.readyRead.connect(
                lambda socket=socket: self._read_socket(socket)
            )
            socket.disconnected.connect(
                lambda socket=socket: self._forget_socket(socket)
            )
            QTimer.singleShot(0, lambda socket=socket: self._read_socket(socket))

    def _read_socket(self, socket: QLocalSocket) -> None:
        payload = bytes(socket.readAll())
        if not payload:
            return

        for command in payload.splitlines():
            if command.strip() == INSTANCE_SHOW_COMMAND:
                self.show_requested.emit()

        if socket.state() != QLocalSocket.LocalSocketState.UnconnectedState:
            socket.disconnectFromServer()

    def _forget_socket(self, socket: QLocalSocket) -> None:
        if socket in self._sockets:
            self._sockets.remove(socket)
        socket.deleteLater()


def request_existing_instance_focus(
    server_name: str = INSTANCE_SERVER_NAME,
    attempts: int = 10,
    timeout_ms: int = 100,
) -> bool:
    """Ask the primary instance to show its window."""
    for attempt in range(attempts):
        socket = QLocalSocket()
        socket.connectToServer(server_name)

        if socket.waitForConnected(timeout_ms):
            payload = INSTANCE_SHOW_COMMAND + b"\n"
            bytes_written = socket.write(payload)
            socket.flush()
            socket.waitForBytesWritten(timeout_ms)
            if bytes_written == len(payload):
                socket.disconnectFromServer()
                return True

        socket.abort()
        if attempt < attempts - 1:
            time.sleep(timeout_ms / 1000)

    return False


__all__ = [
    "INSTANCE_SERVER_NAME",
    "InstanceIpcServer",
    "request_existing_instance_focus",
]
