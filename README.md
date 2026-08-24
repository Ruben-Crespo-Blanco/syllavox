# Syllavox

Syllavox reads text aloud on your Windows computer using local speech
synthesis. Text is processed on the computer rather than sent to a cloud TTS
service.

This is the public MVP release, version **0.2.0**. It is a Windows portable
application: download it, extract it, and run it. No installer or Python
installation is required for ordinary use.

For the concise public-release summary, see the
[v0.2.0 release notes](docs/release-notes-0.2.0.md).

## Before you start

- Windows is the supported platform for this release.
- The public application does not include voice models. You choose and
  download the voices you want from Piper's official catalog.
- An internet connection is needed to browse and download a voice. Once a
  voice is installed, speech synthesis runs locally.
- Voice models have their own licenses and model-card terms. Review those
  terms before using or redistributing a voice.
- The portable folder is large because it contains the application runtime and
  Chinese-language support. Syllavox uses one universal distribution; there
  are no separate Chinese and non-Chinese builds.

## Install and start Syllavox

1. Download `Syllavox-portable.zip` from the **Releases** page of the public
   GitHub repository.
2. Extract the ZIP to a folder of your choice. Do not try to run the program
   from inside the ZIP file.
3. Open the extracted `Syllavox` folder and double-click `Syllavox.exe`.
4. Syllavox starts in the Windows notification area (system tray). Use the
   tray icon to open the main window.

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

Voices are downloaded from the official
[Piper voice catalog](https://huggingface.co/rhasspy/piper-voices). Syllavox
does not include the project's complete developer voice backup in public
releases.

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
instead. The selected voice and playback preferences are shared by the window,
hotkey, and local API.

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
- voice downloads come from the official Piper catalog when you explicitly
  install a voice.

The application stores runtime data under:

```text
%LOCALAPPDATA%\Syllavox\
```

| Location | Contents |
|---|---|
| `settings.json` | Application and playback settings |
| `logs\app.log` | Local diagnostic and lifecycle logs |
| `models\piper\` | Downloaded Piper voice model pairs |
| `models\piper\g2pW\` | Chinese phonemization data when needed |
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

Some Hebrew Piper voices currently fail while loading with
`hebrew is not a valid phoneme type`. v0.2.0 classifies unsupported language
phonemizers explicitly and reports the affected voice/runtime combination;
include the exact voice ID when reporting a remaining compatibility problem.

### A Chinese voice takes longer the first time

Some Chinese voices need Piper's `g2pW` resource. Keep the application open
while it downloads and try again after the download completes.

### The hotkey does nothing

Make sure Syllavox is running and that another application has not claimed
`Ctrl+Alt+R`. The hotkey action can be changed in the Syllavox settings.

### The browser extension reports that Syllavox is not running

Start Syllavox before using the context-menu command. The extension only
communicates with the local application and cannot synthesize speech by
itself.

## Release scope and limitations

Version 0.2.0 extends the focused Windows MVP with:

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
- no playback queue; new requests interrupt current playback.

macOS and Linux versions, a more polished interface, broader language-specific
compatibility work, and additional TTS backends remain future work. Kokoro TTS
is planned as a future backend and voice source.
The internal import package is `syllavox`, and application data is stored in
the current Syllavox data directory.

## Feedback and support

Please read the [public feedback guide](PUBLIC_FEEDBACK.md) before reporting a
problem. It explains what to test and which details are useful while avoiding
the submission of private text or voice files.

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

The local API listens on `http://127.0.0.1:8765` and provides `/v1/status`,
`/v1/speak`, `/v1/stop`, `/v1/pause`, `/v1/resume`, and `/v1/voices`.

The application uses Piper behind a backend-neutral TTS interface. See the
project-level [future-version roadmap](docs/future-version-roadmap.md) for
planned work and release sequencing.

## License

Syllavox source code is released under the [MIT License](LICENSE). The
portable application contains third-party components with their own licenses;
see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing it.
Voice models are separate works and are governed by their own model-card and
dataset terms.
