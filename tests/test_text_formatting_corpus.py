from __future__ import annotations

import json
from pathlib import Path

from syllavox.text_formatting import normalize_for_speech

CORPUS_PATH = Path(__file__).parent / "fixtures" / "text_formatting_corpus.json"


def test_text_formatting_corpus_uses_v020_speech_normalization() -> None:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    assert len(corpus["cases"]) >= 20

    expected_by_id = {
        "outer-whitespace": "Hello world",
        "repeated-spaces": "Hello world",
        "tabs-and-line-breaks": "First second\nthird",
        "paragraph-break": "First paragraph.\n\nSecond paragraph.",
        "repeated-punctuation": "Wait... really?!",
        "typographic-punctuation": "“Hello”—she said. It’s fine.",
        "html-markup": "Hello world",
        "html-entity": "Tom & Jerry",
        "markdown": "Important local link",
        "url": "Visit https://example.com/a?x=1&y=2.",
        "email": "Contact support@example.com for help.",
        "numbers-and-units": "Version 2.5 is 100% ready at 3.5 kg.",
        "bullet-list": "First item\nSecond item",
        "code-fragment": "Run pip install syllavox before starting.",
        "nonbreaking-space": "Price 100 EUR",
        "zero-width-space": "AB",
        "combining-accent": "Café au lait",
        "emoji-and-symbol": "Build passed ✅ — great work!",
        "embedded-control": "Hello world",
        "empty-after-trim": "",
    }

    for case in corpus["cases"]:
        assert case["id"] in expected_by_id
        assert normalize_for_speech(case["input"]) == expected_by_id[case["id"]]
