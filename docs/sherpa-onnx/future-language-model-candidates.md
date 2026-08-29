# Future language-model candidates

This is a research register for languages that are absent from Syllavox's
active non-Piper Sherpa catalog. It also records candidates that have been
promoted from research into a release. It is not a model-file repository: no
model files are committed to Syllavox, and every candidate needs a
compatibility, quality, license, and size review first. A language can appear
here even when Piper already provides a usable voice, because the register
also tracks possible additional backend choices.

## Promoted to the v0.4.2 active catalog

These four Sherpa-compatible Mimic3 VITS bundles were downloaded from the
official Sherpa-ONNX release archive, installed through Syllavox's atomic
bundle installer, and synthesized successfully on Windows using Sherpa-ONNX
1.13.6. The archives are optional user downloads; they are not included in the
portable application or repository.

| Language | Model directory | Speakers | Archive SHA-256 |
|---|---|---:|---|
| Afrikaans | `vits-mimic3-af_ZA-google-nwu_low` | 9 | `a4d2649d4b5e72e04d981c843e419b41d76845eec297a9c06f73bdd44e79ac1f` |
| Bengali | `vits-mimic3-bn-multi_low` | 16 | `a921a622e9dac5e0ad4bfe9f4a02b6d15fe6797532213718305e06312b7a0ae3` |
| Gujarati | `vits-mimic3-gu_IN-cmu-indic_low` | 3 | `ed6849f311bac71cc9f76b33d32412671ca201ea4b3b575f7b28d67e26eac6ae` |
| Tswana | `vits-mimic3-tn_ZA-google-nwu_low` | 26 | `7f43753eb4d3c4b17ff43c8764d2fb90204ba5e8247ee4023cfe9e0ac40816d3` |

The upstream Sherpa-ONNX Android model-generation script names these Mimic3
VITS models and establishes the model filenames used by the bundles. The
voice repository lists the speaker counts and language provenance. See the
[Sherpa-ONNX model-generation script](https://github.com/k2-fsa/sherpa-onnx/blob/master/scripts/apk/generate-tts-apk-script.py)
and [MycroftAI's Mimic3 voice repository](https://github.com/MycroftAI/mimic3-voices).

## Remaining candidates already close to Sherpa-ONNX

The upstream Sherpa-ONNX Android model-generation script names these Mimic3
VITS models for additional languages already represented by Syllavox's active
catalog. They are tracked for future voice diversity and quality improvements,
not as v0.4.2 language-coverage gaps.

| Language | Candidate source | Proposed future route |
|---|---|---|
| Persian | Upstream Mimic3 voice entries | Compare quality and locale metadata with the current Persian Sherpa entry. |
| Finnish | Upstream Mimic3 voice entries | Compare quality and model size with the current Finnish Sherpa entry. |
| Hungarian | Upstream Mimic3 voice entries | Compare quality and model size with the current Hungarian Sherpa entry. |
| Korean | Upstream Mimic3 voice entries | Compare quality and speaker metadata with the current Korean Sherpa entry. |
| Nepali | Upstream Mimic3 voice entries | Compare quality and locale metadata with the current Nepali Sherpa entry. |
| Polish | Upstream Mimic3 voice entries | Compare quality and model size with the current Polish Sherpa entry. |
| Vietnamese | Upstream Mimic3 voice entries | Compare quality and model size with the current Vietnamese Sherpa entry. |

The same upstream list also contains models for Persian, Finnish, Hungarian,
Korean, Nepali, Polish, and Vietnamese. Those languages already have entries
in the current Sherpa catalog snapshot, so they are tracked as possible
quality/voice additions rather than language-coverage gaps. The source list is
the upstream [Sherpa-ONNX model-generation script](https://github.com/k2-fsa/sherpa-onnx/blob/master/scripts/apk/generate-tts-apk-script.py).

## Other existing model sources

| Missing or useful language group | Existing source | Compatibility and trade-off |
|---|---|---|
| Thai | [Meta MMS Thai](https://huggingface.co/facebook/mms-tts-tha) | Existing single-language VITS checkpoint; likely a conversion project. The model is about 145 MB in safetensors form and is CC BY-NC 4.0, so it is not an obvious general-purpose redistribution choice. |
| Bengali, Gujarati, Kannada, Marathi, Punjabi, Tamil, Telugu and related Indic languages | [Indic Parler-TTS](https://huggingface.co/ai4bharat/indic-parler-tts) and [Meta MMS](https://huggingface.co/facebook/mms-tts) | Indic Parler-TTS covers 21 languages and is Apache-2.0, but its roughly 0.9B-parameter model is far too large for the lightweight default path. MMS has much wider coverage but is CC BY-NC 4.0 and also needs conversion. |
| Malay, Filipino/Tagalog, Burmese/Myanmar, Amharic, Azerbaijani and other long-tail languages | [Meta MMS language collection](https://huggingface.co/facebook/mms-tts) | The collection advertises more than 1,000 language checkpoints. Treat each language as a separate candidate; check the exact ISO 639-3 checkpoint, pronunciation quality, model size, and non-commercial license before adoption. |

Meta's individual Bengali, Tamil, and Telugu checkpoints are also available
as [MMS Bengali](https://huggingface.co/facebook/mms-tts-ben), [MMS Tamil](https://huggingface.co/facebook/mms-tts-tam), and [MMS Telugu](https://huggingface.co/facebook/mms-tts-tel).
They are useful proof that models exist, but their current Transformers/VITS
packaging does not establish Sherpa-ONNX compatibility.

## Recommended future order

1. Thai: evaluate the MMS checkpoint with a small ONNX conversion prototype,
   subject to its license and resource constraints.
2. Tamil, Telugu, Marathi, Punjabi, and Kannada: compare MMS with the smaller
   Sherpa-compatible options that may emerge from Indic model work.
3. Malay, Tagalog, Burmese, Amharic, Azerbaijani, and other long-tail
   languages: prioritize from demand and quality evidence rather than adding a
   large collection blindly.

For every future model, record the model-card license, archive size, peak
memory, cold and warm latency, language normalization behavior, and a short
native-speaker quality check before adding it to the in-app catalog.
