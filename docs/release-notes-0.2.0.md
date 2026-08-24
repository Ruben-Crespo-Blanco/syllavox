# Syllavox v0.2.0 release notes

Syllavox v0.2.0 is the compatibility and privacy release for the Windows
portable MVP.

## Included

- Shared speech-text normalization for common pasted HTML/Markdown markup,
  HTML entities, Unicode forms, invisible controls, whitespace, and paragraph
  boundaries.
- Runtime-aware Piper phonemizer checks, clearer language-compatibility errors,
  and a new diagnostic classification for unsupported language configurations.
- **Clear local data and quit** in the Settings section. It removes the entire
  Syllavox-managed application data directory, including settings, logs,
  temporary and retained audio, models, and `g2pW` resources.
- Regression coverage for formatting, cleanup, logging-handler release, and
  language compatibility.

Exported WAV files saved outside the Syllavox application data directory are
not removed by the privacy action.

## Unchanged scope

Reading sessions and the accessibility-first reading interface remain deferred
until after 1.0.0. This release also does not add Sherpa-ONNX or
`rust-tts-wrapper`; the former remains planned for the additional-backend phase
and the latter remains an interoperability option for a future native-engine
requirement.

Windows remains the supported platform, the public distribution remains
portable rather than installer-based, Firefox support is experimental, and new
speech requests interrupt current playback instead of entering a queue.

## Development checks

From the project directory on Windows:

```powershell
python -m pip install -e ".[dev,packaging]"
pytest
```
