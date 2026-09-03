from __future__ import annotations

import time
import uuid
import subprocess
import sys
from types import SimpleNamespace

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QSystemTrayIcon

import syllavox.app as app_module
from syllavox.instance_guard import get_instance_lock_path

from syllavox.lifecycle import (
    InstanceIpcServer,
    SingleInstanceGuard,
    request_existing_instance_focus,
)
from syllavox.tray.tray_app import TrayApp


class FakeInstanceLock:
    def __init__(self) -> None:
        self.acquire_calls = 0
        self.release_calls = 0

    def acquire(self) -> bool:
        self.acquire_calls += 1
        return True

    def release(self) -> None:
        self.release_calls += 1


def test_single_instance_guard_accepts_platform_lock() -> None:
    lock = FakeInstanceLock()
    guard = SingleInstanceGuard(implementation=lock)

    assert guard.acquire() is True
    guard.release()
    assert lock.acquire_calls == 1
    assert lock.release_calls == 1


def test_non_windows_instance_locks_are_scoped_to_each_user_data_dir(
    tmp_path,
) -> None:
    alice_path = get_instance_lock_path(
        platform_name="linux",
        environment={},
        home=tmp_path / "alice",
    )
    bob_path = get_instance_lock_path(
        platform_name="linux",
        environment={},
        home=tmp_path / "bob",
    )

    assert alice_path != bob_path
    assert alice_path.parent == (
        tmp_path / "alice" / ".local" / "share" / "Syllavox" / "runtime"
    )
    assert bob_path.parent == (
        tmp_path / "bob" / ".local" / "share" / "Syllavox" / "runtime"
    )


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


def test_bootstrap_restarts_only_after_shutdown_and_guard_release(
    monkeypatch,
) -> None:
    events: list[object] = []

    class Guard:
        def acquire(self) -> bool:
            events.append("acquire")
            return True

        def release(self) -> None:
            events.append("release")

    class Signal:
        def connect(self, callback) -> None:
            events.append("connect-shutdown")

    class QtApplication:
        aboutToQuit = Signal()

        def exec(self) -> int:
            events.append("exec")
            return 0

    class StateManager:
        state = SimpleNamespace(value="ready")

        def mark_ready(self) -> None:
            events.append("ready")

    runtime = SimpleNamespace(
        qt_app=QtApplication(),
        api_server=SimpleNamespace(start=lambda: events.append("api-start")),
        state_manager=StateManager(),
        logger=SimpleNamespace(info=lambda *args: None),
        tray_app=SimpleNamespace(
            refresh=lambda: None,
            open_window=lambda: None,
            show_information=lambda *args: None,
        ),
        settings_manager=SimpleNamespace(
            settings={"ui": {"start_minimized_to_tray": True}}
        ),
        main_window=SimpleNamespace(
            restart_command=("python", ["-m", "syllavox.main"])
        ),
        shutdown=lambda: events.append("shutdown"),
    )

    monkeypatch.setattr(app_module, "SingleInstanceGuard", Guard)
    monkeypatch.setattr(app_module, "_create_runtime", lambda: runtime)
    monkeypatch.setattr(app_module, "_configure_hotkey", lambda _runtime: None)
    monkeypatch.setattr(
        app_module.QSystemTrayIcon,
        "isSystemTrayAvailable",
        lambda: True,
    )
    monkeypatch.setattr(
        app_module.QProcess,
        "startDetached",
        lambda executable, arguments: events.append(
            ("launch", executable, arguments)
        ) or (True, 4321),
    )

    assert app_module.bootstrap() == 0
    assert events.index("shutdown") < events.index("release")
    assert events.index("release") < events.index(
        ("launch", "python", ["-m", "syllavox.main"])
    )


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
