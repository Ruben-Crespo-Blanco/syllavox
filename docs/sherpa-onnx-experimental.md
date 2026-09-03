# Sherpa-ONNX in Syllavox v0.4.x

Sherpa-ONNX is an optional second speech backend. Piper remains the default
backend and remains the broadest voice catalog. Sherpa is useful because one
offline runtime can host several model families without changing Syllavox's
voice, playback, API, or WAV contracts.

## Install the optional runtime

From the Syllavox project directory:

```powershell
python -m pip install -e ".[dev,packaging,sherpa]"
```

The `sherpa` extra pins the tested Python wrapper and native runtime to
`1.13.6`. Normal Piper installations do not install those packages. For
portable distribution, build with `-IncludeSherpa`; the base portable build
stays Piper-only to keep its download smaller.

## Install a Sherpa model from the application

1. Start a Sherpa-enabled Syllavox build.
2. Open **Settings**, choose **Sherpa-ONNX**, select **Apply/Save settings**,
   and restart Syllavox.
3. Select **Find more voices...**.
4. Select a model bundle and choose **Install selected**.
5. Select one of the installed voices and use **Speak** as usual.

Syllavox downloads the archive from the official Sherpa-ONNX release, safely
extracts it, downloads any declared shared resource such as the Matcha
vocoder, validates all required files, and writes a local `bundle.json`
manifest. Installation is atomic: an incomplete download does not become an
available bundle.

Bundles are stored under:

```text
%LOCALAPPDATA%\Syllavox\models\sherpa-onnx\<bundle-id>\
```

The model files stay outside the repository and portable application. Delete
an installed Sherpa voice from **Manage voices...** to remove its complete
bundle and its downloaded resources. Deleting one voice from a shared bundle
removes the bundle for all voices in that bundle.

## v0.4 catalog

The in-app catalog contains curated non-Piper archives from the official
[Sherpa-ONNX model list](https://k2-fsa.github.io/sherpa/onnx/tts/all/index.html):

- Kokoro v1.1 multilingual INT8 and full-precision bundles;
- Kokoro v1.0 multilingual and English v0.19 bundles;
- Matcha English LJSpeech, Chinese Baker, and Chinese + English bundles;
- KittenTTS Nano, Micro, and Mini English bundles, including the v0.8 FP32
  and INT8 variants;
- Inflect English Nano and Micro v2 VITS bundles;
- MeloTTS Chinese + English VITS;
- Mimic3 VITS voices for Afrikaans, Bengali, Gujarati, and Tswana;
- Supertonic 3 multilingual INT8.

The catalog includes the separate non-Piper monolingual bundles listed by the
upstream pages. The per-language `supertonic-3-*` pages all point to the same
single multilingual Supertonic archive, so Syllavox exposes that archive once
with language-qualified voices instead of downloading one duplicate bundle per
language. Converted `vits-piper-*` archives remain intentionally omitted.

All five fixed-voice families are supported by the adapter: VITS, Matcha,
Kokoro, KittenTTS, and Supertonic. The Sherpa catalogue's converted
`vits-piper-*` archives are deliberately omitted because Piper already owns
that catalog in Syllavox. ZipVoice and Pocket remain future work because they
require reference audio and voice-cloning controls rather than a fixed voice
selection.

Kokoro speakers are shown with their readable names and the correct English or
Chinese language. Supertonic voices use IDs such as:

```text
sherpa-onnx:sherpa-onnx-supertonic-3-tts-int8-2026-05-11#sid=0&lang=fr
```

The language is passed through Sherpa's generation configuration, so the
selected language is not inferred from the user's text. Language labels use
readable names such as `English (en)` and `French (fr)` rather than displaying
an opaque language family alone.

Changing the speech engine shows a dedicated restart action in Settings; the
action saves the selection and relaunches the application so the new backend
is actually loaded.

The separate [future language-model candidate register](sherpa-onnx/future-language-model-candidates.md)
records the four Mimic3 additions and tracks Thai, Tamil, Telugu, Marathi,
Punjabi, Kannada, and other languages that need
conversion, quality, licensing, or resource evaluation before they belong in
the active catalog. See the [v0.4.2 language coverage record](language-coverage-0.4.2.md)
for the tested additions and their archive digests.

## Runtime behavior and diagnostics

The backend is lazy. Importing Syllavox does not import Sherpa, and loading a
voice creates one cached `OfflineTts` instance per bundle. Multiple speakers
from one bundle therefore share the model in memory. The v0.4 path uses CPU
execution with two threads by default and writes the standard Syllavox WAV
artifact using Sherpa's native writer when available.

Incomplete manifests, missing files, invalid paths, unsupported speakers,
runtime failures, and sample-rate mismatches are reported as backend
diagnostics. The local `/v1/voices` and `/v1/speak` API routes retain the same
shape used by Piper; only the backend-qualified voice ID changes.

## Benchmarking

After installing the optional dependency and a complete bundle:

```powershell
python scripts/benchmark_sherpa_onnx.py
```

Use `--voice` to select a voice, `--threads` to compare CPU budgets, and
`--output` to choose a WAV destination. The report includes cold load time,
warm synthesis time, audio duration, real-time factor, output size, and bundle
size. Compare the same text and machine against Piper before choosing a
default voice or changing the default backend.

For real model validation across the curated catalog, run:

```powershell
python scripts/smoke_test_sherpa_models.py --threads 2
```

The original v0.4 validation run passed 44/44 representative inference checks
across the original 11 curated bundles, including both Kokoro languages and
one Supertonic speaker in each of its 31 languages. The v0.4.2 validation run
also passed installation, loading, and basic inference for the four Mimic3
bundles. The smoke test validates bundle loading and basic speech generation,
not every speaker, text condition, or long-form workload.

The initial Amy-low comparison showed Sherpa's native writer producing warm
audio in roughly 0.143 seconds with two threads for about 3.024 seconds of
audio; this is a machine-specific baseline, not a product guarantee. Sherpa
does not provide exact word-level timing for Syllavox. Reading sessions and
accessibility-first synchronized highlighting are available in the v1.0.0
desktop workflow at sentence/paragraph granularity; exact word-level timing
and highlighting inside third-party applications remain out of scope.

## Return to Piper

Select **Piper (default)** in Settings and restart Syllavox. Piper model files
remain in `models\piper`; Sherpa bundles remain isolated in
`models\sherpa-onnx`. Choosing one backend never deletes the other backend's
models.
