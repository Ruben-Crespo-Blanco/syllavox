# Syllavox v0.4.1 release notes

Syllavox v0.4.1 is a hardening release after the v0.4.0 Sherpa-ONNX
integration. It keeps Piper as the default and prepares the codebase for
future macOS and Linux platform work.

## Included

- Platform boundaries for global hotkeys, user-data paths, and single-instance
  locking.
- Cross-platform data-root conventions for Windows, macOS, and Linux/Unix
  development environments.
- Deterministic release of cached Piper and Sherpa model resources when the
  application exits.
- Dependency and portable-build inventory tooling at
  `scripts/audit_runtime.py`.
- Regression coverage for platform selection, runtime cleanup, and path
  resolution.
- Clearer Hebrew Piper compatibility documentation based on the latest manual
  test.

## Portable-build changes

The PyInstaller specification now excludes optional download acceleration,
development tooling, and Qt module families that Syllavox does not import.
Required QtCore, QtGui, QtNetwork, QtMultimedia, and QtWidgets components are
retained. The Piper-only build remains separate from the optional Sherpa
runtime.

The measured Piper-only portable baseline is recorded in
`docs/portable-size-audit-0.4.1-piper.md`. A Sherpa-enabled build has its own
larger runtime footprint and remains opt-in. The current measurements are
325.4 MiB unpacked for Piper-only and 352.8 MiB for Sherpa-enabled, with 3,189
and 3,207 files respectively.

## Validation

The release was checked with the automated regression suite, platform seam
tests, clean portable launch validation, and representative Piper/Sherpa
speech-generation tests. Model files are not included in the application
package and retain their own licenses and dataset terms.

## Unchanged scope

Reading sessions and the accessibility-first reading interface remain deferred
until after 1.0.0. macOS is planned for v0.5.0, Linux for v0.6.0, and an
Android/mobile application remains planned after 1.0.0.
