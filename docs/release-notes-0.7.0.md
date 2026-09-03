# Syllavox v0.7.0

Syllavox v0.7.0 adds the Ubuntu-first Linux path to the existing application.
It uses the same Python package, Qt UI, speech pipeline, settings, catalogs,
and backend contracts as Windows and macOS.

## What is included

- XDG-compatible Linux application data and per-user startup registration.
- X11 global hotkeys through optional `python-xlib`.
- Wayland global hotkeys through the freedesktop Global Shortcuts portal and
  optional `dbus-next`.
- Optional eSpeak NG system voices, discovered from the host installation and
  rendered through the shared system-speech provider contract.
- Readable Linux system-voice labels in Settings and voice management.
- Native Linux packaging scaffolding for `amd64` and `arm64` Debian packages,
  plus AppImage output when `appimagetool` is available.
- Optional Sherpa-ONNX inclusion in the Linux build, while Piper remains the
  default and Sherpa voice models remain user-managed downloads.

## Linux setup

The first supported target is Ubuntu 22.04/24.04 on `amd64` or `arm64`.
Published Linux artifacts must be built and manually tested on Linux.

For development:

```bash
sudo apt update
sudo apt install espeak-ng python3-venv dpkg-dev desktop-file-utils
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,packaging,linux]"
pytest
python -m syllavox.main
```

The `espeak-ng` package is optional for Piper-only use. When it is installed,
select **Linux system voices (eSpeak NG)** in Settings, save the settings, and
restart Syllavox. eSpeak voices are installed and managed by the operating
system; Syllavox does not download or delete them.

For X11, the Linux extra provides `python-xlib`. For Wayland, the Linux extra
provides `dbus-next` and the desktop must expose the Global Shortcuts portal.
If the current Wayland desktop does not provide that portal, the application
reports the limitation instead of reading raw keyboard devices.

## Build artifacts

From a Linux checkout with the packaging extra installed:

```bash
bash packaging/build_linux.sh --skip-appimage
```

This creates an architecture-specific Debian package under `build/linux/`.
Install `appimagetool` and run the script without `--skip-appimage` to create
an AppImage as well. Use `--include-sherpa` for an optional Sherpa-enabled
variant. The base build does not include Sherpa, eSpeak NG, or downloaded voice
models.

The Windows development machine can run the Linux seam tests, but it cannot
produce or validate native Linux artifacts. Native Linux checks still need an
Ubuntu machine or CI runner with a graphical session.

## Scope

Piper remains the default backend, and the Windows and macOS paths remain in
the same source tree. The v0.7.0 release itself does not include reading
sessions. Those features are implemented in the later post-v0.7 development
tree and must not be attributed to the published v0.7 artifact.
