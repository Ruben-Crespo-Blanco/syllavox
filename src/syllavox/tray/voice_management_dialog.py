"""Dialog controller for loading, unloading, and deleting voices."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtWidgets import QDialog, QMessageBox, QVBoxLayout

from syllavox.state import AppState, StateManager, StateSnapshot
from syllavox.tray.background_worker import BackgroundWorkerMixin
from syllavox.tray.voice_management_view import VoiceManagementView
from syllavox.tts.base import VoiceInfo
from syllavox.tts.errors import TTSBackendError
from syllavox.tts.manager import TTSBackendManager


VoicesChangedCallback = Callable[[], None]
CurrentVoiceCallback = Callable[[], str | None]


class VoiceManagementDialog(BackgroundWorkerMixin, QDialog):
    """Coordinate installed-voice operations and their presentation."""

    def __init__(
        self,
        catalog: object,
        backend_manager: TTSBackendManager,
        state_manager: StateManager,
        voices: list[VoiceInfo],
        current_voice_callback: CurrentVoiceCallback,
        on_voices_changed: VoicesChangedCallback,
        logger: logging.Logger,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._catalog = catalog
        self._backend_manager = backend_manager
        self._state_manager = state_manager
        self._voices = list(voices)
        self._current_voice_callback = current_voice_callback
        self._on_voices_changed = on_voices_changed
        self._logger = logger
        self._initialize_worker(self._on_worker_result)

        self.setWindowTitle("Manage installed voices")
        self.setMinimumSize(760, 460)

        self._view = VoiceManagementView()
        self._tree = self._view.tree
        self._status_label = self._view.status_label
        self._load_button = self._view.load_button
        self._unload_button = self._view.unload_button
        self._delete_button = self._view.delete_button
        self._remove_resources_button = self._view.remove_resources_button
        self._close_button = self._view.close_button

        self._supports_voice_deletion = bool(
            getattr(catalog, "supports_voice_deletion", True)
        )
        self._supports_resource_cleanup = bool(
            getattr(catalog, "supports_resource_cleanup", True)
        )
        self._view.selection_changed.connect(self._current_item_changed)
        self._view.load_requested.connect(self._load_selected)
        self._view.unload_requested.connect(self._unload_selected)
        self._view.delete_requested.connect(self._delete_selected)
        self._view.remove_resources_requested.connect(
            self._remove_unused_resources
        )
        self._view.close_requested.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(self._view)
        self.setLayout(layout)

        self._state_manager.add_listener(self._on_state_changed)
        self._populate_tree()
        self._set_status("Select an installed voice.")

    def closeEvent(self, event) -> None:
        if self._is_worker_running():
            self._set_status("Wait for the current voice operation to finish.")
            event.ignore()
            return

        self._state_manager.remove_listener(self._on_state_changed)
        super().closeEvent(event)

    def _populate_tree(self) -> None:
        self._view.populate(
            self._voices,
            self._catalog.voice_model_size,
            self._backend_manager.is_voice_loaded,
        )
        self._refresh_controls()
        self._refresh_resource_button()

    def _selected_voice_id(self) -> str | None:
        return self._view.selected_voice_id()

    def _current_item_changed(self, *args: object) -> None:
        del args
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        voice_id = self._selected_voice_id()
        busy = self._is_worker_running()
        active_speech = self._state_manager.state in {
            AppState.SPEAKING,
            AppState.PAUSED,
        }

        can_modify = voice_id is not None and not busy and not active_speech
        voice_loaded = (
            self._backend_manager.is_voice_loaded(voice_id)
            if can_modify
            else False
        )
        self._view.set_controls(
            load_enabled=can_modify and not voice_loaded,
            unload_enabled=can_modify and voice_loaded,
            delete_enabled=can_modify and self._supports_voice_deletion,
            close_enabled=not busy,
        )

    def _refresh_resource_button(self) -> None:
        busy = self._is_worker_running()
        can_remove = (
            not busy
            and self._supports_resource_cleanup
            and self._state_manager.state not in {
                AppState.SPEAKING,
                AppState.PAUSED,
            }
            and self._catalog.g2pw_size() > 0
            and not self._catalog.has_installed_pinyin_voice()
        )
        self._view.set_remove_resources_enabled(can_remove)

    def _load_selected(self) -> None:
        voice_id = self._selected_voice_id()
        if not self._can_start_operation(voice_id):
            return

        self._start_operation(
            "Loading voice…",
            lambda: self._backend_manager.load_voice(voice_id),
        )

    def _unload_selected(self) -> None:
        voice_id = self._selected_voice_id()
        if not self._can_start_operation(voice_id):
            return

        self._start_operation(
            "Unloading voice…",
            lambda: self._backend_manager.unload_voice(voice_id),
        )

    def _delete_selected(self) -> None:
        if not self._supports_voice_deletion:
            self._set_status(
                "Deleting model resources is not supported by this backend."
            )
            return

        voice_id = self._selected_voice_id()
        if not self._can_start_operation(voice_id):
            return

        current_voice_id = self._current_voice_callback()
        affected_voice_ids = self._affected_voice_ids(voice_id)
        remaining_voice_count = sum(
            voice.voice_id not in affected_voice_ids for voice in self._voices
        )

        deletion_description = getattr(
            self._catalog,
            "deletion_description",
            None,
        )
        if callable(deletion_description):
            details = deletion_description(voice_id)
        else:
            details = (
                "This removes its Piper model and configuration files "
                "from disk."
            )
        message = f"Delete {voice_id}?\n\n{details}"
        if current_voice_id in affected_voice_ids and remaining_voice_count:
            message += (
                "\n\nThe current voice will be replaced by another installed voice."
            )
        elif current_voice_id in affected_voice_ids:
            message += "\n\nThis will leave the application with no installed voices."

        answer = QMessageBox.question(
            self,
            "Delete voice",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        remaining_voice_ids = [
            voice.voice_id
            for voice in self._voices
            if voice.voice_id not in affected_voice_ids
        ]
        replacement_voice_id = (
            remaining_voice_ids[0] if remaining_voice_ids else None
        )

        def delete_voice() -> int:
            for affected_voice_id in affected_voice_ids:
                if self._backend_manager.is_voice_loaded(affected_voice_id):
                    self._backend_manager.unload_voice(affected_voice_id)
            removed_size = self._catalog.delete_voice_files(voice_id)
            if self._backend_manager.default_voice_id in affected_voice_ids:
                self._backend_manager.set_default_voice_id(
                    replacement_voice_id
                )
            return removed_size

        self._start_operation("Deleting voice…", delete_voice)

    def _remove_unused_resources(self) -> None:
        answer = QMessageBox.question(
            self,
            "Remove unused language data",
            "Remove the unused Chinese g2pW phonemization resource?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._start_operation(
            "Removing unused language data…",
            self._catalog.delete_unused_g2pw,
        )

    def _affected_voice_ids(self, voice_id: str) -> set[str]:
        voice_ids = [voice.voice_id for voice in self._voices]
        voice_ids_for_resource = getattr(
            self._catalog,
            "voice_ids_for_resource",
            None,
        )
        if callable(voice_ids_for_resource):
            return set(voice_ids_for_resource(voice_id, voice_ids))
        return {voice_id}

    def _can_start_operation(self, voice_id: str | None) -> bool:
        if voice_id is None:
            return False

        if self._state_manager.state in {AppState.SPEAKING, AppState.PAUSED}:
            self._set_status(
                "Wait until playback has finished before changing voice files."
            )
            return False

        return not self._is_worker_running()

    def _start_operation(
        self,
        busy_message: str,
        operation: Callable[[], object],
    ) -> None:
        self._set_status(busy_message)
        self._refresh_controls()

        self._start_worker(operation)
        self._refresh_controls()

    def _on_worker_result(self, result: tuple[str, object]) -> None:
        self._worker = None
        operation, payload = result

        if operation == "error":
            self._logger.warning(
                "Voice resource operation failed: %s",
                payload,
            )
            self._set_status(str(payload))
            self._refresh_controls()
            self._refresh_resource_button()
            return

        self._on_voices_changed()
        self._refresh_voices_from_backend()
        self._set_status("Voice resources updated.")

    def _refresh_voices_from_backend(self) -> None:
        try:
            self._voices = self._backend_manager.list_voices()
        except TTSBackendError:
            self._voices = []

        self._populate_tree()

    def _on_state_changed(self, snapshot: StateSnapshot) -> None:
        del snapshot
        self._refresh_controls()

    def _set_status(self, message: str) -> None:
        self._view.set_status(message)


__all__ = ["VoiceManagementDialog"]
