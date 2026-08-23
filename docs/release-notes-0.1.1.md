# Syllavox v0.1.1 release notes

Syllavox v0.1.1 is a maintenance release for the Windows portable MVP. It
keeps the v0.1.0 user-facing behavior and focuses on making the project and
release process easier to reproduce.

## Included

- Consistent `0.1.1` version metadata across the Python project, runtime, and
  Chrome/Edge and Firefox extension manifests.
- A declared `dev` optional dependency for installing the pytest test runner.
- Release metadata regression coverage.
- Updated documentation and portable-build text for v0.1.1.

## Unchanged scope

This release does not introduce reading sessions, a redesigned
accessibility-first interface, additional TTS backends, or macOS/Linux
support. Those remain future roadmap work.

The existing v0.1.0 limitations also remain: Windows is the supported
platform, the public distribution is portable rather than installer-based,
Firefox support is experimental, voice models are installed separately, and
new speech requests interrupt current playback instead of entering a queue.

## Development checks

From the project directory on Windows:

```powershell
python -m pip install -e ".[dev,packaging]"
pytest
```

The portable build continues to exclude user voice models and includes the
project's license, third-party notices, changelog, and dependency inventory.
