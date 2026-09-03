"""Linux global-hotkey adapters for X11 and Wayland.

Wayland sessions use the freedesktop Global Shortcuts portal through the
optional ``dbus-next`` package. X11 sessions use the optional ``python-xlib``
package and register a single key grab on the root window. The application
receives an explicit unsupported error when the current desktop cannot offer
either mechanism; it never reads raw keyboard devices.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import secrets
import sys
import threading
from collections.abc import Callable, Mapping
from typing import Any

from syllavox.hotkey.errors import (
    HotkeyRegistrationError,
    HotkeyUnsupportedPlatformError,
)
from syllavox.hotkey.parser import (
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_WIN,
    parse_hotkey,
)


HotkeyCallback = Callable[[], None]

WAYLAND_PORTAL_BUS = "org.freedesktop.portal.Desktop"
WAYLAND_PORTAL_PATH = "/org/freedesktop/portal/desktop"
WAYLAND_GLOBAL_SHORTCUTS_INTERFACE = (
    "org.freedesktop.portal.GlobalShortcuts"
)
WAYLAND_REQUEST_INTERFACE = "org.freedesktop.portal.Request"
WAYLAND_SESSION_INTERFACE = "org.freedesktop.portal.Session"


def _new_portal_token(prefix: str) -> str:
    """Return a unique token accepted in a D-Bus object-path component."""
    return f"syllavox_{prefix}_{secrets.token_hex(8)}"


def _portal_request_path(unique_name: str, token: str) -> str:
    """Predict the Request handle path defined by the portal specification."""
    sender = unique_name.lstrip(":").replace(".", "_")
    if not sender:
        raise HotkeyRegistrationError(
            "The Wayland session bus did not assign a unique connection name."
        )
    return f"/org/freedesktop/portal/desktop/request/{sender}/{token}"


def _portal_trigger(binding: HotkeyBinding) -> str:
    """Convert Syllavox's shortcut grammar to the XDG shortcut grammar."""
    key_name = binding.display_name.split("+")[-1]
    key_names = {
        "Enter": "Return",
        "Escape": "Escape",
        "Backspace": "BackSpace",
        "PageUp": "Page_Up",
        "PageDown": "Page_Down",
        "Space": "space",
    }
    key = key_names.get(
        key_name,
        key_name.upper() if len(key_name) == 1 else key_name,
    )

    modifier_names: list[str] = []
    if binding.modifiers & MOD_CONTROL:
        modifier_names.append("CTRL")
    if binding.modifiers & MOD_ALT:
        modifier_names.append("ALT")
    if binding.modifiers & MOD_SHIFT:
        modifier_names.append("SHIFT")
    if binding.modifiers & MOD_WIN:
        modifier_names.append("LOGO")

    return "+".join([*modifier_names, key])


def _unwrap_variant(value: Any) -> Any:
    return getattr(value, "value", value)


def _message_name(message: Any) -> str:
    message_type = getattr(message, "message_type", None)
    return str(getattr(message_type, "name", message_type or ""))


class LinuxX11GlobalHotkey:
    """Register one hotkey using X11 root-window key grabs."""

    def __init__(
        self,
        callback: HotkeyCallback,
        *,
        display_factory: Callable[[], Any] | None = None,
        x_module: Any | None = None,
        xk_module: Any | None = None,
    ) -> None:
        self._callback = callback
        self._display_factory = display_factory
        self._x_module = x_module
        self._xk_module = xk_module
        self._display: Any | None = None
        self._root: Any | None = None
        self._x: Any | None = None
        self._binding: HotkeyBinding | None = None
        self._keycode: int | None = None
        self._base_modifiers = 0
        self._ignored_modifiers = 0
        self._stop_event = threading.Event()
        self._event_thread: threading.Thread | None = None

    def register(self, hotkey: str) -> HotkeyBinding:
        self._require_linux()
        binding = parse_hotkey(hotkey)
        self.unregister()

        x_module, xk_module = self._load_xlib()
        display_factory = self._display_factory or x_module.display.Display

        try:
            display = display_factory()
            screen = display.screen()
            root = screen.root
            keysym = _x11_keysym(binding, xk_module)
            keycode = int(display.keysym_to_keycode(keysym))
            if keycode == 0:
                raise HotkeyRegistrationError(
                    f"X11 does not support the hotkey key {binding.display_name!r}."
                )

            base_modifiers = _x11_modifier_mask(binding, x_module)
            ignored_modifiers = int(getattr(x_module, "LockMask", 2)) | int(
                getattr(x_module, "Mod2Mask", 0)
            )
            for lock_mask in _lock_mask_variants(
                int(getattr(x_module, "LockMask", 2)),
                int(getattr(x_module, "Mod2Mask", 0)),
            ):
                root.grab_key(
                    keycode,
                    base_modifiers | lock_mask,
                    False,
                    x_module.GrabModeAsync,
                    x_module.GrabModeAsync,
                )
            display.sync()
        except HotkeyRegistrationError:
            _close_display(display if "display" in locals() else None)
            raise
        except Exception as exc:
            _close_display(display if "display" in locals() else None)
            raise HotkeyRegistrationError(
                "Could not register the global hotkey through X11. It may "
                "already be in use or the X server may have denied the grab."
            ) from exc

        self._display = display
        self._root = root
        self._x = x_module
        self._xk_module = xk_module
        self._binding = binding
        self._keycode = keycode
        self._base_modifiers = base_modifiers
        self._ignored_modifiers = ignored_modifiers
        self._stop_event.clear()
        self._event_thread = threading.Thread(
            target=self._event_loop,
            name="syllavox-linux-x11-hotkey",
            daemon=True,
        )
        self._event_thread.start()
        return binding

    def unregister(self) -> None:
        display = self._display
        root = self._root
        x_module = self._x
        keycode = self._keycode

        self._binding = None
        self._keycode = None
        self._stop_event.set()

        if root is not None and x_module is not None:
            try:
                for lock_mask in _lock_mask_variants(
                    int(getattr(x_module, "LockMask", 2)),
                    int(getattr(x_module, "Mod2Mask", 0)),
                ):
                    root.ungrab_key(
                        keycode or 0,
                        self._base_modifiers | lock_mask,
                    )
                display.sync()
            except Exception:
                pass

        _close_display(display)
        event_thread = self._event_thread
        if event_thread is not None and event_thread is not threading.current_thread():
            event_thread.join(timeout=0.5)

        self._event_thread = None
        self._display = None
        self._root = None
        self._x = None

    def shutdown(self) -> None:
        self.unregister()

    def is_registered(self) -> bool:
        return self._binding is not None and self._display is not None

    def current_hotkey(self) -> str | None:
        return self._binding.display_name if self._binding else None

    def _event_loop(self) -> None:
        display = self._display
        x_module = self._x
        if display is None or x_module is None:
            return

        try:
            while not self._stop_event.is_set():
                event = display.next_event()
                if self._stop_event.is_set():
                    break
                if getattr(event, "type", None) != x_module.KeyPress:
                    continue
                if getattr(event, "detail", None) != self._keycode:
                    continue

                state = int(getattr(event, "state", 0)) & ~self._ignored_modifiers
                if state != self._base_modifiers:
                    continue
                try:
                    self._callback()
                except Exception:
                    continue
        except Exception:
            # Closing the display is the normal way to wake the blocking
            # next_event call during unregister().
            return

    def _load_xlib(self) -> tuple[Any, Any]:
        if self._x_module is not None and self._xk_module is not None:
            return self._x_module, self._xk_module

        try:
            from Xlib import X, XK, display
        except ImportError as exc:
            raise HotkeyUnsupportedPlatformError(
                "Linux X11 global hotkeys require the optional 'linux' "
                "dependency (python-xlib)."
            ) from exc

        self._x_module = X
        self._x_module.display = display
        self._xk_module = XK
        return X, XK

    @staticmethod
    def _require_linux() -> None:
        if not sys.platform.startswith("linux"):
            raise HotkeyUnsupportedPlatformError(
                "Linux global hotkeys are available only on Linux."
            )


class LinuxWaylandGlobalHotkey:
    """Register a hotkey through the XDG Global Shortcuts portal."""

    def __init__(
        self,
        callback: HotkeyCallback,
        *,
        bus_factory: Callable[[], Any] | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self._callback = callback
        self._bus_factory = bus_factory
        self._timeout_seconds = timeout_seconds
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="syllavox-linux-wayland-hotkey",
            daemon=True,
        )
        self._thread.start()
        self._loop_ready.wait(timeout=self._timeout_seconds)
        self._bus: Any | None = None
        self._session_handle: str | None = None
        self._shortcut_id: str | None = None
        self._message_handler: Callable[[Any], None] | None = None
        self._binding: HotkeyBinding | None = None

    def register(self, hotkey: str) -> HotkeyBinding:
        self._require_linux()
        binding = parse_hotkey(hotkey)
        self.unregister()
        self._run_sync(self._register_async(binding))
        self._binding = binding
        return binding

    def unregister(self) -> None:
        if self._loop is None:
            self._binding = None
            return
        try:
            self._run_sync(self._close_async())
        except Exception:
            pass
        self._binding = None

    def shutdown(self) -> None:
        self.unregister()
        loop = self._loop
        if loop is not None:
            loop.call_soon_threadsafe(loop.stop)
        if self._thread is not threading.current_thread():
            self._thread.join(timeout=1.0)
        self._loop = None

    def is_registered(self) -> bool:
        return self._binding is not None and self._session_handle is not None

    def current_hotkey(self) -> str | None:
        return self._binding.display_name if self._binding else None

    async def _register_async(self, binding: HotkeyBinding) -> None:
        message, message_type, variant = _load_dbus_types()
        bus = self._bus_factory() if self._bus_factory else _default_bus_factory()
        connected = bus.connect()
        if inspect.isawaitable(connected):
            await connected
        self._bus = bus

        create_token = _new_portal_token("create")
        session_token = _new_portal_token("session")
        create_response = await self._call_request(
            message,
            message_type,
            request_token=create_token,
            interface=WAYLAND_GLOBAL_SHORTCUTS_INTERFACE,
            member="CreateSession",
            signature="a{sv}",
            body=[
                {
                    "handle_token": variant("s", create_token),
                    "session_handle_token": variant("s", session_token),
                }
            ],
        )
        session_handle = _unwrap_variant(
            _unwrap_variant(create_response.get("session_handle"))
        )
        if not session_handle:
            raise HotkeyRegistrationError(
                "The Wayland Global Shortcuts portal did not create a session."
            )
        self._session_handle = str(session_handle)

        self._message_handler = self._handle_portal_message
        bus.add_message_handler(self._message_handler)
        bind_token = _new_portal_token("bind")
        bind_response = await self._call_request(
            message,
            message_type,
            request_token=bind_token,
            interface=WAYLAND_GLOBAL_SHORTCUTS_INTERFACE,
            member="BindShortcuts",
            signature="oa(sa{sv})sa{sv}",
            body=[
                self._session_handle,
                [
                    (
                        "read_text",
                        {
                            "description": variant("s", "Read clipboard text"),
                            "preferred_trigger": variant(
                                "s",
                                _portal_trigger(binding),
                            ),
                        },
                    )
                ],
                "",
                {"handle_token": variant("s", bind_token)},
            ],
        )
        shortcuts = _unwrap_variant(bind_response.get("shortcuts", []))
        if not shortcuts:
            raise HotkeyRegistrationError(
                "The Wayland desktop did not approve the configured global "
                "hotkey."
            )
        self._shortcut_id = "read_text"

    async def _close_async(self) -> None:
        message, message_type, _variant = _load_dbus_types()
        bus = self._bus
        session_handle = self._session_handle
        handler = self._message_handler
        self._session_handle = None
        self._shortcut_id = None
        self._message_handler = None

        if bus is None:
            return
        if handler is not None:
            try:
                bus.remove_message_handler(handler)
            except Exception:
                pass
        if session_handle:
            try:
                await self._call(
                    message,
                    message_type,
                    destination=WAYLAND_PORTAL_BUS,
                    path=session_handle,
                    interface=WAYLAND_SESSION_INTERFACE,
                    member="Close",
                    signature="",
                    body=[],
                )
            except Exception:
                pass
        disconnect = getattr(bus, "disconnect", None)
        if callable(disconnect):
            result = disconnect()
            if inspect.isawaitable(result):
                await result
        self._bus = None

    async def _call(
        self,
        message_type: Any,
        dbus_message_type: Any,
        *,
        interface: str,
        member: str,
        signature: str,
        body: list[Any],
        destination: str = WAYLAND_PORTAL_BUS,
        path: str = WAYLAND_PORTAL_PATH,
    ) -> Any:
        del dbus_message_type
        bus = self._bus
        if bus is None:
            raise HotkeyRegistrationError(
                "The Wayland session bus is not connected."
            )
        reply = await bus.call(
            message_type(
                destination=destination,
                path=path,
                interface=interface,
                member=member,
                signature=signature,
                body=body,
            )
        )
        if _message_name(reply) == "ERROR":
            details = str(reply.body[0]) if reply.body else "unknown portal error"
            raise HotkeyRegistrationError(
                f"Wayland global hotkey registration failed: {details}"
            )
        return reply

    async def _call_request(
        self,
        message_type: Any,
        dbus_message_type: Any,
        *,
        request_token: str,
        interface: str,
        member: str,
        signature: str,
        body: list[Any],
    ) -> dict[str, Any]:
        """Subscribe for a portal response before issuing the method call."""
        bus = self._bus
        if bus is None:
            raise HotkeyRegistrationError(
                "The Wayland session bus is not connected."
            )
        unique_name = str(getattr(bus, "unique_name", "") or "")
        expected_path = _portal_request_path(unique_name, request_token)
        request_paths = {expected_path}
        loop = asyncio.get_running_loop()
        response_future: asyncio.Future[tuple[int, dict[str, Any]]] = (
            loop.create_future()
        )

        def handler(message: Any) -> None:
            if (
                _message_name(message) == "SIGNAL"
                and getattr(message, "path", None) in request_paths
                and getattr(message, "interface", None) == WAYLAND_REQUEST_INTERFACE
                and getattr(message, "member", None) == "Response"
            ):
                if not response_future.done():
                    response_future.set_result(
                        (int(message.body[0]), message.body[1])
                    )

        bus.add_message_handler(handler)
        try:
            reply = await self._call(
                message_type,
                dbus_message_type,
                interface=interface,
                member=member,
                signature=signature,
                body=body,
            )
            if not reply.body:
                raise HotkeyRegistrationError(
                    "The Wayland portal returned no request handle."
                )
            request_paths.add(str(reply.body[0]))
            response_code, results = await asyncio.wait_for(
                response_future,
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise HotkeyRegistrationError(
                "The Wayland desktop did not respond to the global hotkey "
                "request."
            ) from exc
        finally:
            try:
                bus.remove_message_handler(handler)
            except Exception:
                pass

        if response_code != 0:
            raise HotkeyRegistrationError(
                "The Wayland desktop rejected the global hotkey request."
            )
        return {
            str(key): _unwrap_variant(value)
            for key, value in (results or {}).items()
        }

    def _handle_portal_message(self, message: Any) -> None:
        if (
            _message_name(message) != "SIGNAL"
            or getattr(message, "interface", None)
            != WAYLAND_GLOBAL_SHORTCUTS_INTERFACE
            or getattr(message, "member", None) != "Activated"
            or not message.body
            or message.body[0] != self._session_handle
            or message.body[1] != self._shortcut_id
        ):
            return
        try:
            self._callback()
        except Exception:
            return

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._loop_ready.set()
        loop.run_forever()
        loop.close()

    def _run_sync(self, coroutine: Any) -> Any:
        loop = self._loop
        if loop is None:
            raise HotkeyUnsupportedPlatformError(
                "The Wayland global shortcut event loop is unavailable."
            )
        future = asyncio.run_coroutine_threadsafe(coroutine, loop)
        try:
            return future.result(timeout=self._timeout_seconds)
        except TimeoutError as exc:
            future.cancel()
            raise HotkeyRegistrationError(
                "Timed out while registering the Wayland global hotkey."
            ) from exc

    @staticmethod
    def _require_linux() -> None:
        if not sys.platform.startswith("linux"):
            raise HotkeyUnsupportedPlatformError(
                "Linux global hotkeys are available only on Linux."
            )


class LinuxGlobalHotkey:
    """Choose the current Linux session's safe global-hotkey mechanism."""

    def __init__(
        self,
        callback: HotkeyCallback,
        *,
        environment: Mapping[str, str] | None = None,
        wayland_factory: Callable[[HotkeyCallback], Any] | None = None,
        x11_factory: Callable[[HotkeyCallback], Any] | None = None,
    ) -> None:
        self._callback = callback
        self._environment = dict(environment or os.environ)
        self._wayland_factory = wayland_factory
        self._x11_factory = x11_factory
        self._backend: Any | None = None

    def register(self, hotkey: str) -> HotkeyBinding:
        if not sys.platform.startswith("linux"):
            raise HotkeyUnsupportedPlatformError(
                "Linux global hotkeys are available only on Linux."
            )

        backend = self._create_backend()
        self.unregister()
        try:
            binding = backend.register(hotkey)
        except Exception:
            backend.shutdown()
            raise
        self._backend = backend
        return binding

    def unregister(self) -> None:
        if self._backend is not None:
            self._backend.unregister()
            self._backend = None

    def shutdown(self) -> None:
        if self._backend is not None:
            self._backend.shutdown()
            self._backend = None

    def is_registered(self) -> bool:
        return bool(self._backend and self._backend.is_registered())

    def current_hotkey(self) -> str | None:
        if self._backend is None:
            return None
        return self._backend.current_hotkey()

    def _create_backend(self) -> Any:
        session_type = self._environment.get("XDG_SESSION_TYPE", "").lower()
        has_wayland = bool(self._environment.get("WAYLAND_DISPLAY"))
        has_x11 = bool(self._environment.get("DISPLAY"))

        if session_type == "wayland" or (not session_type and has_wayland):
            factory = self._wayland_factory or LinuxWaylandGlobalHotkey
            return factory(self._callback)

        if session_type == "x11" or has_x11:
            factory = self._x11_factory or LinuxX11GlobalHotkey
            return factory(self._callback)

        raise HotkeyUnsupportedPlatformError(
            "Linux global hotkeys require an X11 DISPLAY or a Wayland "
            "session with the Global Shortcuts portal."
        )


def _load_dbus_types() -> tuple[Any, Any, Any]:
    try:
        from dbus_next import Message, MessageType, Variant
    except ImportError as exc:
        raise HotkeyUnsupportedPlatformError(
            "Linux Wayland global hotkeys require the optional 'linux' "
            "dependency (dbus-next)."
        ) from exc
    return Message, MessageType, Variant


def _default_bus_factory() -> Any:
    from dbus_next import BusType
    from dbus_next.aio import MessageBus

    return MessageBus(bus_type=BusType.SESSION)


def _x11_keysym(binding: HotkeyBinding, xk_module: Any) -> int:
    key_name = binding.display_name.split("+")[-1]
    names = {
        "Enter": "Return",
        "Escape": "Escape",
        "Backspace": "BackSpace",
        "PageUp": "Prior",
        "PageDown": "Next",
        "Space": "space",
    }
    return int(
        xk_module.string_to_keysym(
            names.get(
                key_name,
                key_name.lower() if len(key_name) == 1 else key_name,
            )
        )
    )


def _x11_modifier_mask(binding: HotkeyBinding, x_module: Any) -> int:
    mask = 0
    if binding.modifiers & MOD_CONTROL:
        mask |= int(x_module.ControlMask)
    if binding.modifiers & MOD_ALT:
        mask |= int(x_module.Mod1Mask)
    if binding.modifiers & MOD_SHIFT:
        mask |= int(x_module.ShiftMask)
    if binding.modifiers & MOD_WIN:
        mask |= int(x_module.Mod4Mask)
    return mask


def _lock_mask_variants(lock_mask: int, num_lock_mask: int) -> tuple[int, ...]:
    values = {0, lock_mask, num_lock_mask, lock_mask | num_lock_mask}
    return tuple(sorted(values))


def _close_display(display: Any | None) -> None:
    if display is None:
        return
    try:
        display.close()
    except Exception:
        return


__all__ = [
    "LinuxGlobalHotkey",
    "LinuxWaylandGlobalHotkey",
    "LinuxX11GlobalHotkey",
]
