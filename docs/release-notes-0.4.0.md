# Syllavox v0.4.0 release notes

Syllavox v0.4.0 adds Sherpa-ONNX as an optional local speech backend. Piper
remains the default and continues to provide the broadest voice catalog.

## Included

- Lazy CPU-first Sherpa-ONNX support for VITS, Matcha, Kokoro, KittenTTS, and
  Supertonic.
- In-app catalog browsing and atomic installation of official non-Piper Sherpa
  model bundles.
- Language-aware Kokoro voices, including readable speaker names and English /
  Chinese selection.
- Supertonic's 31-language, multi-speaker selection through stable
  language-qualified voice IDs.
- Bundle-level loading, unloading, diagnostics, model-size reporting, and
  deletion of all downloaded model resources.
- Sherpa-native WAV writing when the runtime provides it.
- A documented future-language register for existing Hebrew, Thai, Bengali,
  Gujarati, Tamil, Telugu, and other model candidates.

## Distribution and model scope

The ordinary portable build remains Piper-only so users do not pay the
Sherpa runtime size unless they need it. Build a Sherpa-enabled portable
variant with `packaging/build_portable.ps1 -IncludeSherpa`. Neither build
bundles voice models; users install models explicitly, and each model's own
license and dataset terms apply.

The Sherpa catalog intentionally excludes converted `vits-piper-*` archives.
Piper remains the source of truth for those voices. ZipVoice and Pocket are not
included because their reference-audio voice-cloning workflow does not match
Syllavox's fixed-voice interface.

## Unchanged scope

Reading sessions and an accessibility-first reading interface remain deferred
until after 1.0.0. `rust-tts-wrapper` was evaluated but is not used as the
core TTS layer. Windows remains the supported platform, Firefox support is
experimental, and new speech requests interrupt current playback.

## Development checks

From the project directory on Windows:

```powershell
python -m pip install -e ".[dev,packaging,sherpa]"
pytest
python scripts/benchmark_sherpa_onnx.py
```
