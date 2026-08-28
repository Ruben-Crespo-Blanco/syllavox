"""PyInstaller specification for the portable Windows application."""

from pathlib import Path
import os

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)


PROJECT_ROOT = Path(SPECPATH).parent
APPLICATION_NAME = "Syllavox"

piper_datas = collect_data_files("piper")
piper_binaries = collect_dynamic_libs("piper")
# Keep the Python files beside g2pw's package data. This avoids a data-only
# directory shadowing the frozen package at runtime.
g2pw_datas = collect_data_files("g2pw", include_py_files=True)
g2pw_binaries = collect_dynamic_libs("g2pw")
g2pw_hiddenimports = collect_submodules("g2pw")
unicode_rbnf_datas = collect_data_files("unicode_rbnf", include_py_files=True)
onnx_binaries = collect_dynamic_libs("onnxruntime")
sherpa_datas = []
sherpa_binaries = []
sherpa_hiddenimports = []

if os.environ.get("SYLLAVOX_INCLUDE_SHERPA") == "1":
    try:
        import sherpa_onnx  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Sherpa packaging was requested, but the optional dependency "
            "is not installed. Run: python -m pip install -e .[sherpa]"
        ) from exc

    sherpa_datas = collect_data_files("sherpa_onnx", include_py_files=True)
    sherpa_binaries = collect_dynamic_libs("sherpa_onnx")
    sherpa_hiddenimports = collect_submodules("sherpa_onnx")
tray_icon_datas = [
    (
        str(PROJECT_ROOT / "src" / "syllavox" / "assets" / "tray_icon.png"),
        "syllavox/assets",
    )
]

analysis = Analysis(
    [str(PROJECT_ROOT / "packaging" / "entrypoint.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=(
        piper_binaries
        + g2pw_binaries
        + onnx_binaries
        + sherpa_binaries
    ),
    datas=(
        piper_datas
        + g2pw_datas
        + unicode_rbnf_datas
        + tray_icon_datas
        + sherpa_datas
    ),
    hiddenimports=[
        "piper",
        "piper.voice",
        "piper.config",
        "piper.const",
        "piper.phoneme_ids",
        "piper.phonemize_espeak",
        "piper.phonemize_chinese",
        "piper.tashkeel",
        *g2pw_hiddenimports,
        "sentence_stream",
        "unicode_rbnf",
        "onnxruntime",
        "onnxruntime.capi._pybind_state",
        *sherpa_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(PROJECT_ROOT / "packaging" / "pyside6_runtime_hook.py")],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=APPLICATION_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APPLICATION_NAME,
)
