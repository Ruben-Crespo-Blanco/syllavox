"""Request-identifier generation shared by application entry points."""

from __future__ import annotations

from uuid import uuid4


def new_request_id(prefix: str | None = None) -> str:
    """Return a unique request ID, optionally namespaced by a prefix."""
    identifier = str(uuid4())
    return f"{prefix}-{identifier}" if prefix else identifier
