# Syllavox v0.4.2 language coverage record

v0.4.2 promotes four Sherpa-ONNX-compatible Mimic3 VITS voices into the
optional catalog. Piper remains the default backend and remains the fallback
for languages already covered by Piper. The application and portable builds
do not contain voice files; users download selected bundles on demand.

## Active additions

| Language | Locale metadata | Speakers | Archive size | Installed size | Runtime result |
|---|---|---:|---:|---:|---|
| Afrikaans | Afrikaans — South Africa (`af`) | 9 | 76.3 MB | 90.0 MB | Passed load and mono 16-bit WAV synthesis |
| Bengali | Bengali — Bangladesh (`bn`) | 16 | 76.2 MB | 90.0 MB | Passed load and mono 16-bit WAV synthesis |
| Gujarati | Gujarati — India (`gu`) | 3 | 76.3 MB | 90.0 MB | Passed load and mono 16-bit WAV synthesis |
| Tswana | Tswana — South Africa (`tn`) | 26 | 76.2 MB | 90.0 MB | Passed load and mono 16-bit WAV synthesis |

Archive sizes are the downloaded `.tar.bz2` files rounded to one decimal
megabyte. Installed sizes include the shared phonemization data carried by
each archive. The four archives are approximately 320 MB compressed or 360 MB
installed when all four are selected; users only pay that cost for voices they
choose to install.

The first technical smoke test used Sherpa-ONNX 1.13.6 on Windows with the
first speaker from each bundle:

| Language | Output rate | Duration | Elapsed | Real-time factor |
|---|---:|---:|---:|---:|
| Afrikaans | 22,050 Hz | 2.643 s | 1.053 s | 0.399 |
| Bengali | 22,050 Hz | 3.334 s | 1.015 s | 0.304 |
| Gujarati | 22,050 Hz | 3.332 s | 1.199 s | 0.360 |
| Tswana | 22,050 Hz | 2.825 s | 1.612 s | 0.571 |

These are engineering smoke-test measurements, not a language-quality study.
They confirm that the real archives install, load, select a speaker, and
produce the existing Syllavox audio contract. Native-speaker review and wider
text/number testing remain appropriate follow-up work. The runtime emitted a
non-fatal unknown-combining-mark warning during the run; it did not prevent
valid WAV generation and should be monitored if broader pronunciation testing
finds a language-specific issue.

## Integrity and provenance

Each active archive has a pinned SHA-256 digest in the catalog. The installer
checks the digest before extraction and writes the digest, source URL, readable
language/country metadata, and license links into the installed `bundle.json`
manifest.

The model directory and filename conventions follow the upstream
[Sherpa-ONNX model-generation script](https://github.com/k2-fsa/sherpa-onnx/blob/master/scripts/apk/generate-tts-apk-script.py).
The converted model cards identify the corresponding
[Mimic3 voice repository](https://github.com/MycroftAI/mimic3-voices), whose
voice repository is CC BY-SA 4.0. Dataset and component-specific terms still
apply; users should review the upstream records before redistribution.

## Remaining gaps

v0.4.2 does not add every language represented by Meta MMS or other research
collections. Thai, Tamil, Telugu, Marathi, Punjabi, Kannada, Malay,
Filipino/Tagalog, Burmese/Myanmar, Amharic, Azerbaijani, and other long-tail
languages remain research candidates because conversion compatibility,
pronunciation quality, model size, and/or license terms still need review.
See the [future model candidate register](sherpa-onnx/future-language-model-candidates.md)
for the next evaluation order.

## Re-running the validation

The dependency-free metadata check is:

```text
python scripts/validate_sherpa_catalog.py --json
```

After installing the optional Sherpa dependency and the selected bundles, the
real synthesis check is:

```text
python scripts/validate_sherpa_catalog.py --synthesize --output-dir validation-output --json
```

The tool returns a non-zero exit status for a missing bundle, incomplete
metadata, failed model load, failed synthesis, or a non-mono/non-16-bit WAV.
