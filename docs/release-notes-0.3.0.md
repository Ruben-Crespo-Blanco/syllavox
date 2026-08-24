# Syllavox v0.3.0 release notes

Syllavox v0.3.0 is the UI/UX polish release for the portable Windows MVP.

## Included

- A minimal, smooth, original visual theme with clearer hierarchy, spacing,
  rounded surfaces, and focused status feedback.
- A refreshed Syllavox speech-and-waveform icon used by the tray and main
  application window.
- A configurable global **Read hotkey** in Settings. Press a modifier plus one
  supported key and save the setting; `Ctrl+Alt+R` remains the default.
- Safe runtime hotkey replacement. If Windows rejects the new shortcut,
  Syllavox keeps the previous working shortcut and reports the reason.
- A larger default window layout for comfortable text entry and settings use.
- Installed voices now show readable language names for supported locale
  families, including Hebrew instead of the raw `HE` family code.
- The text-length setting remains configurable from 100 to 10,000 characters;
  the upper bound is a practical single-request safeguard, not a Piper limit.
- The Read hotkey row includes a visible **Apply changes** action for immediate
  confirmation and persistence.

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
