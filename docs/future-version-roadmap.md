# Syllavox Future-Version Roadmap

This roadmap maps planned development to proposed versions. The version
assignments are planning targets, not commitments. The current public release
is the language coverage release, version 0.4.2; v0.5.0 is the current
development milestone and its release remains pending packaging and manual
validation.

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
| **0.5.0** | Windows SAPI and distribution | Add Windows SAPI as an optional TTS backend that discovers installed system voices and renders compatible WAV output; introduce the system-speech provider boundary needed by future macOS and Linux adapters; add a per-user Windows installer and opt-in Windows startup registration; preserve Piper and Sherpa as existing options. |
| **0.6.0** | macOS adaptation | Add macOS platform services, global hotkeys, single-instance handling, tray behavior, audio validation, packaging, manual testing, and a native macOS system-speech provider behind the v0.5 abstraction. |
| **0.7.0** | Linux adaptation | Add Linux platform services, hotkeys, tray integration, packaging, distribution testing, documented supported environments, and a supported Linux system-speech provider behind the v0.5 abstraction. |
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
- Leave actual macOS implementation, packaging, and manual testing to v0.6.0.

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
- The macOS implementation can begin in v0.6.0 without redesigning the core
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

## v0.5.0 implementation plan: Windows SAPI and system speech

v0.5.0 adds Windows SAPI as an optional system-voice backend and completes the
first user-facing Windows distribution path before the macOS and Linux
adaptations begin. SAPI voices are installed and managed by Windows; Syllavox
will discover them, let the user select one, render speech to the same local
WAV workflow used by Piper and Sherpa-ONNX, and expose the backend through the
existing UI, hotkey, API, and browser-extension paths. Piper remains the
default, Sherpa-ONNX remains available when installed, and no SAPI voice files
are downloaded or bundled by Syllavox.

The implementation should use the Windows SAPI COM automation interfaces
directly. `SpVoice` supports voice enumeration and rendering, while
`SpFileStream` provides file output for the existing playback and export
contracts. See Microsoft's [SpVoice documentation](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms720149%28v%3Dvs.85%29),
[voice property documentation](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms723614%28v%3Dvs.85%29),
and [SpFileStream documentation](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms722561%28v%3Dvs.85%29).

### Goal and non-goals

- Add a selectable `windows_sapi` backend for Windows installations that
  expose SAPI 5 voices.
- Discover installed SAPI voice tokens and present readable names and locale
  information in the normal voice selector.
- Generate valid local WAV files for both Speak and Export WAV operations.
- Reuse the current `SpeechController`, `AudioPlayer`, temporary-file cleanup,
  hotkey, local API, and browser-extension paths.
- Keep SAPI system voices read-only from Syllavox: they can be selected but
  not downloaded, deleted, or unloaded as model resources.
- Keep the default single-request workflow and defer reading sessions,
  synchronized highlighting, and a dedicated accessibility-first interface
  until after 1.0.0.
- Add an opt-in, per-user Windows startup registration setting. It must be
  independent from the existing “start minimized to tray” preference, while
  allowing users to combine both behaviors.
- Do not implement macOS or Linux system speech in v0.5. Their adapters should
  be possible without changing the application-level speech contract.

### 1. Confirm the Windows SAPI integration path

- Time-box a small Windows-only COM spike before the main implementation.
- Prefer a lazy `comtypes` bridge because it maps to SAPI's COM automation
  objects through Python's existing `ctypes`-based Windows integration and
  avoids a subprocess dependency. Keep `pywin32` as a fallback only if
  `comtypes` cannot be frozen reliably or cannot enumerate/render the target
  SAPI installations.
- Verify the bridge can create `SAPI.SpVoice`, enumerate `GetVoices()`, select
  a token, create `SAPI.SpFileStream`, write a WAV file, close all COM streams,
  and report HRESULT/COM failures without crashing the application.
- Verify the process architecture explicitly. A 64-bit portable build should
  enumerate the SAPI voices visible to its 64-bit COM registration; document
  that a voice missing from the matching Windows/SAPI installation cannot be
  made available by Syllavox.
- Reject `pyttsx3` as the core integration path because its backend selection,
  voice identifiers, file-rendering behavior, and cross-platform behavior are
  indirect. Do not add `rust-tts-wrapper` for v0.5; its native ABI and build
  matrix would add complexity that direct SAPI COM does not require.

### 2. Add the system-speech abstraction

- Keep `TTSBackend` as the application-level contract for health checks, voice
  enumeration, synthesis, and shutdown. Piper, Sherpa-ONNX, and SAPI must all
  remain substitutable implementations of that contract.
- Add a narrow `SystemSpeechProvider` protocol or abstract base for
  platform-owned speech providers. It should cover provider identity,
  health, voice enumeration, synthesis, and lifecycle cleanup without
  exposing COM objects to the rest of the application.
- Add a `WindowsSapiProvider` implementation and a small
  `SystemSpeechBackend` adapter, or an equivalent composition that keeps the
  provider details private. Future macOS and Linux providers should fit this
  boundary rather than adding operating-system checks throughout the UI.
- Add a backend descriptor/factory registry containing the stable backend ID,
  display name, platform availability, constructor, and voice-resource
  capabilities. Replace the current application-composition branches that
  assume only Piper and Sherpa-ONNX.
- Make backend IDs stable and normalized in settings. Existing `piper` and
  `sherpa_onnx` settings must continue to load unchanged; `windows_sapi` must
  be rejected or shown unavailable on non-Windows systems without silently
  corrupting the saved configuration.

### 3. Enumerate and identify SAPI voices safely

- Enumerate the tokens returned by `SpVoice.GetVoices()` rather than reading
  the registry directly. This keeps discovery aligned with what SAPI can
  actually activate.
- Build each `VoiceInfo` from the token description and attributes such as
  locale/language, gender, vendor, and age when available. Keep the public
  `VoiceInfo` and `/v1/voices` response shapes stable.
- Normalize Windows locale values, including hexadecimal SAPI locale IDs,
  into readable language and region labels. Unknown values must still display
  a useful fallback instead of exposing an opaque identifier as the primary
  language name.
- Create a stable backend-qualified voice ID such as
  `windows_sapi:<token-digest>`. Keep the original token ID in a private
  provider mapping so registry paths and COM details are not exposed through
  the public API or UI.
- Re-enumerate on startup and resolve persisted IDs through the stable mapping.
  If a voice was removed or renamed in Windows, preserve the current fallback
  behavior and explain that the saved system voice is no longer available.
- Do not implement SAPI voice installation, model-size reporting, model
  deletion, or loaded-model controls. The system voice manager must report
  those capabilities as unsupported and explain that Windows manages them.

### 4. Render SAPI output through the existing audio contract

- For each synthesis request, initialize COM in the calling thread, create a
  SAPI voice object, resolve the selected token, and render into a temporary
  `SpFileStream` path. Do not share COM objects across Qt, API, or worker
  threads.
- Close the SAPI stream before validating or handing the file to
  `AudioPlayer`. Use the same atomic output-path behavior and retained-WAV
  behavior already used by Piper and Sherpa-ONNX.
- Prefer a standard PCM WAV format compatible with `QMediaPlayer`; if SAPI
  negotiates a different supported PCM sample rate, accept it after explicit
  validation rather than assuming one fixed rate. Reject non-PCM, incomplete,
  empty, or otherwise invalid output with `SynthesisFailedError`.
- Ensure every failure path closes the COM stream and removes or quarantines
  partial output files. COM initialization/uninitialization must be balanced
  even when voice selection, synthesis, or file creation fails.
- Keep Syllavox's Volume and Speed settings as playback controls. Do not map
  them to SAPI's synthesis rate or volume in v0.5, because that would change
  the meaning of existing settings and produce backend-dependent behavior.
- Keep input as normalized plain text. Do not implicitly treat user text as
  SAPI XML/SSML, which could change punctuation behavior or interpret pasted
  markup unexpectedly.
- Preserve current lifecycle semantics: a request still interrupts current
  playback, but a synchronous SAPI render is allowed to finish before the
  resulting audio can be stopped. Measure this behavior and document it if it
  differs materially from Piper or Sherpa.

### 5. Integrate the backend into the application

- Add `Windows SAPI` to the Settings backend selector only when the factory
  reports that the current platform supports it. Keep Piper as the default.
- Require the existing restart flow after a backend change so COM/provider
  resources are created under the correct startup configuration.
- Update the main-window voice selector to support an installed-system-voice
  mode. Hide or disable download/catalog actions for SAPI and show that voices
  are managed by Windows.
- Update the installed-voice management dialog to become read-only for SAPI:
  no load, unload, delete, or resource-cleanup actions should be presented as
  available. Keep the dialog useful by showing the selected voice, locale,
  and the reason system management is unavailable.
- Keep voice selection, fallback, hotkey speech, `/v1/speak`, `/v1/voices`,
  WAV export, pause, stop, playback rate, volume, temporary cleanup, and
  shutdown on the existing shared paths.
- Return clear backend health details when SAPI is unavailable, COM activation
  fails, no SAPI voices are installed, or the selected voice disappears.
  Selecting SAPI must not make the application fail to start.
- Ensure API clients and browser extensions do not need a new protocol. They
  should see the selected backend through the existing status response and
  receive the same voice/synthesis error categories.
- Add a Windows-only **Run Syllavox on Windows startup** preference in the
  existing Settings panel. Persist it in the settings schema, write the
  current frozen executable command to the current user's
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` key, remove the value
  when disabled, and surface registration failures without preventing normal
  application startup. Do not request elevation or register Syllavox as a
  service.

### 6. Package SAPI without undermining the lightweight build

- Add the chosen COM bridge as a Windows-conditional optional dependency,
  keeping non-Windows development environments free of Windows-only modules.
- Add a packaging switch such as `-IncludeSapi` and make the v0.5 Windows
  release artifact SAPI-enabled. The minimal Piper-only artifact may remain
  available for users who do not need SAPI; a combined Sherpa/SAPI artifact
  should also be reproducible.
- Collect only the bridge modules needed by the frozen application. Add
  hidden-import or generated-COM-wrapper handling only after a clean portable
  launch test proves it is required.
- Do not bundle SAPI voice models or Windows voice data. Record the bridge
  package and license in `DEPENDENCY_VERSIONS.txt` and the portable notices.
- Verify that omitting `-IncludeSapi` still produces a working Piper-only
  build and that the SAPI-enabled build does not collect unrelated optional
  runtimes.
- Measure the size difference, startup time, idle memory, synthesis memory,
  and warm/cold latency for Piper-only, SAPI-enabled, and combined
  Sherpa/SAPI builds.
- Add an Inno Setup 6 script that consumes the validated SAPI-enabled portable
  folder, installs per-user under LocalAppData, creates Start Menu and
  optional desktop shortcuts, and offers launch-after-install. Keep the
  portable ZIP available as an alternative, and do not bundle voice models.
- Make uninstallation remove the app-owned startup registration. Ask before
  deleting Syllavox user data so reinstalling does not unexpectedly remove
  downloaded voices, settings, or logs.

### 7. Test the implementation

- Add provider unit tests using a fake COM automation layer for token
  enumeration, locale parsing, stable IDs, voice selection, output-path
  handling, cleanup, and error translation.
- Add Windows integration tests, skipped with a clear reason when SAPI is not
  available, covering at least one installed voice, multiple visible voices,
  voice disappearance, valid WAV output, explicit export, Unicode text,
  punctuation, long text near the configured limit, and COM cleanup.
- Add backend-registry tests proving SAPI is exposed on Windows, not imported
  on non-Windows platforms, and cannot become the default accidentally.
- Add UI tests for selecting SAPI, restart-required messaging, read-only voice
  management, unavailable/no-voice status, saved voice fallback, and backend
  switching back to Piper or Sherpa.
- Add integration coverage proving SAPI uses the same SpeechController path
  for the main window, hotkey, local API, and WAV export.
- Add packaging tests for both SAPI-enabled and SAPI-disabled frozen builds,
  including clean launch, Qt DLL loading, SAPI module import, and absence of
  bundled voice models.
- Validate the installer script inputs, versioned output name, checksum file,
  per-user install settings, shortcut targets, and startup-registration
  cleanup. Compile it with the pinned/local Inno Setup 6 compiler when making
  a release artifact.
- Re-run the complete existing Piper/Sherpa regression suite and the real
  Sherpa model smoke tests to ensure the new backend does not alter existing
  behavior.

### 8. Manual validation matrix

- Test on supported 64-bit Windows installations with one built-in voice,
  multiple installed voices, and no usable SAPI voice.
- Select every visible SAPI voice, speak short and long samples, export WAV,
  change playback speed and volume, pause/resume, stop, and start a new
  request while audio is playing.
- Confirm the global read hotkey and browser extension use the selected SAPI
  voice, and confirm `/v1/status`, `/v1/voices`, and `/v1/speak` remain
  functional.
- Restart after selecting SAPI, switch back to Piper and Sherpa, and verify
  the correct catalog and voice-management behavior returns for each backend.
- Test with network access disabled to confirm SAPI synthesis remains local
  and does not trigger a model download.
- Test application exit, repeated backend changes, failed exports, and
  interrupted playback while watching for locked temporary files, lingering
  COM processes, or stale audio artifacts.

### v0.5.0 acceptance criteria

- Windows SAPI is an optional, selectable backend in the SAPI-enabled
  portable build and is not offered on unsupported platforms.
- All SAPI voices visible to the matching Syllavox process architecture can be
  enumerated, selected, persisted, and resolved again on the next launch.
- Speak and Export WAV produce validated files through the existing
  `SynthesisResult` and playback contracts.
- SAPI voice absence, COM failure, missing voice, invalid output, and cleanup
  failures are visible and recoverable without taking down the application.
- Piper remains the default and Sherpa-ONNX remains functional; no existing
  catalog or model-management behavior regresses.
- Hotkey, API, browser extension, playback controls, temporary cleanup, and
  shutdown continue to use the shared application paths.
- The SAPI-enabled portable build launches on a clean supported Windows
  machine, its size/resource delta is recorded, and no voice models are
  bundled.
- The Windows installer compiles from the release portable folder, installs
  without elevation, creates working shortcuts, and leaves the portable
  artifact reproducible.
- The startup preference is opt-in, persists across relaunches, registers the
  correct current-user executable command, and can be disabled or removed by
  uninstall without affecting other users.
- The provider boundary is documented and tested well enough that v0.6 can
  add a macOS system-speech provider and v0.7 can add a Linux system-speech
  provider without changing `SpeechController`, API schemas, or the public
  voice-selection contract.

### v0.5.0 risks and explicit trade-offs

- SAPI voice quality and language availability depend on what the user has
  installed in Windows; Syllavox cannot guarantee a universal language pool
  through this backend.
- COM apartment rules and 32/64-bit registration can make a voice visible in
  one host but unavailable in another. The provider must treat this as a
  diagnosable compatibility condition.
- SAPI output is system-provided rather than a Syllavox-managed model, so
  model size and model lifecycle controls do not apply.
- Direct COM adds a small Windows-only packaging dependency, but avoids
  shipping another speech engine or model collection. The release decision
  should be based on measured portable size and reliability, not only the
  dependency count.
- SAPI does not change the post-1.0.0 status of reading sessions,
  accessibility-first UI, or synchronized word highlighting.

### v0.5.0 implementation status

The v0.5.0 implementation is present in the working tree. Windows SAPI voice
enumeration, readable locale labels, stable IDs, shared backend selection,
read-only system-voice management, optional dependency metadata, SAPI
portable packaging switches, the Windows startup preference, and installer
configuration are implemented and covered by unit tests or script validation.
The development host can enumerate its installed voices, but its local SAPI
engine currently rejects speech rendering with HRESULT `0x80045040`; the
provider reports that failure cleanly and leaves no partial WAV file. Final
release publication still requires a successful rendering check on a Windows
installation with a functioning SAPI engine, a locally available Inno Setup
compiler for the installer artifact, plus the planned portable size and
clean-launch measurements.

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
