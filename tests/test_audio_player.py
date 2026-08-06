from pathlib import Path

import pytest

from syllavox.audio.errors import AudioFileNotFoundError
from syllavox.fakes import FakeAudioPlayer


def test_fake_audio_player_play_tracks_state(tmp_path: Path) -> None:
    audio_path = tmp_path / "test.wav"
    audio_path.write_bytes(b"fake wav")

    player = FakeAudioPlayer()

    player.play(audio_path, "req-1")

    assert player.is_playing() is True
    assert player.current_request_id() == "req-1"
    assert player.play_calls == [(audio_path, "req-1")]


def test_fake_audio_player_stop_tracks_state(tmp_path: Path) -> None:
    audio_path = tmp_path / "test.wav"
    audio_path.write_bytes(b"fake wav")

    player = FakeAudioPlayer()
    player.play(audio_path, "req-1")
    player.stop()

    assert player.is_playing() is False
    assert player.current_request_id() is None
    assert player.stop_calls == 1


def test_fake_audio_player_interrupts_existing_playback(tmp_path: Path) -> None:
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    first.write_bytes(b"fake wav")
    second.write_bytes(b"fake wav")

    player = FakeAudioPlayer()

    player.play(first, "req-1")
    player.play(second, "req-2")

    assert player.stop_calls == 1
    assert player.is_playing() is True
    assert player.current_request_id() == "req-2"
    assert player.play_calls == [
        (first, "req-1"),
        (second, "req-2"),
    ]


def test_fake_audio_player_missing_file_raises(tmp_path: Path) -> None:
    player = FakeAudioPlayer()

    with pytest.raises(AudioFileNotFoundError):
        player.play(tmp_path / "missing.wav", "req-1")


def test_fake_audio_player_finished_callback_runs(tmp_path: Path) -> None:
    audio_path = tmp_path / "test.wav"
    audio_path.write_bytes(b"fake wav")

    calls = []

    player = FakeAudioPlayer()
    player.set_finished_callback(lambda request_id: calls.append(request_id))

    player.play(audio_path, "req-1")
    player.simulate_finished("req-1")

    assert calls == ["req-1"]
