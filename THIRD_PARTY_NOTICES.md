# Syllavox third-party notices and release licensing

This document records the licensing and provenance policy for Syllavox. It is
an engineering release record, not legal advice. Dependency versions listed
below are the versions recorded from the environment used to produce the
v0.1.0 portable build on 2026-08-06. The accompanying
`DEPENDENCY_VERSIONS.txt` file in the portable build is the authoritative
machine-generated inventory for that artifact.

## Syllavox code

Syllavox's own source code is released under the MIT License. See
[`LICENSE`](LICENSE).

The MIT license applies to Syllavox code only. It does not relicense the
third-party engines, libraries, native binaries, or voice models used by the
application.

## Distribution model

The project has two different distribution forms:

1. The Python source/distribution package contains Syllavox code under MIT and
   declares its dependencies separately.
2. The portable Windows build bundles the Python runtime and dependencies into
   a distributable application folder. That build is a mixed-license
   distribution and must include this notice, the Syllavox MIT license, the
   applicable third-party license texts, and the relevant source links.

The portable build must not be described as MIT-only. In particular, the
bundled Piper engine is GPL-3.0-or-later. The final release must preserve the
corresponding-source and notice obligations for the GPL-covered components.

## Direct runtime dependencies

These are the direct runtime dependencies declared by `pyproject.toml` and the
main components they bring into the application.

| Component | Version observed | License | Upstream source |
|---|---:|---|---|
| `piper-tts` | 1.6.0 | GPL-3.0-or-later | [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) |
| `PySide6` / Qt for Python | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html) |
| `fastapi` | 0.141.1 | MIT | [FastAPI](https://github.com/fastapi/fastapi) |
| `uvicorn` | 0.52.1 | BSD-3-Clause | [Uvicorn](https://github.com/Kludex/uvicorn) |
| `pydantic` | 2.13.4 | MIT | [Pydantic](https://github.com/pydantic/pydantic) |

## Optional Sherpa-ONNX runtime

The `sherpa` optional dependency adds the following components only when a
Sherpa-enabled environment or portable build is explicitly requested:

| Component | Version pinned | License | Upstream source |
|---|---:|---|---|
| `sherpa-onnx` | 1.13.6 | Apache-2.0 | [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) |
| `sherpa-onnx-bin` | 1.13.6 | Apache-2.0 | [sherpa-onnx-bin on PyPI](https://pypi.org/project/sherpa-onnx-bin/) |

The Sherpa-ONNX runtime is optional and is not part of the base Piper-only
portable build. A Sherpa-enabled portable build collects its native
runtime files and applicable license texts; `DEPENDENCY_VERSIONS.txt` remains
the authoritative inventory for the actual artifact.

Sherpa model bundles, phonemization data, lexicons, and voice files are
separate works. Their licenses and redistribution terms come from each model's
upstream release or model card and are not covered by the Sherpa-ONNX runtime
license or Syllavox's MIT license.

PySide6 also installs the `PySide6_Essentials`, `PySide6_Addons`, and
`shiboken6` packages. They carry the same Qt for Python licensing choices and
are part of the portable-build review.

## Piper and Chinese-language runtime components

The `piper-tts[zh]` dependency adds or uses the following important runtime
components:

| Component | Version observed | License | Upstream source |
|---|---:|---|---|
| `g2pw` | 0.1.1 | Apache-2.0 | [GitYCC/g2pW](https://github.com/GitYCC/g2pW) |
| `sentence-stream` | 1.3.0 | Apache-2.0 | [OHF-Voice/sentence-stream](https://github.com/OHF-Voice/sentence-stream) |
| `unicode-rbnf` | 2.4.0 | MIT | [rhasspy/unicode-rbnf](https://github.com/rhasspy/unicode-rbnf) |
| `onnxruntime` | 1.28.0 | MIT | [ONNX Runtime](https://github.com/microsoft/onnxruntime) |
| `pathvalidate` | 3.3.1 | MIT | [pathvalidate](https://github.com/thombashi/pathvalidate) |
| `transformers` | 5.14.1 | Apache-2.0 | [Hugging Face Transformers](https://github.com/huggingface/transformers) |
| `huggingface-hub` | 1.26.0 | Apache-2.0 | [Hugging Face Hub](https://github.com/huggingface/huggingface_hub) |
| `requests` | 2.34.2 | Apache-2.0 | [Requests](https://github.com/psf/requests) |
| `torch` | 2.13.0 | BSD-style license; verify exact upstream notice at release | [PyTorch](https://github.com/pytorch/pytorch) |

The Piper package also includes native phonemization data and binaries. The
Piper source and license files are authoritative for those components and must
be retained or linked in the final release inventory.

## Native and transitive components

The current environment also contains transitive components such as NumPy,
protobuf, flatbuffers, Starlette, AnyIO, Click, h11, Jinja2, certifi,
charset-normalizer, urllib3, and their dependencies. Their licenses remain
those of their respective upstream distributions. The final portable-build
check must generate an exact package inventory from the environment used to
build that release; this document is the human-readable summary of the major
components, not a substitute for that final inventory.

The optional packaging extra uses PyInstaller. PyInstaller is GPLv2-or-later
with a special exception permitting distribution of programs built with it;
the PyInstaller license and exception text must remain available with the
release build. See [PyInstaller](https://github.com/pyinstaller/pyinstaller).

## Voice models and language resources

Syllavox does not bundle Piper voice models in the repository or portable
build. The complete developer backup at `..\piper_voice_backup\` is private
development safekeeping and is not a release asset.

Users install voices explicitly from the official
[Piper voice catalog](https://huggingface.co/rhasspy/piper-voices). Voice
models are separate works and are not covered by Syllavox's MIT license. The
catalog does not provide one blanket license for every voice: each voice's
model card and dataset source determine its applicable terms. The local
catalog includes examples of CC0, attribution, public-domain, attribution-
noncommercial, and other dataset conditions. Some model cards, including the
Chinese `xiao_ya` and Greek `joy` voices, contain non-commercial terms.

The application should continue to direct users to the upstream catalog and
model-card information. Syllavox must not mirror, bundle, or publicly host the
complete voice backup without a separate per-voice redistribution review.

The Chinese `g2pW` language resource is a separate runtime dependency. It is
covered by the `g2pw` package's upstream license and is not a Syllavox asset.

## Project-generated icon assets

The browser-extension icons in `extension/icons/` and the matching tray asset
at `src/syllavox/assets/tray_icon.png` were generated for Syllavox as an
original generic speech-and-sound mark. No third-party icon library, logo,
character, or source image was used for these assets, and no external
attribution is currently required for them. This statement should be retained
with the project provenance record.

## Portable-build release requirements

Before publishing a portable build:

- copy `LICENSE` and this file into the portable output;
- include the applicable dependency license texts, including Piper, Qt for
  Python, and PyInstaller materials;
- record the exact dependency versions used by the build;
- preserve upstream source links and GPL corresponding-source information;
- verify that no voice model or private voice backup has entered the archive;
- re-check each dependency and model-card license if the dependency set or
  voice catalog changes.
