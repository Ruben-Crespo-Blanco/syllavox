from __future__ import annotations

import json
from pathlib import Path


CORPUS_PATH = Path(__file__).parent / "fixtures" / "text_formatting_corpus.json"


def test_text_formatting_corpus_matches_current_shared_trim_behavior() -> None:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    assert corpus["current_shared_controller_behavior"] == (
        "strip_outer_whitespace_only"
    )
    assert len(corpus["cases"]) >= 20

    for case in corpus["cases"]:
        assert case["expected_current_speech_text"] == case["input"].strip()
