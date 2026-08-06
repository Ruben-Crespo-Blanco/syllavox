# Syllavox v0.1.0

Syllavox v0.1.0 is the first public MVP release: a portable Windows desktop
application for reading text aloud locally with Piper voices.

## What is included

- Portable Windows application; extract the ZIP and run `Syllavox.exe`.
- Local Piper text-to-speech and WAV playback.
- Voice discovery and explicit installation from the in-app catalog.
- Loading, unloading, and deletion of installed voice files.
- Language-grouped voice selection shared by the window, hotkey, browser
  extension, and local API.
- Clipboard hotkey, pause/resume, stop, playback interruption, and explicit
  WAV export.
- Chrome and Edge browser extensions, with experimental unsigned Firefox
  support.
- Local FastAPI API at `127.0.0.1:8765`.
- Piper compatibility diagnostics and local temporary-audio cleanup.

## First use

1. Download `Syllavox-portable.zip` from the GitHub release.
2. Extract it to a folder and run `Syllavox.exe`.
3. Open the window from the system tray.
4. Choose **Find more voices...**, install a voice, select it, and speak a
   short test sentence.

Voice models are intentionally not bundled. An internet connection is needed
to browse and download a voice; speech synthesis itself runs locally after the
voice is installed. Some Chinese voices also download Piper's shared `g2pW`
resource on first use.

## Important limitations

- Windows is the only supported platform in this release.
- There is no conventional installer or automatic updater yet.
- Firefox support is experimental and requires temporary extension loading.
- Some Piper voices have language-specific model or phonemization problems.
  In particular, some Hebrew voices currently fail to load with
  `hebrew is not a valid phoneme type`.
- Voice pronunciation and text-formatting behavior remain under active
  compatibility investigation.

## Privacy and licensing

Syllavox performs synthesis locally and does not use a cloud TTS service.
Downloaded voices, settings, logs, and runtime audio are stored under
`%LOCALAPPDATA%\Syllavox\`. Voice models are separate works with their own
model-card and dataset terms; they are not covered by Syllavox's MIT license.
Review [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) before
redistributing the portable build.

## Feedback

Please use the repository's
[`PUBLIC_FEEDBACK.md`](../PUBLIC_FEEDBACK.md) guide before reporting a
problem. Useful reports include the exact voice ID, Windows version, start
method, and sanitized error details. Do not submit private text, model files,
private voice backups, or unredacted logs.
