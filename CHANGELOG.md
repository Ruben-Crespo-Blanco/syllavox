# Changelog

## [0.1.1] - 2026-08-23

Syllavox 0.1.1 is a maintenance release for the Windows MVP.

### Changed

- Aligned the Python package, runtime, and browser-extension versions at
  `0.1.1`.
- Declared the pytest development extra so the automated test environment can
  be recreated from project metadata.
- Updated release documentation and portable-build metadata for the current
  release.
- Added a release-metadata regression check for the declared test runner.

### Release scope

This release does not add reading sessions, a redesigned accessibility-first
interface, new TTS backends, or new platform targets. Those items remain on
the future roadmap.

## [0.1.0] - 2026-08-06

Syllavox is a Windows-first local, offline text-to-speech desktop application.

### Added

- Windows tray application with a text-entry window
- Piper-backed local speech synthesis and WAV playback
- Explicit voice discovery, installation, loading, unloading, and deletion
- Language-grouped voice selection shared by the UI, hotkey, and local API
- Configurable global hotkey for clipboard speech or opening the window
- Local FastAPI/Uvicorn API on `127.0.0.1:8765`
- Chrome, Edge, and experimental Firefox extension support
- Playback interruption, stop, pause/resume, and temporary WAV cleanup
- Explicit WAV export to a user-selected destination
- Portable Windows executable packaging
- Piper voice compatibility diagnostics and text-formatting audit corpus
- Local dependency/license notices and a policy excluding voice models from
  public release artifacts

### Known limitations

- Windows is the supported platform; macOS and Linux adaptations are future
  work.
- Firefox distribution is experimental and not signed.
- Voice compatibility and text-formatting improvements remain ongoing,
  especially for language-specific Piper resources.
- Some Hebrew Piper voices currently fail during loading with
  `hebrew is not a valid phoneme type`; this is recorded for a future
  compatibility investigation.
- Users must review the model-card and dataset terms for each voice they
  install; voice models are not covered by Syllavox's MIT license.

### Release distribution

- The public release is a portable Windows ZIP; no installer is included.
- Voice models are not bundled. Users install the voices they want from the
  in-app Piper catalog.
- See [`docs/release-notes-0.1.0.md`](docs/release-notes-0.1.0.md) for the
  user-facing release summary and upgrade-free first-install instructions.
