# Syllavox v1.0.0 release notes

Syllavox v1.0.0 is the stable local-first desktop release. It keeps the core
promise simple: select or copy text, press one shortcut, and listen locally
without an account or a cloud speech service.

## Highlights

- Guided Quick setup with sample playback, voice discovery, and shortcut help.
- A permanent **Run setup again…** action that reopens onboarding without
  replacing saved reading content.
- Automatic operating-system voice fallback when a Piper voice is not yet
  installed. System-owned voices are read-only and cannot be deleted by
  Syllavox.
- Locale-aware Piper recommendations, optional Sherpa-ONNX voices, and
  backend-aware diagnostics.
- Sentence/paragraph navigation, replay, automatic continuation, persistent
  local reading position, and synchronized active-unit highlighting.
- Accessible names and descriptions for the primary setup, voice, editor,
  navigation, state, and feedback controls.
- Local HTTP API v1 and context-menu browser extensions for Chromium and
  Firefox submission packages.
- Windows portable and installer packaging, plus macOS and Ubuntu-first Linux
  packaging paths. See the [support matrix](support-matrix.md) for evidence and
  tier boundaries.

## Distribution and privacy

The public artifacts do not bundle voice models. Voice downloads are initiated
by the user from the documented upstream catalogs, and synthesis remains local
after installation. Syllavox-managed data can be removed from Settings; voices
owned by the operating system remain under the operating system's control.

The Windows portable release is built with SAPI support and includes a SHA-256
sidecar. The Inno Setup definition in `packaging/Syllavox.iss` produces the
per-user installer when compiled with Inno Setup 6. Store publication and
signing remain external release-owner steps; the repository contains the
submission packages and listing copy.

## Upgrade notes

Existing settings, reading text, reading position, and downloaded voices are
preserved. On first launch after upgrade, Quick setup can be completed or
reopened later from the main window. No automatic updater is included.

For feedback, use the [public feedback guide](../PUBLIC_FEEDBACK.md). For
security issues, follow [SECURITY.md](../SECURITY.md).
