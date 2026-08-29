# Syllavox Future-Version Roadmap

This roadmap maps planned development to proposed versions. The version
assignments are planning targets, not commitments. The current public release
is the language coverage release, version 0.4.2; the next planned milestone is
v0.5.0.

## Version plan

| Version | Focus | Planned development |
|---|---|---|
| **0.1.0** | Windows MVP | Portable Windows build, Piper voices, voice installation/deletion, hotkey, local API, browser extensions, diagnostics, temporary WAV cleanup, public documentation, and MIT release. |
| **0.1.1** | Maintenance | Fix issues found during manual and early public testing; improve packaging, documentation, and voice-specific bugs without adding major features. |
| **0.2.0** | Compatibility and privacy | Investigate other language-specific Piper failures, improve text/read formatting, and add complete local-data cleanup for logs, settings, retained WAVs, models, and `g2pW` data. |
| **0.3.0** | UI/UX | Remodel the UI with a minimal, smooth, Apple-inspired visual system; redesign the Syllavox icon and application windows; clarify voice/model management; improve feedback during loading, synthesis, and errors; and let users change the global read hotkey. |
| **0.4.0** | Additional TTS backend | Add Sherpa-ONNX as an optional backend while keeping Piper as the default; support curated non-Piper Kokoro, Matcha, KittenTTS, VITS, and Supertonic bundles with discovery, installation, selection, loading/unloading, deletion, language-aware metadata, and diagnostics. |
| **0.4.1** | Hardening and platform preparation | Audit runtime dependencies and portable-build size; remove unnecessary runtime weight without reducing supported features; strengthen Piper/Sherpa lifecycle, packaging, API, and settings regression coverage; verify voice compatibility; and isolate Windows-specific services behind platform boundaries for the macOS work. |
| **0.4.2** | Language coverage | Add carefully validated voices for important languages absent from the active non-Piper catalog, starting with Sherpa-compatible Mimic3 VITS candidates and then evaluating lightweight, legally redistributable conversion candidates for Thai and underserved Indic and long-tail languages. Keep Piper as the fallback and do not add unverified or oversized models. **Shipped:** Afrikaans, Bengali, Gujarati, and Tswana Mimic3 VITS bundles, integrity checks, and validation tooling. |
| **0.5.0** | macOS adaptation | Add macOS platform services, global hotkeys, single-instance handling, tray behavior, audio validation, packaging, and manual testing. |
| **0.6.0** | Linux adaptation | Add Linux platform services, hotkeys, tray integration, packaging, distribution testing, and documented supported environments. |
| **1.0.0** | Stable multi-platform release | Consolidate supported platforms, resolve major compatibility issues, stabilize APIs and settings, add a complete user-facing installer, complete release documentation, and establish a reliable feedback and maintenance process. |

The existing **0.3.0 UI/UX** phase remains focused on a minimal, smooth, and
original visual language inspired by Apple's restraint, spacing, hierarchy, and
motion. It includes an icon refresh, redesigned application windows and
settings surfaces, clearer voice/model management, improved loading, synthesis,
and error feedback, and a user-configurable global read hotkey. The visual
redesign must remain recognizably Syllavox and must not copy Apple's assets or
branding. The hotkey work should retain `Ctrl+Alt+R` as the default, use the
existing parser and registration layer, persist the selected shortcut, and
explain invalid or unavailable shortcuts without leaving the application with a
stale or silently changed binding.
Reading sessions and a dedicated accessibility-first reading interface are
explicitly outside the numbered roadmap and are deferred to an unassigned
future phase after 1.0.0.

### Deferred beyond 1.0.0

- Reading sessions with sentence/paragraph navigation, replay, previous/next
  controls, and a persistent reading position.
- An accessibility-first reading UI with screen-reader-oriented interaction,
  high-contrast behavior, expanded keyboard control, and optional synchronized
  text highlighting.
- Context-agnostic highlighting inside arbitrary browsers, PDFs, Word
  documents, or other host applications.

## v0.4.1 implementation plan

v0.4.1 is a focused hardening release. It should not introduce reading
sessions, a dedicated accessibility-first reading interface, a new speech
backend, or a new platform. Its purpose is to make the current Windows release
smaller, more predictable, and easier to extend to macOS.

### 1. Establish a release baseline

- Record the current Piper-only and Sherpa-enabled portable sizes.
- Inventory startup time, idle memory, loaded-model memory, and representative
  synthesis latency for both backends.
- Record the current direct and transitive runtime dependencies, native DLLs,
  package data, and license files included in each portable variant.
- Run the existing regression suite and real-model Sherpa smoke test, including
  representative Piper voice paths.

### 2. Audit dependencies and portable size

- Classify dependencies as runtime-required, optional backend, packaging-only,
  development-only, test-only, or unused.
- Confirm that development and packaging tools are not included in the frozen
  application runtime.
- Remove unused runtime packages and package data only after verifying import,
  launch, synthesis, API, catalog, and playback behavior.
- Keep Sherpa native libraries out of the Piper-only portable build and verify
  that optional imports remain lazy.
- Inspect PyInstaller collection rules for duplicated Qt, audio, phonemizer,
  or model-support files.
- Preserve required third-party notices and licenses after every reduction.
- Compare the resulting size and resource usage against the baseline; a size
  reduction is preferred, but a justified increase is acceptable if required
  functionality or reliability improves.

### 3. Harden runtime and model lifecycle behavior

- Test Piper and Sherpa backend switching, restart, loading, unloading,
  interruption, pause/resume, temporary WAV cleanup, and application exit.
- Test incomplete bundles, failed downloads, invalid manifests, missing native
  libraries, unsupported voices, and low-resource conditions.
- Run the curated Sherpa smoke test across all catalog entries and retain a
  compact result summary for the release.
- Check that shared Sherpa bundles are loaded once and released completely when
  no voice from the bundle remains active.

### 4. Prepare the platform boundary

- Identify Windows-specific code for paths, hotkeys, tray/menu behavior,
  single-instance enforcement, clipboard/selection, audio playback, and
  restart handling.
- Introduce small platform interfaces or adapters while preserving the current
  Windows behavior and public API.
- Add tests that exercise the platform-neutral contracts without requiring a
  second operating system.
- Leave actual macOS implementation, packaging, and manual testing to v0.5.0.

### 5. Stabilize contracts and documentation

- Add settings-schema migration and backward-compatibility checks.
- Verify the `/v1/voices` and `/v1/speak` response contracts remain stable for
  both backends.
- Remove stale voice warnings from current documentation and document the
  compatibility checks without claiming every future model is guaranteed.
- Publish separate Piper-only and Sherpa-enabled artifact measurements and
  update the v0.4.1 release notes.

### v0.4.1 acceptance criteria

- No unnecessary runtime dependency remains in the portable builds, with the
  before/after inventory recorded.
- Piper-only and Sherpa-enabled builds launch and synthesize correctly on a
  clean Windows machine.
- The portable size and idle/runtime resource impact are measured and either
  reduced or explicitly justified.
- Existing tests, Sherpa smoke tests, lifecycle tests, and voice regression
  checks pass.
- Windows behavior is unchanged behind the new platform boundary.
- The macOS implementation can begin in v0.5.0 without redesigning the core
  TTS, settings, API, or playback contracts.

## v0.4.2 implementation plan

v0.4.2 is a language-coverage release. It should expand access without
replacing Piper, weakening the lightweight product goal, or turning the
catalog into an unverified model directory. The active non-Piper gap list is
maintained in [the future language-model candidate register](sherpa-onnx/future-language-model-candidates.md).

### 1. Confirm the real coverage gaps

- Compare the current Piper and Sherpa catalogs by language, locale, script,
  voice quality, and license.
- Distinguish “no voice at all” from “no non-Piper voice” and “only a
  low-quality or restricted-license candidate.”
- Rank candidates by population impact, script coverage, model maturity,
  redistribution terms, download size, memory use, and native-speaker demand.

### 2. Add the first Sherpa-compatible candidates

- Validate the upstream Mimic3 VITS candidates for Afrikaans, Bengali,
  Gujarati, and Tswana.
- Prioritize Bengali and Gujarati first because they address meaningful gaps
  and are already close to Sherpa's VITS bundle format.
- Add a candidate to the in-app catalog only after its archive, manifest,
  phonemization resources, license, language metadata, and output format have
  been verified.

### 3. Evaluate conversion candidates for larger gaps

- Prototype Thai using Meta MMS only if the conversion path and license terms
  are acceptable.
- Compare MMS and smaller Indic alternatives for Tamil, Telugu, Marathi,
  Punjabi, Kannada, and related languages.
- Evaluate Malay, Filipino/Tagalog, Burmese/Myanmar, Amharic, Azerbaijani,
  and other long-tail languages according to demand and quality evidence.
- Treat large models such as Indic Parler-TTS as research candidates rather
  than default Syllavox downloads because their resource requirements conflict
  with the lightweight distribution goal.

### 4. Validate quality, resources, and licensing

- Require a successful load and synthesis smoke test for every proposed voice.
- Record native-speaker pronunciation feedback, script/number handling,
  archive size, peak memory, cold and warm latency, and real-time factor.
- Check model-card, dataset, and redistribution terms before publication.
- Keep non-commercial or otherwise restricted models out of the recommended
  catalog unless the user-facing terms and distribution model are explicitly
  resolved.
- Do not commit model files to the repository; downloads remain user-managed.

### 5. Integrate without disrupting existing users

- Preserve Piper voices and the current backend selection behavior.
- Use clear language and locale names in the catalog and installed-voice UI.
- Keep failed or unsupported candidates out of the catalog rather than exposing
  a broken install path.
- Add fallback diagnostics when a language has a candidate but no compatible
  local voice is installed.

### v0.4.2 acceptance criteria

- Every newly listed language has at least one reproducibly tested voice bundle
  and an explicit license record.
- New models produce valid mono, 16-bit WAV output through the existing
  backend contract.
- Size, memory, and latency measurements are recorded and remain compatible
  with the lightweight product goal.
- Piper remains available as the stable fallback for existing languages.
- The catalog contains no unverified, broken, or silently restricted model.

### v0.4.2 implementation status

The first language-coverage wave is complete. The four Mimic3 VITS archives
for Afrikaans, Bengali, Gujarati, and Tswana were installed from their real
upstream archives, verified by SHA-256, loaded with Sherpa-ONNX 1.13.6, and
used to generate valid mono, 16-bit WAV files. Their provenance, archive sizes,
measurements, and remaining research candidates are recorded in the
[v0.4.2 language coverage record](language-coverage-0.4.2.md).

Thai, additional Indic languages, and the long-tail language candidates remain
research-only until their conversion path, pronunciation quality, resource
cost, and licensing are suitable for the lightweight product.

## Sherpa-ONNX and rust-tts-wrapper evaluation

Evaluation completed on 2026-08-23 against the current Python/Piper
architecture and the upstream projects.

The Sherpa-ONNX implementation is now the v0.4.0 optional-backend pathway. It
is opt-in, CPU-first, and does not make Sherpa the default or replace Piper.

### Decision

- **Implement Sherpa-ONNX directly as an optional Python backend.** This fits
  the existing `TTSBackend` interface and is now implemented in v0.4.0,
  without replacing Piper or changing the public API.
- **Do not implement rust-tts-wrapper as Syllavox's core TTS layer now.** Keep
  it as a future interoperability option if SAPI, native cross-platform
  bindings, or a shared timing-capable native layer becomes a product
  requirement.

### Sherpa-ONNX fit

Sherpa-ONNX has a direct Python `OfflineTts` API and supports offline VITS
(including Piper-format models), Kokoro, Matcha, and other model families.
Its current examples include English and multilingual Kokoro model bundles,
CPU execution, configurable thread counts, speaker IDs, speech speed, and
sentence-batch limits. Current releases also publish Python wheels for the
Windows, macOS, and Linux environments relevant to the planned platform work.
See the upstream [Python offline TTS example](https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/offline-tts.py),
[TTS model documentation](https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/c-api/docs/tts.dox),
and [PyPI distribution files](https://pypi.org/project/sherpa-onnx/).

It is therefore a good match for Syllavox's existing design:

```text
TTSBackend
├── PiperBackend          (existing default backend)
└── SherpaOnnxBackend     (new optional backend)
```

The implementation should:

1. Add `sherpa-onnx` as an optional dependency rather than making it a
   mandatory 0.1.x dependency.
2. Add a `SherpaOnnxBackend` that creates and caches one `OfflineTts` instance
   per installed model bundle, generates PCM audio, and writes the same local
   WAV artifact consumed by the existing `AudioPlayer`.
3. Store Sherpa model bundles separately under a backend-specific directory.
   A bundle manifest must describe the model, tokens, voices, phonemization
   data, lexicons/rule FSTs, language, and license terms.
4. Represent a Sherpa voice as a stable backend-qualified ID, for example
   `sherpa-onnx:kokoro-multilang-v1_0#sid=18`, because one model bundle can contain many
   speakers. Keep the public `VoiceInfo` and `/v1/voices` shapes stable.
5. Reuse `SpeechController`, `AudioPlayer`, pause/resume, interruption, WAV
   cleanup, and the existing local-only API. Do not add a second playback
   implementation.
6. Add backend-specific diagnostics for missing bundle files, invalid model
   configuration, unsupported speakers, provider/runtime failures, and output
   sample-rate problems.
7. Extend the portable-build specification to collect Sherpa's native runtime
   libraries and notices, pin a tested version, and verify the resulting
   Windows artifact on a clean machine.

The acceptance gate remains measured rather than assumed: cold-start time, warm
synthesis latency, real-time factor on representative text, memory use,
voice/model size, interruption behavior, output compatibility, and licensing
must all be compared with the current Piper path. v0.4 keeps the model catalog
curated and CPU-first; GPU providers, voice cloning, and further catalog
expansion remain future work until the baseline is stable. The current
Amy-low VITS baseline uses Sherpa's native WAV writer and keeps the default
CPU thread count at 2 after the initial 2/4/8-thread comparison.

### Current v0.4.0 implementation

- `src/syllavox/tts/sherpa_onnx.py` provides the lazy Python adapter for VITS,
  Matcha, Kokoro, KittenTTS, and Supertonic bundles. Converted Piper bundles
  are supported by the adapter but intentionally excluded from the v0.4
  catalog.
- `bundle.json` manifests keep model paths, speaker IDs, language metadata, and
  license references explicit. The catalog installs official non-Piper
  archives and generates these manifests locally.
- The Settings panel exposes an explicit Sherpa-ONNX selection. Piper remains
  the default, and changing engines requires a restart.
- The base portable build remains Piper-only. `build_portable.ps1 -IncludeSherpa`
  enables the optional native runtime collection for a Sherpa-enabled build.
- The in-app catalog downloads, validates, installs, and deletes complete
  Sherpa bundles atomically. Model files remain separate from the application
  and still require per-model license review.
- `scripts/benchmark_sherpa_onnx.py` records the latency, real-time factor, WAV,
  and bundle-size measurements needed for the adoption gate.

Sherpa-ONNX should not be adopted as a highlighting solution. Its current TTS
path produces audio but does not provide exact word-level timing to callers;
upstream requests for word-level timestamp/boundary output remain open. See
the open [word-boundary feature request](https://github.com/k2-fsa/sherpa-onnx/issues/3727).
Any future timing interface should therefore be optional and should support
estimated boundaries without claiming exact synchronization.

### rust-tts-wrapper fit

`rust-tts-wrapper` provides a Rust library with a C ABI, native SAPI support,
Sherpa-ONNX integration, optional Speech Markdown/SSML handling, and bindings
for several languages. Its local word-boundary behavior is primarily estimated
for Sherpa-ONNX rather than being a reliable source of exact alignment. See
the upstream [repository](https://github.com/AACTools/rust-tts-wrapper) and
[Cargo feature/dependency definition](https://raw.githubusercontent.com/AACTools/rust-tts-wrapper/main/Cargo.toml).

Using it inside Syllavox now would require:

- building and pinning a native DLL/shared library for every supported target;
- adding a `ctypes`/CFFI layer with callback, lifetime, error, and buffer
  ownership handling;
- extending the PyInstaller and license inventory for the native artifact;
- duplicating or adapting model-bundle discovery and voice management; and
- deciding which optional engines are compiled, while explicitly excluding
  the wrapper's cloud engines to preserve Syllavox's local/offline boundary.

That complexity does not currently buy Syllavox a better integration than the
direct Python API. Revisit the wrapper only if Syllavox needs a shared native
engine for SAPI and multiple desktop platforms, or if upstream provides a
stable packaged binding with timing guarantees that the direct Python path
cannot provide.

## Long-term backlog

- Alternative voice-catalog hosting or mirrors if Hugging Face becomes
  unavailable.
- Additional TTS backends beyond Piper and Sherpa-ONNX.
- Further distribution improvements beyond the 1.0.0 installer.
- Broader automation and integration support.
- Investigate whether Syllavox voices, models, or synthesis services could be
  integrated into or used by NVDA and comparable assistive-technology
  software, subject to technical feasibility, licensing, accessibility needs,
  and collaboration with the relevant projects.
- An Android application or mobile companion app after 1.0.0, reusing the
  stable API and platform-neutral core where practical.

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
