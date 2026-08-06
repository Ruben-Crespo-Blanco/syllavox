"""
Application runtime container and lifecycle cleanup.

The runtime owns the long-lived services created during application startup.
Keeping ownership in one object makes shutdown deterministic and gives the
bootstrap module a small, explicit composition surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import Logger
from typing import TYPE_CHECKING, Callable

from .logging_config import log_shutdown

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

    from .audio.player import AudioPlayerPort
    from .hotkey.manager import HotkeyManager
    from .settings import SettingsManager
    from .speech.controller import SpeechController
    from .state import StateManager
    from .tray.tray_app import TrayApp
    from .tray.window import MainWindow
    from .tts.manager import TTSBackendManager
    from .api.server import ApiServer
    from .lifecycle import InstanceIpcServer


CleanupAction = tuple[str, Callable[[], None]]


@dataclass
class ApplicationRuntime:
    """Own all long-lived application services and their lifecycle."""

    qt_app: QApplication
    logger: Logger
    settings_manager: SettingsManager
    state_manager: StateManager
    backend_manager: TTSBackendManager
    audio_player: AudioPlayerPort
    speech_controller: SpeechController
    hotkey_manager: HotkeyManager
    main_window: MainWindow
    tray_app: TrayApp
    api_server: ApiServer
    instance_ipc: InstanceIpcServer | None = None
    _shutdown_complete: bool = field(default=False, init=False, repr=False)

    @property
    def is_shutdown(self) -> bool:
        """Return whether runtime cleanup has already completed."""
        return self._shutdown_complete

    def shutdown(self) -> None:
        """
        Release runtime resources in a deterministic, idempotent order.

        Cleanup continues after an individual failure so one broken resource
        cannot prevent the remaining services from being released.
        """
        if self._shutdown_complete:
            return

        self._shutdown_complete = True

        cleanup_actions: list[CleanupAction] = [
            (
                "single-instance IPC",
                self.instance_ipc.stop if self.instance_ipc is not None else lambda: None,
            ),
            ("API server", self.api_server.stop),
            ("global hotkey", self.hotkey_manager.shutdown),
            ("audio playback", self.audio_player.stop),
            ("tray icon", self.tray_app.tray_icon.hide),
        ]

        for resource_name, cleanup_action in cleanup_actions:
            try:
                cleanup_action()
            except Exception as exc:
                self.logger.warning(
                    "Failed to clean up %s during shutdown: %s",
                    resource_name,
                    exc,
                )

        try:
            log_shutdown(self.logger)
        except Exception as exc:
            self.logger.warning(
                "Failed to write application shutdown log: %s",
                exc,
            )
