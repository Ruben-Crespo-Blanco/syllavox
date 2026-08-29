# Syllavox v0.4.2 release notes

Syllavox v0.4.2 is a language-coverage release. It adds four optional
Sherpa-ONNX voices for languages that were not represented in the active
non-Piper Sherpa catalog, while keeping Piper as the default and stable
fallback.

## Included

- Afrikaans, Bengali, Gujarati, and Tswana Mimic3 VITS bundles in the curated
  Sherpa catalog.
- Readable language and country labels, speaker counts, sample rates, source
  links, and license metadata for the new bundles.
- SHA-256 verification before a Sherpa archive is extracted, plus checksum and
  provenance fields in the installed `bundle.json` manifest.
- A repeatable validation tool for checking catalog metadata and synthesizing
  short samples from installed real-model bundles.
- A language coverage record with archive sizes, runtime measurements, and the
  deferred candidate list for Thai, Indic, and long-tail languages.

## How to use the new voices

Use a Sherpa-enabled build, open **Find more voices...**, select the **Sherpa**
backend catalog, and install a language bundle. The model archive is downloaded
only after the user selects **Install selected**. Once installed, select the
voice like any other voice and synthesize normally.

The four v0.4.2 archives are approximately 76 MB compressed and 90 MB
installed each. They are intentionally not included in the portable ZIP, so the
base Piper-only build remains smaller and existing users do not download
unwanted models.

## Validation

The four real upstream archives were installed with Syllavox's checksum-aware
installer and tested with Sherpa-ONNX 1.13.6 on Windows. Each produced valid
mono, 16-bit WAV output at 22,050 Hz. Detailed measurements and the exact
archive digests are in
[`docs/language-coverage-0.4.2.md`](language-coverage-0.4.2.md).

The new models are based on the upstream Sherpa-ONNX Mimic3 model layout and
the MycroftAI Mimic3 voice collection. Voice and dataset terms remain separate
from the Syllavox MIT license; review the linked upstream terms before
redistribution.

## Not included in this release

- Piper replacement or changes to the default backend.
- Thai, Tamil, Telugu, Marathi, Punjabi, Kannada, Malay, Filipino/Tagalog,
  Burmese/Myanmar, Amharic, Azerbaijani, or every other MMS language.
- Reading sessions or an accessibility-first reading interface; both remain
  deferred until after 1.0.0.
- macOS, Linux, or Android ports.

See the [future model candidate register](sherpa-onnx/future-language-model-candidates.md)
for the next language evaluation order.
