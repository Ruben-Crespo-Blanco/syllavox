# Future language-model candidates

This is a research register for languages that are absent from the official
Sherpa-ONNX monolingual catalog snapshot used by Syllavox v0.4.0. It is not an
active download catalog: no model files are committed to Syllavox, and every
candidate needs a compatibility, quality, license, and size review first.

## Candidates already close to Sherpa-ONNX

The upstream Sherpa-ONNX Android model-generation script names these Mimic3
VITS models. They are the most promising first candidates because they already
follow Sherpa's VITS model path, although they are not part of Syllavox's v0.4
curated catalog yet.

| Language | Candidate model directory | Proposed future route |
|---|---|---|
| Afrikaans | `vits-mimic3-af_ZA-google-nwu_low` | Validate the upstream archive, manifest it as a VITS bundle, and measure quality. |
| Bengali | `vits-mimic3-bn-multi_low` | Highest-priority Sherpa-native candidate; validate phonemization and licensing. |
| Gujarati | `vits-mimic3-gu_IN-cmu-indic_low` | Validate as a Sherpa VITS bundle and compare against Indic alternatives. |
| Tswana | `vits-mimic3-tn_ZA-google-nwu_low` | Add only if there is demand after the larger-language gaps are addressed. |

The same upstream list also contains models for Persian, Finnish, Hungarian,
Korean, Nepali, Polish, and Vietnamese. Those languages already have entries
in the current Sherpa catalog snapshot, so they are tracked as possible
quality/voice additions rather than language-coverage gaps. The source list is
the upstream [Sherpa-ONNX model-generation script](https://github.com/k2-fsa/sherpa-onnx/blob/master/scripts/apk/generate-tts-apk-script.py).

## Other existing model sources

| Missing or useful language group | Existing source | Compatibility and trade-off |
|---|---|---|
| Hebrew | [Meta MMS Hebrew](https://huggingface.co/facebook/mms-tts-heb); Piper already has `he_IL` voices | MMS is a VITS checkpoint usable through Transformers, not a drop-in Sherpa bundle. It would need ONNX export, tokenizer/phonemizer validation, and a license review. Piper remains the practical v0.4 path. |
| Thai | [Meta MMS Thai](https://huggingface.co/facebook/mms-tts-tha) | Existing single-language VITS checkpoint; likely a conversion project. The model is about 145 MB in safetensors form and is CC BY-NC 4.0, so it is not an obvious general-purpose redistribution choice. |
| Bengali, Gujarati, Kannada, Marathi, Punjabi, Tamil, Telugu and related Indic languages | [Indic Parler-TTS](https://huggingface.co/ai4bharat/indic-parler-tts) and [Meta MMS](https://huggingface.co/facebook/mms-tts) | Indic Parler-TTS covers 21 languages and is Apache-2.0, but its roughly 0.9B-parameter model is far too large for the lightweight default path. MMS has much wider coverage but is CC BY-NC 4.0 and also needs conversion. |
| Malay, Filipino/Tagalog, Burmese/Myanmar, Amharic, Azerbaijani and other long-tail languages | [Meta MMS language collection](https://huggingface.co/facebook/mms-tts) | The collection advertises more than 1,000 language checkpoints. Treat each language as a separate candidate; check the exact ISO 639-3 checkpoint, pronunciation quality, model size, and non-commercial license before adoption. |

Meta's individual Bengali, Tamil, and Telugu checkpoints are also available
as [MMS Bengali](https://huggingface.co/facebook/mms-tts-ben), [MMS Tamil](https://huggingface.co/facebook/mms-tts-tam), and [MMS Telugu](https://huggingface.co/facebook/mms-tts-tel).
They are useful proof that models exist, but their current Transformers/VITS
packaging does not establish Sherpa-ONNX compatibility.

## Recommended future order

1. Bengali and Gujarati: test the Sherpa-native Mimic3 candidates first.
2. Hebrew: keep Piper as the user-facing solution while fixing or documenting
   the Hebrew phonemizer issue; only then evaluate an MMS conversion.
3. Thai: evaluate the MMS checkpoint with a small ONNX conversion prototype.
4. Tamil, Telugu, Marathi, Punjabi, and Kannada: compare MMS with the smaller
   Sherpa-compatible options that may emerge from Indic model work.
5. Malay, Tagalog, Burmese, Amharic, Azerbaijani, and Tswana: prioritize from
   demand and quality evidence rather than adding a large collection blindly.

For every future model, record the model-card license, archive size, peak
memory, cold and warm latency, language normalization behavior, and a short
native-speaker quality check before adding it to the in-app catalog.
