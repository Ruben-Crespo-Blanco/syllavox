from syllavox.reading_session import (
    ReadingSession,
    paragraph_segments,
    sentence_segments,
)


def test_sentence_segments_preserve_source_offsets_and_punctuation() -> None:
    text = '  First sentence.  Second question?\n\nFinal paragraph!  '

    segments = sentence_segments(text)

    assert [segment.text for segment in segments] == [
        "First sentence.",
        "Second question?",
        "Final paragraph!",
    ]
    assert [text[segment.start : segment.end] for segment in segments] == [
        segment.text for segment in segments
    ]


def test_paragraph_segments_split_only_at_blank_lines() -> None:
    text = "First line\ncontinues here.\n\nSecond paragraph."

    assert [segment.text for segment in paragraph_segments(text)] == [
        "First line\ncontinues here.",
        "Second paragraph.",
    ]


def test_session_navigates_and_clamps_at_document_edges() -> None:
    session = ReadingSession("One. Two. Three.")

    assert session.current is not None
    assert session.current.text == "One."
    assert session.can_move_previous is False
    assert session.move(-1).text == "One."
    assert session.move(1).text == "Two."
    assert session.move(99).text == "Three."
    assert session.can_move_next is False


def test_session_mode_change_keeps_the_current_source_position() -> None:
    text = "One. Two.\n\nThree. Four."
    session = ReadingSession(text, position=text.index("Three"))

    assert session.current is not None
    assert session.current.text == "Three."

    session.set_mode("paragraph")

    assert session.current is not None
    assert session.current.text == "Three. Four."
    assert session.index == 1


def test_session_restores_nearest_segment_for_saved_position() -> None:
    session = ReadingSession("One. Two. Three.", position=7)

    assert session.current is not None
    assert session.current.text == "Two."


def test_empty_session_is_safe_to_navigate() -> None:
    session = ReadingSession(" \n\n ")

    assert session.current is None
    assert session.count == 0
    assert session.move(1) is None
