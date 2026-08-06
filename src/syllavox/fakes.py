from pathlib import Path

from syllavox.audio.errors import AudioFileNotFoundError
from syllavox.audio.player import AudioPlayer
from syllavox.tts.base import (
    AudioRetention,
    BackendHealth,
    SynthesisRequest,
    SynthesisResult,
    TTSBackend,
    VoiceMemoryBackend,
    VoiceInfo,
)
from syllavox.tts.errors import BackendUnavailableError


class FakeBackend(TTSBackend, VoiceMemoryBackend):
    def __init__(
        self,
        audio_path: Path | None = None,
        healthy: bool = True,
        voices: list[VoiceInfo] | None = None,
    ) -> None:
        self.audio_path = audio_path or Path("fake.wav")
        self._healthy = healthy
        self._voices = voices or [
            VoiceInfo(
                voice_id="fake-voice",
                name="Fake Voice",
                language="en",
            )
        ]
        self._loaded_voice_ids: set[str] = set()
        self.last_request: SynthesisRequest | None = None
        self.synthesis_calls: list[SynthesisRequest] = []

    def backend_name(self) -> str:
        return "fake"

    def health(self) -> BackendHealth:
        return BackendHealth(
            name="fake",
            healthy=self._healthy,
            details="ok" if self._healthy else "backend unavailable",
        )

    def list_voices(self) -> list[VoiceInfo]:
        if not self._healthy:
            raise BackendUnavailableError("backend unavailable")

        return self._voices

    def load_voice(self, voice_id: str) -> None:
        self._loaded_voice_ids.add(voice_id)

    def unload_voice(self, voice_id: str) -> None:
        self._loaded_voice_ids.discard(voice_id)

    def is_voice_loaded(self, voice_id: str) -> bool:
        return voice_id in self._loaded_voice_ids

    def loaded_voice_ids(self) -> list[str]:
        return sorted(self._loaded_voice_ids)

    def synthesize(
        self,
        request: SynthesisRequest,
    ) -> SynthesisResult:
        self.last_request = request
        self.synthesis_calls.append(request)

        audio_path = self.audio_path
        if request.output_path is not None:
            audio_path = request.output_path
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_bytes(b"fake exported wav")

        return SynthesisResult(
            request_id=request.request_id,
            voice_id=request.voice_id or self._voices[0].voice_id,
            audio_path=audio_path,
            retention=request.retention,
        )


class FakeAudioPlayer(AudioPlayer):
    def __init__(self) -> None:
        self.play_calls: list[tuple[Path, str]] = []
        self.stop_calls = 0
        self.pause_calls = 0
        self.resume_calls = 0
        self._is_playing = False
        self._is_paused = False
        self._current_request_id: str | None = None
        self._on_finished = None
        self._volume = 1.0
        self._playback_rate = 1.0

    def play(
        self,
        audio_path: Path,
        request_id: str,
        retention: AudioRetention = AudioRetention.TEMPORARY,
    ) -> None:
        if not audio_path.exists() or not audio_path.is_file():
            raise AudioFileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        if self._is_playing:
            self.stop()

        self.play_calls.append((audio_path, request_id))
        self._is_playing = True
        self._is_paused = False
        self._current_request_id = request_id

    def stop(self) -> None:
        self.stop_calls += 1
        self._is_playing = False
        self._is_paused = False
        self._current_request_id = None

    def is_playing(self) -> bool:
        return self._is_playing

    def is_paused(self) -> bool:
        return self._is_paused

    def pause(self) -> None:
        if self._is_playing:
            self.pause_calls += 1
            self._is_playing = False
            self._is_paused = True

    def resume(self) -> None:
        if self._is_paused:
            self.resume_calls += 1
            self._is_playing = True
            self._is_paused = False

    def set_volume(self, volume: float) -> None:
        self._volume = volume

    def volume(self) -> float:
        return self._volume

    def set_playback_rate(self, rate: float) -> None:
        self._playback_rate = rate

    def playback_rate(self) -> float:
        return self._playback_rate

    def current_request_id(self) -> str | None:
        return self._current_request_id

    def simulate_finished(self, request_id: str) -> None:
        """Simulate natural completion for speech lifecycle tests."""
        self._is_playing = False
        self._is_paused = False
        self._current_request_id = None

        if self._on_finished is not None:
            self._on_finished(request_id)
