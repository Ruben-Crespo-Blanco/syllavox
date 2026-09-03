# Support Matrix

**Updated:** 3 September 2026

Support labels describe the evidence available for the current v1.0.0 release.
They do not imply that every voice model or desktop configuration works.

| Area | Tier | Recommended path | Current evidence / limitation |
|---|---|---|---|
| Windows 10/11, x64 | Supported | Per-user installer containing Piper and Windows system-voice support | Established packaging and automated coverage; final release candidates still require a clean-machine smoke test. |
| Windows portable | Supported | Release portable ZIP built with `-IncludeSapi` | Useful where installation is not allowed; the base developer build remains Piper-only, and settings/models stay in local application data. |
| macOS 11+, Apple silicon | Best effort | Native `.app` ZIP or DMG | Native build path has been validated; screen-reader, hotkey-permission, and release-candidate checks remain manual. |
| macOS 11+, Intel | Experimental | Architecture-matched `.app` ZIP or DMG | Build support exists, but current evidence is insufficient for the same support promise as Windows. |
| Ubuntu 22.04/24.04, amd64 | Best effort | `.deb`; AppImage as a portable alternative | CI builds and launches an AppImage; X11/Wayland, tray, audio, and package installation still need release-candidate desktop testing. |
| Ubuntu 22.04/24.04, arm64 | Experimental | Native `.deb` when published | Packaging supports arm64, but native-hardware validation is still required. |
| Other Linux distributions | Experimental | Source checkout | Qt, audio, tray, portal, package, and dependency behavior vary by distribution. |
| Piper voices | Supported | Recommended locale-matching catalog voice | Model quality and upstream availability vary; no voice models are bundled. |
| Windows/macOS system voices | Supported on their supported OS tier | Automatically offered with the default Piper workflow when available | Voice installation and removal remain owned by the operating system. |
| Linux eSpeak NG voices | Best effort | Install the host `espeak-ng` package | Availability and quality depend on the distribution package. |
| Sherpa-ONNX | Experimental | Explicit optional build and curated bundles | Larger optional runtime and model-specific compatibility burden. |
| Chrome / Edge extension | Ready for store submission | Store package after approval | Submission ZIP and checksums are built in CI; no store availability claim is valid until review completes. |
| Firefox extension | Experimental | Signed AMO package after approval | A stable extension ID and submission ZIP exist; permanent installation still requires external signing/review. |
| Local HTTP API v1 | Supported | Loopback `127.0.0.1:8765` integration | Local integrations only; new speech requests interrupt current playback. |

## Support policy

- Fix regressions on supported paths before expanding experimental paths.
- Accept reproducible reports for every tier, but do not promise equal response
  time or platform parity.
- Promote a tier only after its native install, first speech, hotkey, playback,
  clean exit, and accessibility checklist pass on a release candidate.
- Downgrade a tier when a known platform change breaks the primary workflow and
  no maintained fix is available.
