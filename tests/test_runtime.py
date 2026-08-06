from __future__ import annotations

import logging

from syllavox.runtime import ApplicationRuntime


class FakeCleanupService:
    def __init__(
        self,
        name: str,
        calls: list[str],
        fail: bool = False,
    ) -> None:
        self.name = name
        self.calls = calls
        self.fail = fail

    def cleanup(self) -> None:
        self.calls.append(self.name)

        if self.fail:
            raise RuntimeError(f"{self.name} cleanup failed")

    def stop(self) -> None:
        self.cleanup()

    def shutdown(self) -> None:
        self.cleanup()


class FakeTrayIcon:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def hide(self) -> None:
        self._calls.append("tray")


class FakeTray:
    def __init__(self, calls: list[str]) -> None:
        self.tray_icon = FakeTrayIcon(calls)


def make_runtime(
    calls: list[str],
    api_fails: bool = False,
) -> ApplicationRuntime:
    api_server = FakeCleanupService("api", calls, fail=api_fails)
    hotkey_manager = FakeCleanupService("hotkey", calls)
    audio_player = FakeCleanupService("audio", calls)

    return ApplicationRuntime(
        qt_app=object(),
        logger=logging.getLogger("tests.runtime"),
        settings_manager=object(),
        state_manager=object(),
        backend_manager=object(),
        audio_player=audio_player,  # type: ignore[arg-type]
        speech_controller=object(),
        hotkey_manager=hotkey_manager,  # type: ignore[arg-type]
        main_window=object(),
        tray_app=FakeTray(calls),  # type: ignore[arg-type]
        api_server=api_server,  # type: ignore[arg-type]
    )


def test_runtime_shutdown_cleans_resources_in_order() -> None:
    calls: list[str] = []
    runtime = make_runtime(calls)

    runtime.shutdown()

    assert calls == ["api", "hotkey", "audio", "tray"]
    assert runtime.is_shutdown is True


def test_runtime_shutdown_is_idempotent() -> None:
    calls: list[str] = []
    runtime = make_runtime(calls)

    runtime.shutdown()
    runtime.shutdown()

    assert calls == ["api", "hotkey", "audio", "tray"]


def test_runtime_shutdown_continues_after_cleanup_failure(
    caplog,
) -> None:
    calls: list[str] = []
    runtime = make_runtime(calls, api_fails=True)

    with caplog.at_level(logging.WARNING, logger="tests.runtime"):
        runtime.shutdown()

    assert calls == ["api", "hotkey", "audio", "tray"]
    assert "Failed to clean up API server" in caplog.text
