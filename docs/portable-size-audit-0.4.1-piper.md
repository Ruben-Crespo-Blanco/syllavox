# Runtime audit: piper-only

This report combines the declared project metadata with distribution metadata from the selected bundle or local environment.

## Declared runtime dependencies

- `PySide6>=6.10.1,<6.11`
- `fastapi`
- `uvicorn`
- `pydantic`
- `piper-tts[zh]`

## Optional dependency groups

### `dev`

- `pytest>=8.0`

### `packaging`

- `pyinstaller>=6.0`

### `sherpa`

- `sherpa-onnx==1.13.6`
- `sherpa-onnx-bin==1.13.6`

## Bundled runtime distribution inventory

Source: `build\portable\Syllavox\_internal`

Distributions discovered: **18**

- `click==8.5.0`
- `fastapi==0.141.1`
- `filelock==3.32.4`
- `huggingface_hub==1.29.0`
- `numpy==2.5.2`
- `packaging==26.3`
- `protobuf==7.36.0`
- `pydantic==2.13.4`
- `PyYAML==6.0.3`
- `regex==2026.7.19`
- `rich==15.0.0`
- `safetensors==0.8.0`
- `starlette==1.6.0`
- `tokenizers==0.23.1`
- `tqdm==4.70.0`
- `typer==0.27.1`
- `unicode-rbnf==2.4.0`
- `uvicorn==0.52.4`

## Portable artifact

Path: `build\portable\Syllavox`

Total size: **325.4 MiB** (341238466 bytes)
File count: **3189**

### Largest top-level entries

| Entry | Size |
|---|---:|
| `_internal` | 296.4 MiB |
| `Syllavox.exe` | 29.0 MiB |
| `licenses` | 66.8 KiB |
| `THIRD_PARTY_NOTICES.md` | 7.7 KiB |
| `CHANGELOG.md` | 6.9 KiB |
| `LICENSE` | 1.1 KiB |
| `PORTABLE_README.txt` | 1.0 KiB |
| `DEPENDENCY_VERSIONS.txt` | 532.0 B |

### File-type totals

| Extension | Files | Size |
|---|---:|---:|
| `.dll` | 110 | 147.5 MiB |
| `.pyd` | 49 | 54.8 MiB |
| `.py` | 2291 | 38.1 MiB |
| `.exe` | 1 | 29.0 MiB |
| `.onnx` | 2 | 24.9 MiB |
| `[no extension]` | 466 | 18.8 MiB |
| `.qm` | 124 | 6.5 MiB |
| `.json` | 7 | 1.9 MiB |
| `.zip` | 1 | 1.3 MiB |
| `.xml` | 91 | 1.1 MiB |
| `.png` | 3 | 951.9 KiB |
| `.pem` | 1 | 234.6 KiB |
| `.txt` | 22 | 110.1 KiB |
| `.md` | 14 | 35.0 KiB |
| `.html` | 1 | 18.9 KiB |
| `.apache` | 1 | 9.9 KiB |
| `.bsd` | 1 | 1.3 KiB |
| `.pyi` | 1 | 574.0 B |
| `.typed` | 3 | 0.0 B |
