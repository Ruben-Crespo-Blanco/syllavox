# Changelog

## [1.0.0] - 2026-09-03

### Added

- A non-modal Quick setup flow with sample playback and shortcut guidance.
- Operating-system voices as a zero-download fallback beside the default Piper
  workflow when the platform provider is available.
- Locale-aware recommended voice selection in the offline catalog.
- Sentence/paragraph navigation, replay, automatic continuation, persistent
  local editor position, and synchronized active-unit highlighting.
- Accessible names and descriptions for primary setup, voice, editor,
  navigation, state, and feedback controls.
- Chromium and Firefox store-submission packages with SHA-256 files and CI
  artifacts.
- Product positioning, support-tier, accessibility, research, and release
  baseline documentation.
- A persistent **Run setup again…** action for revisiting onboarding without
  replacing saved reading content.

### Changed

- Speech-engine and maximum request-length controls now live under Advanced
  settings.
- The browser extension no longer requests page-wide, tab, or scripting
  permissions; it uses only the user-invoked context-menu selection.
- Windows portable and Linux packaging now emit SHA-256 files.
- System voices are explicitly read-only in voice management, including when
  they are presented alongside downloadable voices.

## [0.7.0] - 2026-09-02

Syllavox 0.7.0 adds the Ubuntu-first Linux adaptation in the shared
codebase. Piper remains the default speech engine, Sherpa-ONNX remains
optional, and Linux system voices are provided by the host's eSpeak NG
package rather than bundled into the application.

### Added

- Linux XDG data/startup integration with a per-user autostart desktop entry.
- Linux global-hotkey selection for X11 and Wayland.
- X11 registration through optional `python-xlib` and Wayland registration
  through the freedesktop Global Shortcuts portal with optional `dbus-next`.
- A Linux eSpeak NG system-voice provider that discovers host voices and
  produces validated mono, 16-bit WAV output through the shared system-speech
  abstraction.
- Clear Linux backend and system-voice labels in Settings and voice
  management, with no Linux voice-model downloads managed by Syllavox.
- Ubuntu-first Linux packaging scaffolding for architecture-specific `.deb`
  and AppImage artifacts, with optional Sherpa inclusion.
- Linux platform regression coverage for startup files, backend selection,
  eSpeak rendering, hotkey routing, X11 registration, and UI behavior.

### Validation and release scope

- The Windows-hosted automated suite validates the Linux seams with fakes and
  passes without importing Linux-only libraries during ordinary test startup.
- Native eSpeak NG voice discovery, X11/Wayland registration, tray behavior,
  and Debian/AppImage builds still require manual validation on Ubuntu.
- Reading sessions and the accessibility-first reading interface remain
  deferred until after 1.0.0.

## [0.6.0] - 2026-08-30

Syllavox 0.6.0 adds the first macOS adaptation in the shared codebase while
preserving the existing Windows Piper, Sherpa-ONNX, SAPI, portable, and
installer paths.

### Added

- A macOS system-speech provider using the built-in `say` and `afconvert`
  commands, with readable voice metadata and validated mono 16-bit WAV output.
- A lazy macOS AppKit global-hotkey adapter with Input Monitoring guidance.
- macOS per-user startup registration using the bundled app login-item API when
  available and a LaunchAgent fallback for source checkouts.
- A macOS PyInstaller `.app` specification, Info.plist, icon conversion, ZIP,
  DMG, checksum, signing, and optional notarization build script.
- Python 3.10 compatibility for the hotkey enum and TOML-based test and
  packaging tooling through the `tomli` backport.
- macOS-aware system-voice labels, backend settings, startup wording, and
  read-only voice management.
- Simulated macOS regression coverage that runs on the existing Windows
  development machine without importing macOS-only modules.
- macOS dependency resolution that pins Piper 1.7.0 and ONNX Runtime 1.19.2,
  avoiding the incompatible legacy `piper-phonemize` path.

### Validation and release scope

- The Windows-safe automated suite covers the new macOS seams and preserves the
  existing Windows behavior.
- The native macOS build path has been validated. A manual smoke test remains
  required before publishing a macOS artifact. The build must run on macOS or a
  macOS CI runner because
  Apple's SDK tools, `say`, `afconvert`, signing, and notarization are not
  available on Windows.
- Linux adaptation, reading sessions, and the accessibility-first reading
  interface remain future work. Reading sessions and the accessibility-first
  interface stay deferred until after 1.0.0.

## [0.5.0] - 2026-08-29

Syllavox 0.5.0 adds optional Windows SAPI system-voice support and a per-user
Windows installer while keeping Piper as the default backend.

### Added

- A backend-neutral `SystemSpeechProvider` abstraction for future native
  macOS and Linux system-speech providers.
- Windows SAPI discovery through the optional `comtypes` dependency.
- Stable SAPI voice IDs and readable language/country metadata.
- Synchronous SAPI WAV rendering through `SpVoice` and `SpFileStream`, with
  output validation and partial-file cleanup.
- A Windows SAPI choice in Settings and a restart action for backend changes.
- Read-only system-voice management UI; Windows remains responsible for
  installing and removing those voices.
- A per-user Inno Setup installer with Start Menu and optional desktop
  shortcuts, built from the SAPI-enabled portable application.
- An opt-in Windows startup setting that writes the current installation to
  the signed-in user's Run registry key and supports starting minimized to
  the tray.
- `-IncludeSapi` portable packaging support, while the base build continues to
  exclude the optional SAPI dependency.

### Validation

- Unit coverage verifies SAPI locale conversion, COM lifecycle balancing,
  stable IDs, WAV validation, atomic output handling, and failure cleanup.
- The development host successfully enumerates its installed Windows SAPI
  voices. Rendering remains dependent on the local SAPI engine and is reported
  as an actionable synthesis error when Windows rejects the request.

### Release scope

Reading sessions and an accessibility-first reading interface remain deferred
until after 1.0.0. Piper remains the default, and macOS/Linux adaptations stay
on the roadmap for later milestones.

## [0.4.2] - 2026-08-29

Syllavox 0.4.2 expands optional Sherpa-ONNX language coverage while keeping
Piper as the default backend and fallback.

### Added

- Curated Sherpa-ONNX Mimic3 VITS bundles for Afrikaans, Bengali, Gujarati,
  and Tswana.
- Clear language, country, source, license, speaker, and sample-rate metadata
  for the new voices.
- SHA-256 archive verification during Sherpa bundle installation, with the
  digest preserved in each installed manifest.
- `scripts/validate_sherpa_catalog.py` for metadata checks and real-model WAV
  smoke tests.
- Release documentation recording model provenance, archive sizes, runtime
  measurements, and the remaining language-coverage candidates.

### Changed

- The Sherpa voice catalog now uses readable language labels for the v0.4.2
  additions instead of exposing locale codes as the primary language name.
- No model files are included in the source repository or portable build;
  models remain explicit, user-managed downloads.

### Validation

- All four real upstream archives installed through the Syllavox bundle
  installer and produced valid mono, 16-bit WAV output with Sherpa-ONNX 1.13.6
  on Windows.
- Thai, additional Indic languages, and other long-tail gaps remain research
  candidates pending conversion, quality, size, and license review.

### Release scope

Reading sessions and the accessibility-first reading interface remain deferred
until after 1.0.0. macOS remains planned for v0.5.0, Linux for v0.6.0, and
Android remains planned after 1.0.0.

## [0.4.1] - 2026-08-29

Syllavox 0.4.1 is a hardening release that prepares the Windows application
for future macOS and Linux adaptations.

### Added

- Platform seams for global hotkeys, application data paths, and
  single-instance locking, while preserving the existing Windows behavior.
- Explicit release of cached Piper and Sherpa model resources during shutdown.
- A dependency and frozen-portable-size audit script.
- Regression coverage for platform selection, platform data directories, and
  complete runtime cleanup.

### Changed

- The portable build excludes optional `hf_xet`, development tooling, and
  unused Qt module families while retaining the required Qt and speech
  runtime components.
- macOS uses the Application Support data-root convention and Linux/Unix uses
  XDG data paths when those platforms are used in development.
- Hebrew Piper is no longer documented as an active compatibility blocker.

### Release scope

This release does not implement macOS, Linux, reading sessions, the
accessibility-first reading interface, or Android. Those remain future work.

## [0.4.0] - 2026-08-28

Syllavox 0.4.0 adds Sherpa-ONNX as an optional speech backend while keeping
Piper as the default.

### Added

- Lazy Sherpa-ONNX integration for VITS, Matcha, Kokoro, KittenTTS, and
  Supertonic model families.
- In-app discovery and atomic installation of curated official non-Piper
  Sherpa model bundles.
- Language-aware Kokoro speaker metadata and language-qualified Supertonic
  voice IDs.
- Sherpa model loading/unloading, complete bundle deletion, diagnostics, model
  size reporting, and native WAV output.
- A future-language model register covering existing candidates for Hebrew,
  Thai, Bengali, Gujarati, Tamil, Telugu, and other missing languages.

### Changed

- The optional `sherpa` dependency and `-IncludeSherpa` portable build switch
  now provide a supported opt-in backend pathway. The base portable build
  remains Piper-only to minimize its size.
- Sherpa's converted `vits-piper-*` archives are omitted from its catalog;
  Piper remains responsible for those voices.

### Release scope

Reading sessions and a dedicated accessibility-first reading interface remain
deferred until after 1.0.0. `rust-tts-wrapper` remains a future native
interoperability option rather than Syllavox's core TTS layer.

## [0.3.0] - 2026-08-24

Syllavox 0.3.0 is the UI/UX polish release for the Windows MVP.

### Added

- Configurable global read-hotkey capture in Settings, retaining
  `Ctrl+Alt+R` as the default.
- Conflict-safe runtime hotkey re-registration with restoration of the previous
  shortcut when the replacement cannot be registered.
- A minimal, smooth visual theme for the main window, settings, voice
  management surfaces, and speech editor.
- Refreshed Syllavox speech-and-waveform icon used by the tray and application
  window.
- Readable language names for installed voices, including Hebrew and other
  supported locale families.

### Changed

- The default window geometry now gives the speech editor and settings room to
  breathe while preserving user-saved geometry.
- Hotkey status and save feedback now show the active configured shortcut.
- An immediately visible **Apply changes** action is available beside the
  Read hotkey field.
- The text-length setting documents its practical 10,000-character ceiling;
  this is a single-request safeguard rather than a Piper engine limit.

### Release scope

This release does not add reading sessions, a dedicated accessibility-first
reading interface, new TTS backends, or new platform targets. Those remain
future roadmap work.

## [0.2.0] - 2026-08-23

Syllavox 0.2.0 is the compatibility and privacy release for the Windows MVP.

### Added

- Conservative shared text normalization for common HTML/Markdown markup,
  HTML entities, Unicode normalization, invisible controls, whitespace, and
  paragraph boundaries.
- Runtime-aware Piper phonemizer compatibility preflight and diagnostics for
  language-specific voice failures.
- **Clear local data and quit** action covering settings, logs, temporary and
  retained audio, downloaded models, and language resources.

### Changed

- The visible text counter and request validation now count the normalized
  speech text rather than unformatted pasted input.
- Piper health details report voices that need language compatibility attention.

### Release scope

This release does not add reading sessions, an accessibility-first reading
interface, new TTS backends, or new platform targets. Those remain future
roadmap work.

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
