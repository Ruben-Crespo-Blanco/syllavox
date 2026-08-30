"""Application composition root and Qt event-loop bootstrap."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from logging import Logger

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from .api.context import ApiContext
from .api.server import ApiServer
from .audio.player import (
    AudioPlayer,
    AudioPlayerPort,
    DEFAULT_PLAYBACK_RATE,
    DEFAULT_PLAYBACK_VOLUME,
    MAX_PLAYBACK_RATE,
    MIN_PLAYBACK_RATE,
    normalize_playback_value,
)
from .audio.qt_bridge import QtAudioBridge
from .constants import (
    DEFAULT_MAX_TEXT_LENGTH,
    DEFAULT_READ_HOTKEY,
    DEFAULT_TTS_BACKEND,
    MAX_CONFIGURABLE_TEXT_LENGTH,
    PRODUCT_NAME,
    SHERPA_ONNX_TTS_BACKEND,
    WINDOWS_SAPI_TTS_BACKEND,
)
from .hotkey.errors import (
    HotkeyActionError,
    HotkeyRegistrationError,
    HotkeyUnsupportedPlatformError,
)
from .hotkey.manager import HotkeyAction, HotkeyManager
from .logging_config import configure_logging, get_logger, log_startup
from .lifecycle import (
    InstanceIpcServer,
    SingleInstanceGuard,
    request_existing_instance_focus,
)
from .paths import ensure_app_directories
from .request_ids import new_request_id
from .runtime import ApplicationRuntime
from .settings import SettingsManager
from .startup import (
    StartupRegistrationError,
    set_startup_enabled,
    sync_startup_registration,
)
from .speech.controller import SpeechController
from .state import StateManager
from .tray.tray_app import TrayApp
from .tray.theme import apply_app_theme
from .tray.window import MainWindow
from .tts.manager import TTSBackendManager
from .tts.backend_registry import create_backend, normalize_backend_id
from .tts.catalog import (
    PiperVoiceCatalog,
    SherpaVoiceCatalog,
    SystemVoiceCatalog,
)
from .tts.paths import cleanup_temporary_audio_files, ensure_tts_directories
from .tts.paths import get_piper_models_dir, get_sherpa_onnx_models_dir


@dataclass(frozen=True)
class _StartupContext:
    """Services prepared before the rest of the application is composed."""

    qt_app: QApplication
    logger: Logger
    settings_manager: SettingsManager
    state_manager: StateManager


@dataclass(frozen=True)
class _SpeechServices:
    """Audio and speech services shared by the UI, API, and hotkey paths."""

    audio_player: AudioPlayer
    audio_bridge: QtAudioBridge
    backend_manager: TTSBackendManager
    speech_controller: SpeechController


@dataclass(frozen=True)
class _UiServices:
    """User-interface services assembled around the shared speech services."""

    main_window: MainWindow
    tray_app: TrayApp
    instance_ipc: InstanceIpcServer


def _load_settings() -> tuple[SettingsManager, object]:
    """Create the settings manager, load settings, and return load metadata."""
    settings_manager = SettingsManager()
    settings_result = settings_manager.load()

    return settings_manager, settings_result


def _log_settings_result(logger, settings_manager: SettingsManager, result) -> None:
    """Log first-run, repair, and recovery information for loaded settings."""
    if result.created_default_file:
        logger.info("Settings file did not exist; created defaults")

    if result.repaired_missing_keys:
        logger.warning("Settings file had missing keys; repaired with defaults")

    if result.recovered_from_corruption:
        logger.warning(
            "Settings file was corrupt; backed up to %s and regenerated defaults",
            result.backup_path,
        )

    logger.info(
        "Settings loaded. created_default=%s repaired=%s recovered=%s",
        result.created_default_file,
        result.repaired_missing_keys,
        result.recovered_from_corruption,
    )


def _sync_startup_registration(
    settings_manager: SettingsManager,
    logger: Logger,
) -> None:
    """Apply the persisted startup preference without blocking application startup."""
    ui_settings = settings_manager.settings.get("ui", {})
    enabled = bool(ui_settings.get("run_on_startup", False))

    try:
        sync_startup_registration(enabled)
    except StartupRegistrationError as exc:
        logger.warning("Could not reconcile Windows startup registration: %s", exc)


def _create_audio_player() -> AudioPlayer:
    """Create the Qt-owned audio player before speech services are composed."""
    return AudioPlayer()


def _create_speech_services(
    settings_manager: SettingsManager,
    state_manager: StateManager,
    audio_player: AudioPlayerPort,
    logger,
) -> tuple[TTSBackendManager, SpeechController]:
    """Create the configured backend, manager, and shared speech service."""
    tts_settings = settings_manager.settings.get("tts", {})
    configured_backend = normalize_backend_id(
        tts_settings.get("backend", DEFAULT_TTS_BACKEND)
    )

    try:
        backend = create_backend(configured_backend)
    except Exception as exc:
        logger.warning(
            "TTS backend %r could not be created; falling back to Piper: %s",
            configured_backend,
            exc,
        )
        configured_backend = DEFAULT_TTS_BACKEND
        backend = create_backend(DEFAULT_TTS_BACKEND)

    if configured_backend == SHERPA_ONNX_TTS_BACKEND:
        logger.info(
            "Sherpa-ONNX backend selected from settings; "
            "Piper remains the default backend."
        )
    elif configured_backend == WINDOWS_SAPI_TTS_BACKEND:
        logger.info(
            "Windows SAPI backend selected from settings; system voices "
            "will be enumerated from Windows."
        )

    configured_max_text_length = int(
        tts_settings.get("max_text_length", DEFAULT_MAX_TEXT_LENGTH)
    )
    max_text_length = min(
        configured_max_text_length,
        MAX_CONFIGURABLE_TEXT_LENGTH,
    )
    default_voice_id = tts_settings.get("voice_id")
    playback_settings = settings_manager.settings.get("playback", {})

    volume = normalize_playback_value(
        playback_settings.get("volume", DEFAULT_PLAYBACK_VOLUME),
        DEFAULT_PLAYBACK_VOLUME,
        0.0,
        1.0,
    )
    rate = normalize_playback_value(
        playback_settings.get("rate", DEFAULT_PLAYBACK_RATE),
        DEFAULT_PLAYBACK_RATE,
        MIN_PLAYBACK_RATE,
        MAX_PLAYBACK_RATE,
    )

    audio_player.set_volume(volume)
    audio_player.set_playback_rate(rate)

    backend_manager = TTSBackendManager(
        backend=backend,
        max_text_length=max_text_length,
        default_voice_id=(
            default_voice_id
            if isinstance(default_voice_id, str)
            else None
        ),
    )

    speech_controller = SpeechController(
        state_manager=state_manager,
        backend_manager=backend_manager,
        audio_player=audio_player,
        logger=logger,
    )

    return backend_manager, speech_controller


def _create_hotkey_manager(
    qt_app: QApplication,
    tray_app: TrayApp,
    speech_controller: SpeechController,
    logger,
) -> HotkeyManager:
    """Create hotkey actions after all of their service dependencies exist."""
    def speak_clipboard() -> None:
        text = qt_app.clipboard().text().strip()

        if not text:
            logger.warning(
                "Global hotkey ignored because the clipboard contains no text"
            )
            return

        request_id = new_request_id("hotkey")

        try:
            speech_controller.speak(
                text=text,
                request_id=request_id,
                voice_id=None,
            )

        except Exception as exc:
            logger.exception(
                "Clipboard speech failed: request_id=%s",
                request_id,
            )

            raise HotkeyActionError(
                "Clipboard text could not be spoken."
            ) from exc

    def open_main_window() -> None:
        try:
            tray_app.open_window()

        except Exception as exc:
            logger.exception("Failed to open window from global hotkey")

            raise HotkeyActionError(
                "Application window could not be opened."
            ) from exc

    return HotkeyManager(
        logger=logger,
        speak_clipboard_callback=speak_clipboard,
        open_window_callback=open_main_window,
    )


def _prepare_startup_context() -> _StartupContext:
    """Prepare process-wide services and the Qt application object."""
    ensure_app_directories()
    ensure_tts_directories()

    logger = configure_logging()
    log_startup(logger)

    removed_audio_count, failed_audio_count = cleanup_temporary_audio_files()

    if removed_audio_count:
        logger.info(
            "Removed %s leftover temporary audio file(s) from a previous run",
            removed_audio_count,
        )

    if failed_audio_count:
        logger.warning(
            "Could not remove %s leftover temporary audio file(s)",
            failed_audio_count,
        )

    settings_manager, settings_result = _load_settings()
    _log_settings_result(logger, settings_manager, settings_result)
    _sync_startup_registration(settings_manager, logger)

    state_manager = StateManager()

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(PRODUCT_NAME)
    qt_app.setQuitOnLastWindowClosed(False)
    apply_app_theme(qt_app)

    return _StartupContext(
        qt_app=qt_app,
        logger=logger,
        settings_manager=settings_manager,
        state_manager=state_manager,
    )


def _create_speech_context(context: _StartupContext) -> _SpeechServices:
    """Create the audio, backend, and speech services."""
    audio_player = _create_audio_player()
    audio_bridge = QtAudioBridge(audio_player)
    backend_manager, speech_controller = _create_speech_services(
        settings_manager=context.settings_manager,
        state_manager=context.state_manager,
        audio_player=audio_bridge,
        logger=context.logger,
    )
    audio_player.set_finished_callback(
        speech_controller.handle_playback_finished
    )

    return _SpeechServices(
        audio_player=audio_player,
        audio_bridge=audio_bridge,
        backend_manager=backend_manager,
        speech_controller=speech_controller,
    )


def _create_ui_services(
    context: _StartupContext,
    speech_services: _SpeechServices,
) -> _UiServices:
    """Create the main window, tray integration, and focus IPC endpoint."""
    backend_name = speech_services.backend_manager.backend_name()
    if backend_name == WINDOWS_SAPI_TTS_BACKEND:
        voice_catalog = SystemVoiceCatalog()
    elif backend_name == "sherpa-onnx":
        voice_catalog = SherpaVoiceCatalog(
            backend=speech_services.backend_manager.active_backend,
            models_dir=get_sherpa_onnx_models_dir(),
        )
    else:
        voice_catalog = PiperVoiceCatalog(
            models_dir=get_piper_models_dir()
        )

    main_window = MainWindow(
        state_manager=context.state_manager,
        settings_manager=context.settings_manager,
        backend_manager=speech_services.backend_manager,
        speech_controller=speech_services.speech_controller,
        voice_catalog=voice_catalog,
    )

    tray_app = TrayApp(
        qt_app=context.qt_app,
        main_window=main_window,
        state_manager=context.state_manager,
    )

    instance_ipc = InstanceIpcServer()
    instance_ipc.show_requested.connect(tray_app.open_window)

    try:
        instance_ipc.start()
    except Exception as exc:
        context.logger.warning(
            "Single-instance focus channel could not start: %s",
            exc,
        )

    return _UiServices(
        main_window=main_window,
        tray_app=tray_app,
        instance_ipc=instance_ipc,
    )


def _configure_hotkey(runtime: ApplicationRuntime) -> None:
    """Apply configured hotkey action and attempt registration."""
    logger = runtime.logger
    hotkey_settings = runtime.settings_manager.settings.get("hotkey", {})

    hotkey_enabled = bool(hotkey_settings.get("enabled", True))
    hotkey_text = str(hotkey_settings.get("key", DEFAULT_READ_HOTKEY))
    hotkey_action = str(
        hotkey_settings.get(
            "action",
            HotkeyAction.SPEAK_CLIPBOARD.value,
        )
    )

    try:
        runtime.hotkey_manager.set_action(hotkey_action)

    except HotkeyActionError as exc:
        logger.warning(
            "Invalid configured hotkey action %r: %s. "
            "Falling back to speak_clipboard.",
            hotkey_action,
            exc,
        )
        runtime.hotkey_manager.set_action(HotkeyAction.SPEAK_CLIPBOARD)

    if not hotkey_enabled:
        runtime.hotkey_manager.set_disabled()
        runtime.main_window.update_hotkey_status(
            runtime.hotkey_manager.status()
        )
        logger.info("Global hotkey disabled in settings")
        return

    try:
        registered_hotkey = runtime.hotkey_manager.register(hotkey_text)

        logger.info(
            "Global hotkey ready: key=%s action=%s",
            registered_hotkey,
            runtime.hotkey_manager.current_action().value,
        )
        runtime.main_window.update_hotkey_status(
            runtime.hotkey_manager.status()
        )

    except HotkeyRegistrationError as exc:
        runtime.main_window.update_hotkey_status(
            runtime.hotkey_manager.status()
        )
        logger.warning(
            "Global hotkey registration failed. "
            "The application will continue without a global hotkey: %s",
            exc,
        )
        runtime.tray_app.show_warning(
            "Global hotkey unavailable",
            f"{exc}\n\nThe application will continue normally.",
        )

    except HotkeyUnsupportedPlatformError as exc:
        runtime.main_window.update_hotkey_status(
            runtime.hotkey_manager.status()
        )
        logger.warning(
            "Global hotkey is unavailable on this platform: %s",
            exc,
        )
        runtime.tray_app.show_warning(
            "Global hotkey unavailable",
            f"{exc}\n\nThe application will continue normally.",
        )


def _reconfigure_hotkey(runtime: ApplicationRuntime, hotkey: str) -> None:
    """Apply a new shortcut from the running Settings panel."""
    try:
        runtime.hotkey_manager.reconfigure(hotkey)
    finally:
        runtime.main_window.update_hotkey_status(
            runtime.hotkey_manager.status()
        )


def _create_runtime() -> ApplicationRuntime:
    """Construct the complete application runtime without starting it."""
    context = _prepare_startup_context()
    speech_services = _create_speech_context(context)
    ui_services = _create_ui_services(context, speech_services)

    hotkey_manager = _create_hotkey_manager(
        qt_app=context.qt_app,
        tray_app=ui_services.tray_app,
        speech_controller=speech_services.speech_controller,
        logger=context.logger,
    )

    api_context = ApiContext(
        state_manager=context.state_manager,
        backend_manager=speech_services.backend_manager,
        speech_controller=speech_services.speech_controller,
        logger=context.logger,
    )

    api_server = ApiServer(context=api_context)

    runtime = ApplicationRuntime(
        qt_app=context.qt_app,
        logger=context.logger,
        settings_manager=context.settings_manager,
        state_manager=context.state_manager,
        backend_manager=speech_services.backend_manager,
        audio_player=speech_services.audio_bridge,
        speech_controller=speech_services.speech_controller,
        hotkey_manager=hotkey_manager,
        main_window=ui_services.main_window,
        tray_app=ui_services.tray_app,
        api_server=api_server,
        instance_ipc=ui_services.instance_ipc,
    )

    runtime.main_window.set_hotkey_reconfigure_callback(
        lambda hotkey: _reconfigure_hotkey(runtime, hotkey)
    )
    runtime.main_window.set_startup_reconfigure_callback(set_startup_enabled)
    return runtime


def bootstrap() -> int:
    """Construct the application, run Qt, and always release the runtime."""
    instance_guard = SingleInstanceGuard()

    if not instance_guard.acquire():
        request_existing_instance_focus()
        return 0

    runtime: ApplicationRuntime | None = None

    try:
        runtime = _create_runtime()
        runtime.qt_app.aboutToQuit.connect(runtime.shutdown)

        _configure_hotkey(runtime)
        runtime.api_server.start()

        runtime.state_manager.mark_ready()
        runtime.logger.info(
            "Application reached state: %s",
            runtime.state_manager.state.value,
        )
        runtime.tray_app.refresh()

        tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        start_minimized = bool(
            runtime.settings_manager.settings.get("ui", {}).get(
                "start_minimized_to_tray",
                True,
            )
        )
        if not tray_available or not start_minimized:
            runtime.tray_app.open_window()

        if not tray_available:
            QMessageBox.warning(
                runtime.main_window,
                PRODUCT_NAME,
                "System tray is not available on this system.",
            )
            runtime.logger.warning("System tray is not available.")
        else:
            runtime.tray_app.show_information(
                PRODUCT_NAME,
                "Ready and running in the system tray.",
            )

        return runtime.qt_app.exec()

    finally:
        if runtime is not None:
            runtime.shutdown()
        instance_guard.release()


__all__ = ["ApplicationRuntime", "bootstrap"]
