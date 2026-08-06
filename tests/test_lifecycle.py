from __future__ import annotations

import time
import uuid
import subprocess
import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QSystemTrayIcon

import syllavox.app as app_module

from syllavox.lifecycle import (
    InstanceIpcServer,
    SingleInstanceGuard,
    request_existing_instance_focus,
)
from syllavox.tray.tray_app import TrayApp


def _process_events_until(
    application: QCoreApplication,
    predicate,
    timeout_seconds: float = 1.0,
) -> bool:
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        application.processEvents()
        if predicate():
            return True
        time.sleep(0.01)

    application.processEvents()
    return bool(predicate())


def test_single_instance_guard_allows_one_owner() -> None:
    name = f"Local\\Syllavox-test-{uuid.uuid4()}"
    first = SingleInstanceGuard(name)
    second = SingleInstanceGuard(name)

    try:
        assert first.acquire() is True
        assert second.acquire() is False
    finally:
        second.release()
        first.release()

    assert second.acquire() is True
    second.release()


def test_secondary_launch_requests_focus() -> None:
    application = QCoreApplication.instance() or QCoreApplication([])
    server_name = f"Syllavox-test-ipc-{uuid.uuid4()}"
    server = InstanceIpcServer(server_name)
    focus_requests: list[bool] = []
    server.show_requested.connect(lambda: focus_requests.append(True))
    child: subprocess.Popen | None = None

    try:
        server.start()
        assert server.is_listening is True
        child_code = (
            "import sys; "
            "from syllavox.lifecycle import request_existing_instance_focus; "
            "raise SystemExit(0 if request_existing_instance_focus("
            "sys.argv[1]) else 1)"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", child_code, server_name],
        )
        assert _process_events_until(
            application,
            lambda: child.poll() is not None and bool(focus_requests),
            timeout_seconds=10.0,
        )
        assert child.wait(timeout=1) == 0
        assert focus_requests == [True]
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(timeout=1)
        server.stop()


def test_secondary_launch_returns_false_when_no_primary_exists() -> None:
    server_name = f"Syllavox-missing-ipc-{uuid.uuid4()}"

    assert request_existing_instance_focus(
        server_name,
        attempts=1,
        timeout_ms=10,
    ) is False


def test_bootstrap_exits_without_creating_runtime_for_secondary_launch(
    monkeypatch,
) -> None:
    focus_requests: list[bool] = []

    class ExistingInstanceGuard:
        def acquire(self) -> bool:
            return False

        def release(self) -> None:
            raise AssertionError("A secondary instance must not release the owner guard")

    monkeypatch.setattr(app_module, "SingleInstanceGuard", ExistingInstanceGuard)
    monkeypatch.setattr(
        app_module,
        "request_existing_instance_focus",
        lambda: focus_requests.append(True) or True,
    )
    monkeypatch.setattr(
        app_module,
        "_create_runtime",
        lambda: (_ for _ in ()).throw(
            AssertionError("A secondary instance must not create a runtime")
        ),
    )

    assert app_module.bootstrap() == 0
    assert focus_requests == [True]


def test_tray_information_notification_uses_information_icon() -> None:
    calls: list[tuple[object, ...]] = []

    class FakeTrayIcon:
        def showMessage(self, *args: object) -> None:
            calls.append(args)

    tray_app = TrayApp.__new__(TrayApp)
    tray_app._tray_icon = FakeTrayIcon()

    tray_app.show_information("Syllavox", "Ready")

    assert calls == [
        (
            "Syllavox",
            "Ready",
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )
    ]


def test_tray_icon_uses_bundled_syllavox_asset() -> None:
    tray_app = TrayApp.__new__(TrayApp)

    icon = tray_app._create_icon()

    assert not icon.isNull()
