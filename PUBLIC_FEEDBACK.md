# Public feedback guide

Thank you for testing Syllavox 0.1.0. This guide is for people trying the
public Windows MVP, including people who do not work with Python or source
code.

## What to test first

The basic test takes about ten minutes:

1. Extract the portable ZIP and start `Syllavox.exe`.
2. Open the window from the tray icon.
3. Install one English voice through **Find more voices...**.
4. Enter a short sentence and select **Speak**.
5. Try changing the voice and speaking again.
6. Copy a sentence and test `Ctrl+Alt+R`.
7. Try **Pause**, **Resume**, **Stop**, and **Export WAV...**.
8. Quit and restart Syllavox.

If you use a browser, also test selecting text and choosing **Read selected
text locally** from the context menu. The application must be running first.

If you use another language, install and test one voice for that language. A
Chinese voice may download the additional `g2pW` resource on first use.

## What to report

Please report both failures and confusing or unexpectedly good behavior. The
most useful information is:

- Syllavox version, normally `0.1.0`;
- Windows version;
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
- Was it clear where the application was running when the window was hidden?
- Did the voice selector make language and quality understandable?
- Did the hotkey and browser extension use the voice you expected?
- Was any wait time or error message confusing?
- Which feature would make Syllavox useful in your daily work?

## Current limitations

The 0.1.0 release is a Windows portable MVP. It has no installer or automatic
updater, Firefox support is experimental, voice models are downloaded by the
user, and new speech requests interrupt current playback instead of entering a
queue.

## Security reports

Do not use a public issue for a suspected security vulnerability. Follow the
[security policy](SECURITY.md) instead.
