"""Small compatibility shims for the project's supported Python versions."""

from __future__ import annotations

from enum import Enum


try:
    from enum import StrEnum as StrEnum
except ImportError:

    class StrEnum(str, Enum):
        """Backport the Python 3.11 ``enum.StrEnum`` behavior to 3.10."""

        def __str__(self) -> str:
            return self.value


__all__ = ["StrEnum"]
