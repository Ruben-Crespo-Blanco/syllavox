"""Conservative normalization for text sent to speech synthesis.

The formatter removes common markup and invisible control characters while
preserving visible words, punctuation, URLs, email addresses, and paragraph
boundaries. It is shared by the desktop, hotkey, browser, and API paths through
``SpeechController``.
"""

from __future__ import annotations

import html
import re
import unicodedata


_BLOCK_TAG_RE = re.compile(
    r"</?(?:address|article|aside|blockquote|br|dd|div|dl|dt|h[1-6]|hr|"
    r"li|ol|p|pre|section|table|tr|ul)\b[^>]*>",
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_MARKDOWN_LINK_RE = re.compile(r"!?(?:\[([^\]]*)\])\([^)]*\)")
_MARKDOWN_HEADING_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+")
_MARKDOWN_BULLET_RE = re.compile(r"(?m)^\s*[-+*•◦▪●‣]\s+")
_MARKDOWN_STRONG_MARKER_RE = re.compile(
    r"(?<!\w)(?:\*\*|__)(?=\S)|(?<=\S)(?:\*\*|__)(?!\w)"
)
_MARKDOWN_EMPHASIS_MARKER_RE = re.compile(
    r"(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)"
)


def normalize_for_speech(text: str) -> str:
    """Return a stable, speech-friendly representation of ``text``.

    The rules are intentionally conservative:

    - NFC-normalize Unicode and decode HTML entities;
    - turn HTML block boundaries into paragraph/list breaks and remove tags;
    - remove common Markdown decoration while retaining visible link text;
    - remove invisible formatting/control characters;
    - collapse horizontal whitespace while preserving single and double line
      breaks, with no more than one blank line between paragraphs.
    """
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    normalized = _HTML_COMMENT_RE.sub(" ", normalized)
    normalized = _BLOCK_TAG_RE.sub("\n", normalized)
    normalized = _HTML_TAG_RE.sub(" ", normalized)
    normalized = html.unescape(normalized)

    normalized = _MARKDOWN_LINK_RE.sub(lambda match: match.group(1), normalized)
    normalized = _MARKDOWN_HEADING_RE.sub("", normalized)
    normalized = _MARKDOWN_BULLET_RE.sub("", normalized)
    normalized = _MARKDOWN_STRONG_MARKER_RE.sub("", normalized)
    normalized = _MARKDOWN_EMPHASIS_MARKER_RE.sub("", normalized)
    normalized = normalized.replace("`", "")

    cleaned_chars: list[str] = []
    for character in normalized:
        category = unicodedata.category(character)

        if category == "Cf":
            continue

        if category == "Cc" and character not in {"\n", "\t"}:
            cleaned_chars.append(" ")
            continue

        if character == "\t" or (
            character.isspace() and character != "\n"
        ):
            cleaned_chars.append(" ")
        else:
            cleaned_chars.append(character)

    lines = [
        re.sub(r" +", " ", line).strip()
        for line in "".join(cleaned_chars).split("\n")
    ]

    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    formatted_lines: list[str] = []
    blank_line_pending = False
    for line in lines:
        if not line:
            if formatted_lines and not blank_line_pending:
                formatted_lines.append("")
            blank_line_pending = True
            continue

        formatted_lines.append(line)
        blank_line_pending = False

    return "\n".join(formatted_lines).strip()


__all__ = ["normalize_for_speech"]
