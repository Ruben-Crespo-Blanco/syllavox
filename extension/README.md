# Syllavox browser extension

The Syllavox browser extension lets you select text on a webpage and send it
to the Syllavox desktop application for local speech synthesis.

The extension does not synthesize speech itself and does not send selected
text to a cloud service. Syllavox must be running on the same computer.

For the main application guide, see the [project README](../README.md).

## Supported browsers

| Browser | Status |
|---|---|
| Google Chrome | Supported |
| Microsoft Edge | Supported |
| Mozilla Firefox | Experimental; temporary installation |

The 0.2.0 release does not provide a signed browser-store extension. Chrome
and Edge use an unpacked extension installation. Firefox temporary add-ons
must be loaded again after Firefox restarts.

## Before installing

1. Download or clone the Syllavox project.
2. Start the Syllavox desktop application.
3. Confirm that at least one voice is installed and works from the main
   window.

## Install in Chrome

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode**.
3. Select **Load unpacked**.
4. Choose the project's `extension` folder.
5. Keep Syllavox running.

## Install in Microsoft Edge

1. Open `edge://extensions` in Edge.
2. Turn on **Developer mode**.
3. Select **Load unpacked**.
4. Choose the project's `extension` folder.
5. Keep Syllavox running.

## Install temporarily in Firefox

1. Open `about:debugging` in Firefox.
2. Select **This Firefox**.
3. Select **Load Temporary Add-on...**.
4. Choose `manifest.firefox.json` from the project's `extension` folder.
5. Keep Syllavox running.

Firefox removes temporary add-ons when it restarts. Repeat these steps after a
restart.

For a staged Firefox package, run this command from the `extension` folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\package_firefox.ps1
```

The script creates a temporary Firefox folder and ZIP under `build\firefox\`.
This is a testing package, not a signed permanent Firefox distribution.

## Use the extension

1. Start Syllavox.
2. Open a webpage.
3. Select some text.
4. Right-click the selection.
5. Choose **Read selected text locally**.

The Syllavox application uses the voice selected in its desktop window. New
requests interrupt current playback; the extension does not provide a queue or
separate voice selector.

## Troubleshooting

### The menu command is missing

Select text before opening the context menu. If you recently changed the
extension files, reload the extension from the browser's extension page.

### The extension says that Syllavox is not running

Start Syllavox and try again. The extension communicates with the local API at
`http://127.0.0.1:8765`.

### The application is running but speech fails

Test speech from the Syllavox window first. Confirm that a voice is installed,
then try another voice. When reporting the problem, include the exact voice ID
and error message without sharing private text or model files.

### Firefox stops working after a restart

This is expected for a temporary add-on. Load `manifest.firefox.json` again
from `about:debugging`.

## Privacy

The extension sends selected text only to the Syllavox application on the same
computer. It uses the local API and does not send selected text to a remote
speech service.

## For extension developers

From this directory, run the automated extension checks with:

```powershell
npm test
```

These tests mock browser APIs. They complement, but do not replace, manual
testing in Chrome, Edge, and Firefox.
