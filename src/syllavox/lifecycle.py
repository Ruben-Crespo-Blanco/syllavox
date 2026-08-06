"""Compatibility facade for Syllavox process-lifecycle helpers.

The implementation is split between the single-instance guard and the local
IPC channel so each platform-specific concern can evolve independently.
"""

from .instance_guard import INSTANCE_MUTEX_NAME, SingleInstanceGuard
from .instance_ipc import (
    INSTANCE_SERVER_NAME,
    InstanceIpcServer,
    request_existing_instance_focus,
)


__all__ = [
    "INSTANCE_MUTEX_NAME",
    "INSTANCE_SERVER_NAME",
    "InstanceIpcServer",
    "SingleInstanceGuard",
    "request_existing_instance_focus",
]
