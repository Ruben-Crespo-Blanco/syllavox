# Syllavox v0.5.0 release notes

Syllavox v0.5.0 adds Windows SAPI as an optional speech engine and a per-user
Windows installer while keeping Piper as the default and Sherpa-ONNX as an
optional model backend.

## Included

- Windows SAPI voice discovery through the lightweight `comtypes` COM bridge.
- Stable internal voice IDs derived from the Windows SAPI token ID, so saved
  selections do not expose registry paths in the Syllavox settings file.
- Readable language and country labels from SAPI locale metadata, for example
  “English — United States (en-US)”.
- WAV rendering through `SAPI.SpVoice` and `SAPI.SpFileStream`, with atomic
  output replacement and post-render WAV validation.
- A backend-neutral `SystemSpeechProvider` boundary for future native macOS
  and Linux system-speech implementations.
- A restart action in Settings when changing speech engines.
- Read-only system-voice management that makes it clear Windows owns the
  voices and their installation/removal lifecycle.
- A per-user Windows installer built from the tested portable application
  folder, with Start Menu and optional desktop shortcuts.
- An opt-in **Run Syllavox on Windows startup** setting that registers the
  current installation for the signed-in Windows user without requiring
  administrator privileges. It can be combined with **Start minimized to
  tray**.
- Optional SAPI packaging through `-IncludeSapi`; the ordinary Piper-only
  portable build does not include `comtypes`.
- API, browser-extension, hotkey, export, and playback paths continue to use
  the same shared speech controller and backend manager.

## How to use Windows SAPI

Use a SAPI-enabled build, open **Settings**, choose **Windows SAPI**, select
**Save settings**, and use **Restart to use Windows SAPI**. The voice selector
then shows the voices installed and exposed by Windows. Choose **System
voices…** to review them. Syllavox does not download, load, unload, or delete
these system voices.

Build the optional variant from the repository with:

```powershell
.\packaging\build_portable.ps1 -IncludeSapi
```

Combine `-IncludeSapi` with `-IncludeSherpa` when one portable folder should
expose all three engines.

Build the installer after installing Inno Setup 6 and making `ISCC.exe`
available on `PATH` (or setting `INNO_SETUP_COMPILER`):

```powershell
.\packaging\build_installer.ps1
```

The standard installer includes Piper and Windows SAPI. Add
`-IncludeSherpa` to the build command when producing a combined Piper/SAPI/
Sherpa installer.

## Validation

The provider's unit tests cover COM lifecycle balancing, locale conversion,
stable IDs, valid WAV output, atomic replacement, failure cleanup, and
non-Windows behavior. On the development Windows host, SAPI voice enumeration
is working and reports the installed voices. Actual speech rendering is
delegated to the installed SAPI engine; if Windows returns a COM synthesis
error, Syllavox reports it without leaving a partial WAV file.

Piper remains the default. Reading sessions and the accessibility-first
reading interface remain deferred until after 1.0.0. macOS and Linux system
speech providers remain future work and will use the new provider boundary.
