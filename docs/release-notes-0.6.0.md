# Syllavox v0.6.0 implementation notes

Syllavox v0.6.0 adapts the existing application for macOS without creating a
second codebase. Windows remains the established supported distribution path;
this milestone adds the macOS runtime and packaging path so it can be built
and tested on a Mac next.

## Included

- macOS system voices through Apple's built-in `say` command, converted with
  `afconvert` to the same validated WAV contract used by the other engines;
- stable voice IDs and readable language labels for voices returned by macOS;
- configurable global hotkeys through AppKit event monitors, with a clear
  Input Monitoring permission message when macOS denies monitoring;
- per-user startup registration through `SMAppService` for frozen app bundles,
  with a direct LaunchAgent plist fallback for source development;
- macOS-aware system voice management and Settings wording;
- a native PyInstaller `.app` specification and
  `packaging/build_macos.sh` for app, ZIP, optional DMG, checksum, signing,
  and optional notarization output;
- regression tests for all of the above using platform seams and fakes, so the
  Windows development environment can verify the integration structure.

## Build on macOS

From the repository root on a Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,packaging,macos]"
bash packaging/build_macos.sh --skip-dmg
```

Use `--include-sherpa` for a Sherpa-enabled app. Set `SIGN_IDENTITY` to sign
the app. For release distribution, set `NOTARY_PROFILE` to an already
configured `notarytool` keychain profile; the script submits and staples the
DMG, then regenerates its checksum.

The script creates architecture-specific files under `build/macos/`. Build
arm64 and x86_64 separately on their native runners, or add a deliberate
universal-build step after both native builds have passed manual testing.

The supported Qt 6.5-compatible macOS baseline is macOS 11. On macOS 13 and
newer, startup registration can use Apple's `SMAppService`; on macOS 11–12,
Syllavox uses the per-user LaunchAgent fallback. If `pip` only offers PySide6
6.5.2 on the Mac, use Python 3.11 or another Python version supported by that
PySide6 release.

## macOS permissions and limitations

macOS may require enabling Syllavox under **System Settings → Privacy &
Security → Input Monitoring** before a global hotkey can be registered. System
voices are installed and managed by macOS; Syllavox only discovers and uses
them.

The first macOS artifact is intentionally based on the built-in speech tools,
which keeps the application smaller than bundling another system speech
runtime. Sherpa-ONNX remains an optional model-backed backend, and Piper
remains available through the shared backend interface.

This milestone does not implement Linux support, reading sessions, or the
accessibility-first reading interface. Those reading features remain deferred
until after 1.0.0.
