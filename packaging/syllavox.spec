"""PyInstaller specification for the portable Windows application."""

from pathlib import Path

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
tray_icon_datas = [
    (
        str(PROJECT_ROOT / "src" / "syllavox" / "assets" / "tray_icon.png"),
        "syllavox/assets",
    )
]

analysis = Analysis(
    [str(PROJECT_ROOT / "packaging" / "entrypoint.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=piper_binaries + g2pw_binaries + onnx_binaries,
    datas=(
        piper_datas
        + g2pw_datas
        + unicode_rbnf_datas
        + tray_icon_datas
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
