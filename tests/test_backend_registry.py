from __future__ import annotations

import syllavox.tts.backend_registry as registry
from syllavox.constants import WINDOWS_SAPI_TTS_BACKEND


def test_backend_registry_keeps_piper_and_sherpa_order(monkeypatch) -> None:
    monkeypatch.setattr(registry.sys, "platform", "win32")
    monkeypatch.setattr(registry.importlib.util, "find_spec", lambda name: object())

    descriptors = registry.backend_descriptors()

    assert [descriptor.backend_id for descriptor in descriptors] == [
        "piper",
        "sherpa_onnx",
        WINDOWS_SAPI_TTS_BACKEND,
    ]
    assert descriptors[-1].is_system_backend is True


def test_registry_can_create_sapi_with_a_test_factory() -> None:
    created: list[str] = []

    class FakeBackend:
        def backend_name(self) -> str:
            return WINDOWS_SAPI_TTS_BACKEND

    backend = registry.create_backend(
        WINDOWS_SAPI_TTS_BACKEND,
        factories={
            WINDOWS_SAPI_TTS_BACKEND: lambda: (
                created.append(WINDOWS_SAPI_TTS_BACKEND) or FakeBackend()
            ),
        },
    )

    assert backend.backend_name() == WINDOWS_SAPI_TTS_BACKEND
    assert created == [WINDOWS_SAPI_TTS_BACKEND]
