# Hear Any Desktop Text—Privately

Syllavox v1.0.0

Syllavox is a local-first desktop read-aloud utility for students and knowledge
workers who listen to text across applications.

Copy or select text, press one shortcut, and listen with a voice available on
your computer. Syllavox does not require an account or send text to a cloud TTS
service.

## One reading workflow

- Enter or paste text in Syllavox.
- Copy text from another desktop application and press `Ctrl+Alt+R`.
- Select text in a supported browser and use **Read selected text locally**.
- Navigate by sentence or paragraph, replay a section, and keep your position.
- Export speech as a local WAV file.

## Start without downloading a model

On supported systems, Syllavox offers voices already installed by the operating
system alongside its default offline voice engine. You can hear the sample
immediately, then install a recommended local neural voice for your language if
you want another sound.

Voice downloads happen only after you choose **Install**. Voice models remain
on your computer and retain their own license terms.

After first launch, **Settings → Help → Run setup again…** reopens the guided
setup and sample without changing saved text or voice choices. Operating-system
voices are selectable but read-only; Syllavox never deletes them.

## Local by design

- Speech generation runs on the computer.
- No account is required.
- The browser extension talks only to the local Syllavox API at `127.0.0.1`.
- Downloaded voices, settings, reading position, and local logs are visible and
  removable.
- **Clear local data and quit** removes Syllavox-managed data.

Syllavox is not a replacement for a screen reader. Its keyboard-accessible
reading workflow may complement assistive technology, and current support
levels are documented in the [support matrix](support-matrix.md).

## Download

- **Windows:** use the per-user installer. It is the recommended and most
  established distribution.
- **macOS:** use the architecture-matched application ZIP or DMG when published.
- **Ubuntu Linux:** use the `.deb`; use AppImage when installation is not
  appropriate.

Always download from the official GitHub Releases page and compare the adjacent
SHA-256 file when one is published. See the main [README](../README.md) for
current availability and detailed setup.
