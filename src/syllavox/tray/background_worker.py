"""Reusable background-operation support for Qt dialogs."""

from __future__ import annotations

import threading
from collections.abc import Callable

from syllavox.qt_bridge import QtCallbackRelay


WorkerResult = tuple[str, object]


class BackgroundWorkerMixin:
    """Run one background operation and relay its result to the Qt thread."""

    def _initialize_worker(
        self,
        result_handler: Callable[[WorkerResult], None],
    ) -> None:
        self._worker: threading.Thread | None = None
        self._result_relay = QtCallbackRelay(result_handler)

    def _start_worker(
        self,
        operation: Callable[[], object],
        operation_name: str = "success",
    ) -> None:
        def run() -> None:
            try:
                result = operation()
            except Exception as exc:
                self._result_relay.dispatch(("error", str(exc)))
                return

            self._result_relay.dispatch((operation_name, result))

        self._worker = threading.Thread(target=run, daemon=True)
        self._worker.start()

    def _is_worker_running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()
