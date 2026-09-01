# Contributing to Syllavox

Thank you for taking an interest in Syllavox. The project is a
local text-to-speech application maintained as a small side project.

Version 0.6.0 adds the first macOS adaptation while preserving the validated
Windows SAPI installer path, Sherpa language coverage, hardening work, Piper
and Sherpa voices, a shared local speech pipeline, browser-selected text,
configurable clipboard hotkeys, polished Qt windows, and a local API.
Contributions should preserve
that local-first behavior unless a change is explicitly discussed first.

## Before you start

For a bug, voice problem, or feature idea, please check the existing issues and
use the appropriate template:

- [Bug report](.github/ISSUE_TEMPLATE/bug_report.md)
- [Voice compatibility report](.github/ISSUE_TEMPLATE/voice_compatibility.md)
- [Feature request](.github/ISSUE_TEMPLATE/feature_request.md)

For a substantial change, open an issue before writing code. This helps avoid
duplicated work and makes it possible to agree on the scope.

## Development setup

Windows remains a fully supported development and distribution target. From
the project directory on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,packaging]"
```

To develop or package the Windows SAPI backend, include the optional bridge:

```powershell
python -m pip install -e ".[dev,packaging,sapi]"
```

Run the application with:

```powershell
python -m syllavox.main
```

Run the automated tests with:

```powershell
pytest
```

The macOS adaptation must be developed and packaged on macOS (or a macOS CI
runner), because the native SDK tools and system speech commands are not
available on Windows. On macOS, use:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,packaging,macos]"
pytest
bash packaging/build_macos.sh --skip-dmg
```

The supported Qt 6.5-compatible macOS baseline is macOS 11. Use Python 3.11
for the broadest compatible development environment; Python 3.10 is also
supported, with `tomli` supplied by the development and packaging extras for
the missing standard-library TOML module. The shared project metadata pins
macOS to Piper 1.7.0 and ONNX Runtime 1.19.2; this avoids the legacy
`piper-phonemize` dependency path and newer ONNX Runtime wheels that may not
support the Mac's OS or architecture.

Add `--include-sherpa` when building the optional Sherpa-ONNX variant. The
macOS script writes app, archive, and checksum artifacts under `build/macos/`;
do not commit generated output.

The browser extension has its own JavaScript checks. From the `extension\`
directory, run `npm test` when working on the extension.

## Building the Windows installer

The installer is built from the SAPI-enabled portable folder with Inno Setup
6. Install Inno Setup so `ISCC.exe` is available on `PATH`, or set the
`INNO_SETUP_COMPILER` environment variable to its full path. Then run:

```powershell
.\packaging\build_installer.ps1
```

This first builds the standard Piper/SAPI portable artifact and writes the
installer to `build\installer\`. To include the optional Sherpa runtime as
well, run:

```powershell
.\packaging\build_installer.ps1 -IncludeSherpa
```

Use `-SkipPortableBuild` when the matching portable folder has already been
built. The installer is per-user and does not require administrator rights.
Do not commit generated `build\` output.

## Working principles

- Keep speech synthesis and playback local.
- Keep the public application behind the backend-neutral TTS interface.
- Route desktop, hotkey, browser, and API requests through the shared speech
  pipeline.
- Avoid adding cloud services, telemetry, or hidden downloads.
- Do not commit downloaded voice models, model backups, generated WAV files,
  logs, secrets, or local virtual-environment files.
- Preserve the `syllavox` Python package and Syllavox runtime identifiers.
- Add or update tests for behavior changes.
- Update user documentation when an installation, privacy, or visible
  behavior changes.

## Voice and language contributions

Voice models are separate works with individual model-card and dataset terms.
Do not add voice model files to the repository or release assets.

For a voice compatibility report, include the exact voice ID, language,
quality, and error classification. If you propose a language-specific fix,
also explain which runtime dependency or resource it affects and whether the
change works without that voice installed.

## Pull requests

A useful pull request should:

1. Explain the user-visible problem or goal.
2. Describe the behavior change and any compatibility impact.
3. Include focused tests or explain why tests are not practical.
4. Update documentation when needed.
5. State what was manually tested.

Keep changes focused. Avoid mixing unrelated formatting, refactoring, or
generated files into a feature or bug-fix pull request.

Before submitting, run the relevant automated tests and inspect the working
tree for accidental model files, logs, build output, or secrets.

## Documentation and feedback

Clear instructions and reports from people who are not developers are
especially valuable. The [public feedback guide](PUBLIC_FEEDBACK.md) describes
the current test flow and the information that is useful to maintainers.

## Licensing

Syllavox source code is released under the MIT License. Contributions should
be compatible with that license. Do not assume that a third-party voice,
image, font, code sample, or dependency has compatible terms; record its
source and license before proposing it.
