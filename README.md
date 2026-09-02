# Syllavox

Syllavox reads text aloud on your computer using local speech synthesis. Text
is processed on the computer rather than sent to a cloud TTS service.

This is the v0.7.0 development release. Windows has an installer and a
portable ZIP for ordinary use. The shared macOS adaptation and native build
path are included in the source, and Ubuntu-first Linux source and packaging
paths are included as well. No Python installation is required for published
artifacts.

For the concise public-release summary, see the
[v0.7.0 implementation notes](docs/release-notes-0.7.0.md).

## Before you start

- Windows remains the established published distribution path. macOS and
  Ubuntu-first Linux source/build paths are included and require native
  builds for their final artifacts.
- The public application does not include voice models. You choose and
  download the voices you want from Piper's official catalog or, in a
  Sherpa-enabled build, from Syllavox's curated Sherpa-ONNX model catalog.
- An internet connection is needed to browse and download a voice. Once a
  voice is installed, speech synthesis runs locally.
- Voice models have their own licenses and model-card terms. Review those
  terms before using or redistributing a voice.
- The portable folder is large because it contains the application runtime and
  Chinese-language support. Syllavox uses one universal distribution; there
  are no separate Chinese and non-Chinese builds.
- Windows SAPI is available in SAPI-enabled builds and uses voices already
  installed in Windows; those voices are not downloaded by Syllavox.

## Install and start Syllavox

For the normal installation, download `Syllavox-<version>-setup.exe` from the
**Releases** page and run it. The installer creates a per-user installation,
so administrator privileges are not required. It adds a Start Menu shortcut
and can create a desktop shortcut.

The portable alternative is `Syllavox-portable.zip`:

1. Extract the ZIP to a folder of your choice. Do not try to run the program
   from inside the ZIP file.
2. Open the extracted `Syllavox` folder and double-click `Syllavox.exe`.

By default Syllavox starts in the host notification area (system tray).
Use the tray icon to open the main window. To have Syllavox launch whenever
you sign in to Windows, open **Settings**, enable **Run Syllavox on Windows
startup**, and select **Save settings**. This registers a per-user Windows
startup entry; it does not run Syllavox as administrator. Combine it with
**Start minimized to tray** if Syllavox should remain quiet in the background.

If Windows displays a security warning, first confirm that the file came from
the project's official GitHub release and compare the published checksum. The
first public builds may not be code-signed.

## First-time voice setup

The application starts without a voice model intentionally. This keeps the
distribution from imposing a voice or redistributing voice-model files.

1. Open the Syllavox window from the tray icon.
2. Select **Find more voices...**.
3. Browse the catalog by language and choose a voice.
4. Select **Install selected** and wait for both model files to finish
   downloading.
5. Select the installed voice in the voice list.
6. Enter a short test sentence and select **Speak**.

The first use of some Chinese voices may also download Piper's `g2pW`
phonemization resource. This is a shared language resource and is reused by
later Chinese speech requests.

To use the four v0.4.2 Sherpa additions (Afrikaans, Bengali, Gujarati, or
Tswana), use a Sherpa-enabled build, choose **Sherpa-ONNX** in **Settings**,
save the selection, and use the displayed restart action. Then return to
**Find more voices...** and install the desired bundle. The Sherpa runtime is
optional, and model archives are downloaded only when you select them.

To use Windows' installed system voices, use a SAPI-enabled build, choose
**Windows SAPI** in **Settings**, save the selection, and select the displayed
restart action. Open **System voices…** to review the voices Windows exposes.
System voices are read-only in Syllavox: installation, removal, and language
changes are handled by Windows.

On macOS, choose **macOS system voices** in **Settings**, save the selection,
and select the displayed restart action. The voice list then shows voices
installed by macOS. If the global hotkey is unavailable, enable Syllavox under
**System Settings → Privacy & Security → Input Monitoring**.

On Ubuntu/Linux, install the optional host speech engine with
`sudo apt install espeak-ng`, then choose **Linux system voices (eSpeak NG)**
in **Settings**. Syllavox discovers the voices supplied by the system package;
it does not download or manage them. X11 global hotkeys use the optional
`python-xlib` integration. Wayland uses the desktop's Global Shortcuts portal
when the desktop provides it; some desktops may ask for approval or may not
offer the portal.

Piper voices are downloaded from the official
[Piper voice catalog](https://huggingface.co/rhasspy/piper-voices). A
Sherpa-enabled build also exposes the curated optional bundles documented in
the [v0.4.2 language coverage record](docs/language-coverage-0.4.2.md).
Syllavox does not include voice models or the project's complete developer
voice backup in public releases.

## Language coverage

Syllavox has two voice catalogs. Piper is the default and has the broadest
selection. Sherpa-ONNX is optional and adds a smaller curated selection of
non-Piper voices. The live Piper catalog can change as voices are added or
removed, and the exact locales, speakers, and quality levels vary by language;
use **Find more voices...** to see the current downloadable entries.

Windows SAPI is a third, read-only voice source. It exposes the voices
installed in Windows and does not have a downloadable Syllavox catalog.

### Available now

The current Piper catalog covers these language families:

Arabic, Armenian, Albanian, Basque, Bengali, Bulgarian, Catalan, Chinese,
Czech, Danish, Dutch, English, Estonian, Farsi, Finnish, French, Georgian,
German, Greek, Hebrew, Hindi, Hungarian, Icelandic, Indonesian, Italian,
Japanese, Kazakh, Korean, Kurmanji Kurdish, Latvian, Luxembourgish,
Malayalam, Marathi, Nepali, Norwegian, Polish, Portuguese, Romanian, Russian,
Serbian, Slovak, Slovenian, Spanish, Swedish, Swahili, Telugu, Turkish,
Ukrainian, Vietnamese, and Welsh.

A Sherpa-enabled build additionally provides curated Mimic3 voices for
Afrikaans, Bengali, Gujarati, and Tswana. Its multilingual Supertonic bundle
also provides Croatian and Lithuanian voices, while many other Supertonic
languages overlap with Piper. Sherpa voice downloads are optional and are not
included in the portable application.

### Desired future targets

These are planned targets, not promises of current support. For languages that
already have a Piper voice, the goal may be an additional higher-quality,
regional, or Sherpa-compatible option:

- Thai;
- Tamil, Punjabi, Kannada, and additional Indic languages;
- Malay, Filipino/Tagalog, and Burmese/Myanmar;
- Amharic and Azerbaijani;
- stronger or additional non-Piper options for Marathi and Telugu; and
- other long-tail languages prioritized by demand, pronunciation quality,
  model size, and licensing.

The [future language-model candidate register](docs/sherpa-onnx/future-language-model-candidates.md)
tracks the research status and trade-offs for these targets. The [official
Piper catalog](https://huggingface.co/rhasspy/piper-voices) remains the source
of truth for its live language and voice list.

## Everyday use

### Main window

The main window lets you:

- enter or paste text;
- choose an installed voice, grouped by language;
- speak the text;
- pause, resume, or stop playback;
- export speech to a WAV file;
- adjust playback volume and speed;
- manage installed voices.

The v0.4.0 interface uses a quieter visual hierarchy with rounded cards,
generous spacing, and a focused light palette. The application icon and window
identity use the same original Syllavox speech-and-waveform mark.

New speech requests interrupt the current playback. Syllavox does not queue
multiple requests.

Before synthesis, Syllavox applies conservative text formatting: it removes
common HTML/Markdown decoration, decodes HTML entities, normalizes Unicode,
removes invisible control characters, and preserves visible punctuation,
URLs, and paragraph breaks.

### Clipboard hotkey

The default global hotkey is:

```text
Ctrl+Alt+R
```

By default, it reads the current clipboard text using the voice selected in the
desktop window. The hotkey action can be changed to open the Syllavox window
instead. To change the read shortcut, open **Settings**, click the **Read
hotkey** field, press a modifier plus one supported key, and select **Save
settings**. The default is `Ctrl+Alt+R`; if Windows rejects a replacement
because another application is using it, Syllavox keeps the previous shortcut.
The selected voice and playback preferences are shared by the window, hotkey,
and local API.

### Browser extension

The browser extension adds **Read selected text locally** to the context menu.
It sends selected text to the Syllavox application on the same computer.

The desktop application must already be running.

For installation instructions, see
[the extension guide](extension/README.md). Chrome and Edge are supported;
Firefox support is experimental and uses a temporary extension that must be
loaded again after Firefox restarts.

### Exporting a WAV file

Use **Export WAV...** to save speech to a location you choose. Exported files
remain where you save them. Temporary files used for normal playback are
removed when they are no longer needed.

## Privacy and local files

Syllavox is designed for local operation:

- speech synthesis and playback happen on your computer;
- the browser extension communicates with the local application at
  `127.0.0.1`;
- the application does not use a cloud TTS service;
- voice downloads come from an upstream Piper catalog or a curated Sherpa
  model release only when you explicitly install a voice.

The application stores runtime data under the platform's local user-data
directory:

```text
Windows: %LOCALAPPDATA%\Syllavox\
macOS: ~/Library/Application Support/Syllavox/
Linux: $XDG_DATA_HOME/Syllavox/ or ~/.local/share/Syllavox/
```

| Location | Contents |
|---|---|
| `settings.json` | Application and playback settings |
| `logs\app.log` | Local diagnostic and lifecycle logs |
| `models\piper\` | Downloaded Piper voice model pairs |
| `models\piper\g2pW\` | Chinese phonemization data when needed |
| `models\sherpa-onnx\` | Optional Sherpa-ONNX model bundles |
| `tmp\` | Temporary playback files, cleaned automatically |
| `audio\` | Explicitly retained runtime audio files |

The current release can delete individual voice models from **Manage
voices...**, remove unused `g2pW` data, or use **Clear local data and quit** in
the Settings section. The privacy action removes all Syllavox-managed settings,
logs, temporary and retained audio, downloaded models, and language resources.
It does not delete WAV files exported to other locations.

To remove the application manually, quit Syllavox and delete the extracted
portable application folder. This does not remove local settings, logs, or
downloaded voices. To remove those as well, close Syllavox and delete the
corresponding contents of
`%LOCALAPPDATA%\Syllavox\`. WAV files saved elsewhere are not
removed by this action.

## Troubleshooting

### The application says that no voices are available

Open the window, select **Find more voices...**, and install at least one
voice. Voice models are not included in the public download.

### The tray icon is not visible

Check the Windows notification area and its hidden-icons menu. Syllavox starts
minimized to the tray by default. You can open the window from the tray menu.

### A voice does not work

Try another voice first. Some voices have language-specific requirements or
model limitations. When reporting the problem, include the exact voice ID and
language, but do not attach the model files.

### A Chinese voice takes longer the first time

Some Chinese voices need Piper's `g2pW` resource. Keep the application open
while it downloads and try again after the download completes.

### The hotkey does nothing

Make sure Syllavox is running and that another application has not claimed the
configured shortcut. Open **Settings** to see or change the **Read hotkey**.

### The browser extension reports that Syllavox is not running

Start Syllavox before using the context-menu command. The extension only
communicates with the local application and cannot synthesize speech by
itself.

## Release scope and limitations

Version 0.7.0 extends the focused desktop MVP with:

- one universal portable Windows distribution, including Chinese support;
- no bundled voice models;
- no conventional installer or automatic updater;
- Chrome and Edge extension support;
- experimental Firefox support;
- local HTTP API for integrations;
- conservative speech-text normalization for common pasted markup and Unicode
  formatting artifacts;
- runtime-aware Piper language-compatibility diagnostics;
- complete local-data cleanup for Syllavox-managed data;
- a configurable global read hotkey with conflict-safe re-registration;
- a minimal, smooth visual refresh for the main window, settings, and icon;
- an optional Sherpa-ONNX backend with curated non-Piper Kokoro, Matcha,
  KittenTTS, VITS, and Supertonic bundles;
- optional Sherpa Mimic3 VITS voices for Afrikaans, Bengali, Gujarati, and
  Tswana;
- Sherpa model discovery, atomic installation, language-aware voice selection,
  bundle loading/unloading, deletion, diagnostics, and native WAV output;
- an optional Windows SAPI backend that discovers installed system voices,
  uses readable language labels, and renders through a backend-neutral system
  speech provider boundary;
- read-only management for Windows-owned system voices, with no model files
  downloaded or deleted by Syllavox;
- no playback queue; new requests interrupt current playback.
- a shared macOS adaptation with built-in system speech, AppKit hotkeys,
  per-user startup registration, and a native `.app` packaging path;
- platform-specific macOS ZIP/DMG/checksum build tooling, with signing and
  notarization hooks;
- an Ubuntu-first Linux adaptation with XDG data/startup paths, X11 and
  Wayland global-hotkey adapters, optional eSpeak NG system voices, and `.deb`
  and AppImage packaging scaffolding.

The maximum text length setting defaults to 1,000 characters and can be
increased to 10,000. The upper bound is a practical safeguard for the current
single-request speech workflow, not a Piper engine limitation; reading
sessions and chunked long-form playback remain deferred until after 1.0.0.

The macOS and Linux artifacts require native builds and manual verification on
their target systems. Piper remains the default backend. The base portable
build stays Piper-only to minimize download size; Sherpa and system-voice
builds are explicit variants, while voice models are always downloaded
separately.
Reading sessions and a dedicated accessibility-first reading interface remain
deferred until after 1.0.0.
The internal import package is `syllavox`, and application data is stored in
the current Syllavox data directory.

## Feedback and support

Please read the [public feedback guide](PUBLIC_FEEDBACK.md) before reporting a
problem. It explains what to test and which details are useful while avoiding
the submission of private text or voice files.

For Syllavox questions, support, or project contact, email
`rcresb@gmail.com`.

- [Report a bug](.github/ISSUE_TEMPLATE/bug_report.md)
- [Report a voice compatibility problem](.github/ISSUE_TEMPLATE/voice_compatibility.md)
- [Suggest an improvement](.github/ISSUE_TEMPLATE/feature_request.md)
- [Security policy](SECURITY.md)
- [Contribution guide](CONTRIBUTING.md)
- [Third-party notices and licensing](THIRD_PARTY_NOTICES.md)

## For developers

The published Python package and internal import package are both named
`syllavox`. The application-data directory and IPC names also use Syllavox.

From the project directory on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,packaging]"
python -m syllavox.main
pytest
```

For Windows SAPI development or a SAPI-enabled portable build, install the
optional bridge as well:

```powershell
python -m pip install -e ".[dev,packaging,sapi]"
.\packaging\build_portable.ps1 -IncludeSapi
```

On macOS 11 or later, Python 3.10 and 3.11 are supported. Python 3.10 is a
useful choice when other installed packages require it; the development and
packaging extras install the `tomli` TOML backport needed by Python 3.10.
Do not try to install a package named `tomllib`: `tomllib` is built into
Python 3.11+, while `tomli` supplies the compatible backport for Python 3.10.
The macOS dependency set pins Piper to 1.7.0 and ONNX Runtime to 1.19.2 so
pip does not select the incompatible legacy `piper-phonemize` path or a newer
ONNX Runtime without the required macOS/architecture wheel.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,packaging,macos]"
pytest
bash packaging/build_macos.sh --skip-dmg
```

If Python 3.11 is installed and preferred, replace `python3.10` with
`python3.11`. The build script creates the native `.app`, ZIP, and checksum
under `build/macos/`; use `--include-sherpa` for an optional Sherpa-enabled
variant.

On Ubuntu 22.04/24.04 or a compatible Linux environment, install the native
tools and optional Linux integration packages:

```bash
sudo apt update
sudo apt install espeak-ng python3-venv dpkg-dev
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,packaging,linux]"
pytest
python -m syllavox.main
```

The base Linux runtime uses Piper and does not require eSpeak NG. Installing
`espeak-ng` makes **Linux system voices (eSpeak NG)** available in Settings.
The native Linux build script creates an architecture-specific Debian package
and, when `appimagetool` is installed, an AppImage:

```bash
bash packaging/build_linux.sh --skip-appimage
# or, after installing appimagetool:
bash packaging/build_linux.sh
```

Use `--include-sherpa` for a Sherpa-enabled Linux variant. The Linux build
must run on Linux because PyInstaller collects Linux Qt/native libraries and
the package tools cannot produce a native Linux artifact on Windows or macOS.

The local API listens on `http://127.0.0.1:8765` and provides `/v1/status`,
`/v1/speak`, `/v1/stop`, `/v1/pause`, `/v1/resume`, and `/v1/voices`.

The application uses Piper behind a backend-neutral TTS interface. An
optional Sherpa-ONNX backend is available behind the `sherpa` dependency and
the **Sherpa-ONNX** Settings choice. On Windows, an optional system-speech
provider is available behind the `sapi` dependency and the **Windows SAPI**
Settings choice. On macOS, install the `macos` extra to enable the AppKit and
Service Management adapters and choose **macOS system voices**. On Linux,
install the `linux` extra for X11/Wayland hotkey integration and install the
host `espeak-ng` package when Linux system voices are wanted. See the
[Sherpa-ONNX guide](docs/sherpa-onnx-experimental.md) for setup, catalogs,
model bundles, and benchmarking. The [future language model candidates](docs/sherpa-onnx/future-language-model-candidates.md)
document tracks models that may be integrated later. See the project-level
[future-version roadmap](docs/future-version-roadmap.md) for planned work and
release sequencing.

## License

Syllavox source code is released under the [MIT License](LICENSE). The
portable application contains third-party components with their own licenses;
see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing it.
Voice models are separate works and are governed by their own model-card and
dataset terms.
