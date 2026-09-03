# Security policy

Syllavox is a local desktop application with a supported Windows path and
narrower macOS/Linux support tiers. Its speech API listens on `127.0.0.1`, and
the browser extension communicates with that local address. The application
uses the internet when a user explicitly browses or downloads voices from an
upstream catalog.

## Supported versions

The current public release is:

| Version | Supported |
|---|---|
| Current `1.0.x` release | Yes |
| `0.7.x` and earlier | No |

The project is a small side project, so response times cannot be
guaranteed. Security reports will be reviewed as soon as practical.

## Reporting a vulnerability

Please do not publish security vulnerabilities in a public GitHub issue.

Use the repository's **Private vulnerability reporting** or **Security
Advisory** feature when it is enabled. If that feature is not yet available,
contact the maintainer privately through the GitHub profile associated with
the repository and explain that the message is a security report. Do not send
exploit details, private text, or unredacted logs in a public channel.

Useful information includes:

- the affected Syllavox version;
- operating system, version, architecture, and desktop session where relevant;
- whether the report concerns the portable application, API, or browser
  extension;
- clear reproduction steps;
- the expected and observed behavior;
- a minimal proof of impact, when safe to provide.

Please allow time for the report to be investigated before public disclosure.

## What is in scope

Examples of security issues include:

- a release artifact containing unexpected executable or data files;
- selected text being sent somewhere other than the local application without
  the user's action;
- the local API accepting unsafe commands or exposing data beyond its intended
  local scope;
- a browser extension path allowing unrelated websites to control the
  application unexpectedly;
- unsafe handling of downloaded voice or configuration files;
- a release artifact or update instruction that can be replaced or tampered
  with in a misleading way.

## What is normally not a security vulnerability

The following are usually product or compatibility issues:

- a voice pronouncing text incorrectly;
- a voice failing because its model or language resource is incompatible;
- a missing voice model;
- an application crash that does not expose data or allow unintended control;
- a request being interrupted because Syllavox has no playback queue.

These reports are welcome through the normal [feedback guide](PUBLIC_FEEDBACK.md)
and issue templates.

## Privacy when reporting

Syllavox handles user-provided text. Before sharing screenshots, logs, or
reproduction text, remove personal, confidential, or identifying information.
Never attach voice model files unless the maintainer explicitly asks for a
small, legally shareable sample or metadata instead.
