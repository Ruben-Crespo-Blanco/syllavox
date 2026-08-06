# Syllavox Future-Version Roadmap

This roadmap maps planned development to proposed versions. The version
assignments are planning targets, not commitments. The current public target
is the Windows MVP, version 0.1.0.

## Version plan

| Version | Focus | Planned development |
|---|---|---|
| **0.1.0** | Windows MVP | Portable Windows build, Piper voices, voice installation/deletion, hotkey, local API, browser extensions, diagnostics, temporary WAV cleanup, public documentation, and MIT release. |
| **0.1.1** | Maintenance | Fix issues found during manual and early public testing; improve packaging, documentation, and voice-specific bugs without adding major features. |
| **0.2.0** | Compatibility and privacy | Investigate other language-specific Piper failures, improve text/read formatting, and add complete local-data cleanup for logs, settings, retained WAVs, models, and `g2pW` data. |
| **0.3.0** | UI/UX | Overhaul the front end, improve layout and visual design, clarify voice/model management, and improve feedback during loading, synthesis, and errors. |
| **0.4.0** | Additional TTS backend | Add Kokoro TTS support, including voice discovery, installation, selection, loading/unloading, deletion, and backend-specific diagnostics. |
| **0.5.0** | macOS adaptation | Add macOS platform services, global hotkeys, single-instance handling, tray behavior, audio validation, packaging, and manual testing. |
| **0.6.0** | Linux adaptation | Add Linux platform services, hotkeys, tray integration, packaging, distribution testing, and documented supported environments. |
| **1.0.0** | Stable multi-platform release | Consolidate supported platforms, resolve major compatibility issues, stabilize APIs and settings, add a complete user-facing installer, complete release documentation, and establish a reliable feedback and maintenance process. |

### Known language-specific compatibility issue

- **Hebrew Piper voices:** loading currently fails with `hebrew is not a
  valid phoneme type`. Investigate the voice configuration and Piper phoneme
  support, identify whether the problem affects all Hebrew voices or only
  specific models, and add a diagnostic/manual compatibility check before
  attempting a fix.

## Long-term backlog

- Alternative voice-catalog hosting or mirrors if Hugging Face becomes
  unavailable.
- Additional TTS backends beyond Piper and Kokoro.
- Further distribution improvements beyond the 1.0.0 installer.
- Broader automation and integration support.
- A phone application or mobile companion app.

## Planning principles

- Keep the universal Piper voice approach rather than maintaining separate
  distributions for different language groups.
- Do not bundle voice models in public distributions unless their licensing
  and maintenance requirements make that appropriate.
- Treat voice models and their model-card terms as separate from the
  Syllavox source-code license.
- Use public feedback and real-world voice compatibility reports to prioritize
  maintenance releases.

## Final 0.1.0 release step: public outreach and feedback

After the release build and manual verification are complete, share Syllavox
selectively to find initial users and actionable feedback. Use one canonical
GitHub release page and one GitHub Discussions thread as the source of truth;
community posts should link back to those pages rather than creating separate
support channels.

### Recommended order

1. **GitHub Discussions — primary feedback hub.** Enable Discussions in the
   public repository and create a clearly labelled `0.1.0 feedback` thread.
   Use Discussions for questions, announcements, ideas, and user experience
   reports; use Issues for reproducible bugs and concrete tasks. See the
   [GitHub Discussions quickstart](https://docs.github.com/en/discussions/quickstart)
   and [GitHub communication guidance](https://docs.github.com/en/get-started/using-github/communicating-on-github).

2. **r/TextToSpeech and r/opensource — first external posts.** These are the
   most direct initial audiences for a local Piper-based text-to-speech tool
   and an open-source Windows application. Post a concise project
   announcement, explain what is ready to test, and ask for specific feedback
   rather than making a general promotion post. Re-check each community's
   rules immediately before posting.

3. **NVDA User Group, r/AssistiveTechnology, and r/Blind — targeted
   accessibility testing.** Approach these communities respectfully and only
   where their rules permit it. Explain that Syllavox is seeking voluntary
   testing from people who use screen readers or other assistive workflows;
   do not assume that community members owe the project testing or support.
   The [NVDA User Group](https://groups.google.com/a/nvaccess.org/g/nvda-users)
   is a particularly relevant place to monitor and, if appropriate, ask for
   feedback.

4. **AlternativeTo — software discovery.** Submit Syllavox after the public
   repository and download instructions are stable, linking to the official
   release. The [AlternativeTo FAQ](https://alternativeto.net/faq//) notes that
   new accounts may need to wait before submitting a new app, so this should
   not be treated as the first feedback channel.

5. **r/software, r/selfhosted, and r/windows — secondary discovery.** Use
   these only when the post is genuinely useful to the community: for example,
   local/offline operation, the Windows portable build, or the local API. Do
   not cross-post identical promotional text everywhere.

6. **Hacker News Show HN — optional later outreach.** Consider this only when
   the release is easy to try and the maintainer can participate in the
   discussion. The [Show HN guidelines](https://news.ycombinator.com/showhn.html)
   ask for something people can try and explicitly discourage asking for
   upvotes or comments. Build familiarity with the community before posting;
   the [current Show HN notice](https://news.ycombinator.com/showlim) advises
   prospective submitters to participate before launching.

7. **Product Hunt — optional broader launch.** Reserve this for a later,
   polished presentation with a short demo and clear screenshots. It is useful
   for maker and product discovery, but is less targeted than the TTS and
   accessibility communities. Follow the [Product Hunt launch guide](https://www.producthunt.com/launch)
   and its [sharing guidance](https://www.producthunt.com/launch/sharing-your-launch),
   including the prohibition on manipulating votes.

### Outreach checklist

- Describe Syllavox as a Windows v0.1.0 portable release and state its current
  limitations plainly.
- Link to the GitHub release, download instructions, `PUBLIC_FEEDBACK.md`,
  and the feedback discussion.
- Ask for bounded feedback: installation, first launch, hotkey use, browser
  extension use, voice downloads, pronunciation, resource usage, and language
  compatibility.
- Ask testers not to share private source text, voice files, or unredacted
  logs. Encourage sanitized reports through the documented feedback channel.
- Track recurring reports as GitHub Issues, summarize what is being learned,
  and thank contributors. Re-check community rules before every post because
  they can change.

Do **not** use r/accessibility as a direct launch channel without a rule change
or moderator approval: its current rules prohibit tool promotion and feedback
requests. Review the [r/accessibility rules](https://www.reddit.com/r/accessibility/)
before considering any participation there.
