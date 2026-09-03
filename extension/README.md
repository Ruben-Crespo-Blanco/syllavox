# Syllavox browser extension

This extension is compatible with the Syllavox v1.0.0 desktop release.

The Syllavox browser extension lets you select text on a webpage and send it
to the Syllavox desktop application for local speech synthesis.

The extension does not synthesize speech itself and does not send selected
text to a cloud service. Syllavox must be running on the same computer.

For the main application guide, see the [project README](../README.md).

## Supported browsers

| Browser | Status |
|---|---|
| Google Chrome | Submission package ready; store review pending |
| Microsoft Edge | Submission package ready; store review pending |
| Mozilla Firefox | Experimental; signed-store review pending |

The repository produces minimal-permission Chromium and Firefox submission
ZIPs, but no browser-store listing should be claimed until external review is
complete. Until then, Chrome and Edge use an unpacked development install and
Firefox uses a temporary development install.

Store descriptions, permission justifications, and data disclosure are in
the [store listing copy](../docs/STORE_LISTING.md).

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

For staged Chromium and Firefox packages, run these commands from the
`extension` folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\package_chromium.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\package_firefox.ps1
```

The scripts create staged folders, ZIPs, and SHA-256 files under
`build\chromium\` and `build\firefox\`. CI publishes the same outputs as a
workflow artifact. These are submission/testing packages, not signed permanent
store distributions.

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
speech service. It requests only context-menu, notification, and
`127.0.0.1:8765` permissions; it does not request page-wide, tab, scripting, or
remote-host access.

## For extension developers

From this directory, run the automated extension checks with:

```powershell
npm test
```

These tests mock browser APIs. They complement, but do not replace, manual
testing in Chrome, Edge, and Firefox.
