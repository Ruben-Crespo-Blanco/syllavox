# Public feedback guide

Thank you for testing Syllavox 1.0.0. This guide is for people testing the
supported Windows path or the
best-effort macOS and Ubuntu paths, including people who do not work with
Python or source code.

## What to test first

The basic test takes about ten minutes:

1. Install the recommended artifact for your operating system and start it.
2. Open the window from the tray or menu-bar icon.
3. Follow **Quick setup** and try the sample with an available system voice.
4. Open **Choose an offline voice...** and inspect the recommended voice; a
   download is optional for this test.
5. Enter two short paragraphs and select **Speak**.
6. Try previous, replay, next, and sentence/paragraph navigation.
7. Stop on the second unit, close and reopen the window, and confirm the text
   and highlighted position return.
8. Copy a sentence in another application and test `Ctrl+Alt+R`.
9. Try **Pause**, **Resume**, **Stop**, and **Export WAV...**.

If you use a browser, also test selecting text and choosing **Read selected
text locally** from the context menu. The application must be running first.

If you use another language, install and test one voice for that language. A
Chinese voice may download the additional `g2pW` resource on first use.

## What to report

Please report both failures and confusing or unexpectedly good behavior. The
most useful information is:

- Syllavox version, normally `1.0.0` or a named development revision;
- operating system, version, architecture, and desktop session where relevant;
- exact voice ID and language;
- how you started speech: window, hotkey, browser, or API;
- what you expected;
- what happened instead;
- the exact error message, if one appeared;
- whether trying another voice changed the result.

Use the appropriate issue template:

- [Bug report](.github/ISSUE_TEMPLATE/bug_report.md)
- [Voice compatibility report](.github/ISSUE_TEMPLATE/voice_compatibility.md)
- [Feature request](.github/ISSUE_TEMPLATE/feature_request.md)

## Protect your privacy

Do not include the text you were reading if it is personal, confidential, or
copyright-sensitive. Replace it with a short neutral example that shows the
same problem.

Before sharing logs or screenshots:

- remove names, addresses, document titles, and private text;
- remove local usernames and paths if they identify you;
- do not attach `.onnx` voice models or the private voice backup;
- do not paste API keys or unrelated application logs.

Syllavox is designed to keep speech local, but a public issue is still visible
to other people. Share only what is necessary to reproduce the behavior.

## Good feedback questions

When the basic test is complete, consider these questions:

- Was it clear how to install the first voice?
- Could you hear the sample without downloading a voice model?
- Was it clear where the application was running when the window was hidden?
- Did the voice selector make language and quality understandable?
- Did the hotkey and browser extension use the voice you expected?
- Was any wait time or error message confusing?
- Which feature would make Syllavox useful in your daily work?
- Which one file format, if any, cannot be handled by copying and pasting?

## Current limitations

Windows is the supported distribution; macOS and Ubuntu have narrower tiers
described in the [support matrix](docs/support-matrix.md). Browser-store review
has not been completed, Firefox remains experimental, and voice models are
downloaded only after the user chooses them. New hotkey, browser, and API
requests interrupt current playback instead of entering a queue. Reading text
and position are restored from the local settings file; **Clear local data and
quit** removes them with other Syllavox-managed data. Exported WAV files saved
elsewhere are not deleted.

For moderated activation and document-format research, use the separate
[research plan](docs/user-research-plan.md) rather than changing this general
feedback script.

## Security reports

Do not use a public issue for a suspected security vulnerability. Follow the
[security policy](SECURITY.md) instead.
