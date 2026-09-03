"""Sentence and paragraph navigation for the desktop reading workflow."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


NavigationMode = Literal["sentence", "paragraph"]
_VALID_MODES: tuple[NavigationMode, ...] = ("sentence", "paragraph")
_PARAGRAPH_SEPARATOR = re.compile(r"\n[ \t]*\n+")
_SENTENCE_PATTERN = re.compile(
    r".+?(?:[.!?]+[\"'”’)]*(?=\s+|$)|(?=$))",
    re.DOTALL,
)


@dataclass(frozen=True)
class TextSegment:
    """One navigable, speakable slice of the original editor text."""

    start: int
    end: int
    text: str


def _trimmed_segment(text: str, start: int, end: int) -> TextSegment | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start >= end:
        return None
    return TextSegment(start=start, end=end, text=text[start:end])


def paragraph_segments(text: str) -> list[TextSegment]:
    """Split text at blank lines while preserving offsets into the source."""
    segments: list[TextSegment] = []
    start = 0
    for match in _PARAGRAPH_SEPARATOR.finditer(text):
        segment = _trimmed_segment(text, start, match.start())
        if segment is not None:
            segments.append(segment)
        start = match.end()
    segment = _trimmed_segment(text, start, len(text))
    if segment is not None:
        segments.append(segment)
    return segments


def sentence_segments(text: str) -> list[TextSegment]:
    """Split paragraphs into conservative punctuation-delimited sentences."""
    segments: list[TextSegment] = []
    for paragraph in paragraph_segments(text):
        for match in _SENTENCE_PATTERN.finditer(paragraph.text):
            segment = _trimmed_segment(
                text,
                paragraph.start + match.start(),
                paragraph.start + match.end(),
            )
            if segment is not None:
                segments.append(segment)
    return segments


class ReadingSession:
    """Track a stable navigation position for one editor document."""

    def __init__(
        self,
        text: str,
        *,
        mode: NavigationMode = "sentence",
        position: int = 0,
    ) -> None:
        self.text = text
        self._mode = self._validate_mode(mode)
        self._segments: list[TextSegment] = []
        self._index = 0
        self._rebuild(position)

    @property
    def mode(self) -> NavigationMode:
        return self._mode

    @property
    def index(self) -> int:
        return self._index

    @property
    def count(self) -> int:
        return len(self._segments)

    @property
    def current(self) -> TextSegment | None:
        if not self._segments:
            return None
        return self._segments[self._index]

    @property
    def can_move_previous(self) -> bool:
        return bool(self._segments) and self._index > 0

    @property
    def can_move_next(self) -> bool:
        return bool(self._segments) and self._index < len(self._segments) - 1

    def set_mode(self, mode: NavigationMode) -> None:
        """Change navigation units while retaining the current source position."""
        mode = self._validate_mode(mode)
        if mode == self._mode:
            return
        position = self.current.start if self.current is not None else 0
        self._mode = mode
        self._rebuild(position)

    def move(self, offset: int) -> TextSegment | None:
        """Move by a relative number of units, clamped to the document."""
        if not self._segments:
            return None
        self._index = min(
            len(self._segments) - 1,
            max(0, self._index + offset),
        )
        return self.current

    def move_to_position(self, position: int) -> TextSegment | None:
        """Select the segment containing or immediately following an offset."""
        self._index = self._index_for_position(position)
        return self.current

    def _rebuild(self, position: int) -> None:
        splitter = sentence_segments if self._mode == "sentence" else paragraph_segments
        self._segments = splitter(self.text)
        self._index = self._index_for_position(position)

    def _index_for_position(self, position: int) -> int:
        if not self._segments:
            return 0
        position = max(0, min(len(self.text), int(position)))
        for index, segment in enumerate(self._segments):
            if segment.start <= position < segment.end:
                return index
            if position < segment.start:
                return index
        return len(self._segments) - 1

    @staticmethod
    def _validate_mode(mode: str) -> NavigationMode:
        if mode not in _VALID_MODES:
            return "sentence"
        return mode  # type: ignore[return-value]


__all__ = [
    "NavigationMode",
    "ReadingSession",
    "TextSegment",
    "paragraph_segments",
    "sentence_segments",
]
