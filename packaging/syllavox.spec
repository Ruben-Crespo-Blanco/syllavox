"""PyInstaller specification for the Syllavox desktop applications."""

from pathlib import Path
import os
import plistlib
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 packaging
    import tomli as tomllib

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)
from PyInstaller.building.osx import BUNDLE


PROJECT_ROOT = Path(SPECPATH).parent
APPLICATION_NAME = "Syllavox"
IS_MACOS = sys.platform == "darwin"
PROJECT_VERSION = tomllib.loads(
    (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
)["project"]["version"]

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
sapi_datas = []
sapi_binaries = []
sapi_hiddenimports = []
linux_datas = []
linux_binaries = []
linux_hiddenimports = []

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

if os.environ.get("SYLLAVOX_INCLUDE_SAPI") == "1":
    try:
        import comtypes  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "SAPI packaging was requested, but the optional dependency "
            "is not installed. Run: python -m pip install -e .[sapi]"
        ) from exc

    # Only the generated COM wrappers and runtime bridge are needed. A full
    # collect_submodules("comtypes") would pull in comtypes' test suite and
    # unrelated server helpers, defeating the small optional-build goal.
    sapi_datas = collect_data_files("comtypes.gen", include_py_files=True)
    sapi_hiddenimports = [
        "comtypes",
        "comtypes.client",
        "comtypes.gen",
        "comtypes.gen.SpeechLib",
        *collect_submodules("comtypes.gen"),
        "comtypes.automation",
        "comtypes.typeinfo",
    ]

if os.environ.get("SYLLAVOX_INCLUDE_LINUX") == "1":
    try:
        import dbus_next  # noqa: F401
        import Xlib  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Linux packaging was requested, but the optional Linux "
            "dependencies are not installed. Run: python -m pip install "
            "-e .[linux]"
        ) from exc

    linux_datas = collect_data_files("dbus_next", include_py_files=True)
    linux_datas += collect_data_files("Xlib", include_py_files=True)
    linux_hiddenimports = [
        *collect_submodules("dbus_next"),
        *collect_submodules("Xlib"),
    ]
tray_icon_datas = [
    (
        str(PROJECT_ROOT / "src" / "syllavox" / "assets" / "tray_icon.png"),
        "syllavox/assets",
    )
]

# These packages are installed in the development environment but are not
# needed by the desktop runtime. The Qt modules below are not imported by
# Syllavox; excluding them prevents PyInstaller from collecting their large
# native libraries while retaining QtCore, QtGui, QtNetwork, QtMultimedia,
# and QtWidgets. The exclusions are verified by the clean portable launch
# probe and the application regression suite.
runtime_excludes = [
    "hf_xet",
    "pip",
    "pytest",
    "setuptools",
    "wheel",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DExtras",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtLocation",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtPrintSupport",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.QtXml",
]

if os.environ.get("SYLLAVOX_INCLUDE_SHERPA") != "1":
    # The application keeps the Sherpa import lazy, but PyInstaller can still
    # see the optional import path during analysis. Exclude the optional
    # package from the ordinary Piper-only build; the Sherpa-enabled build
    # intentionally collects it through the conditional block above.
    runtime_excludes.extend([
        "sherpa_onnx",
        "sherpa_onnx.*",
    ])

if os.environ.get("SYLLAVOX_INCLUDE_SAPI") != "1":
    runtime_excludes.extend([
        "comtypes",
        "comtypes.*",
    ])

if os.environ.get("SYLLAVOX_INCLUDE_LINUX") != "1":
    runtime_excludes.extend([
        "dbus_next",
        "dbus_next.*",
        "Xlib",
        "Xlib.*",
    ])

excluded_qt_binary_suffixes = {
    "pyside6/qt6quick.dll",
    "pyside6/qt6qml.dll",
    "pyside6/qt6pdf.dll",
    "pyside6/qt6opengl.dll",
    "pyside6/qt6openglwidgets.dll",
    "pyside6/opengl32sw.dll",
    "pyside6/qtquick.pyd",
    "pyside6/qtqml.pyd",
    "pyside6/qtpdf.pyd",
    "pyside6/qtpdfwidgets.pyd",
    "pyside6/qtopengl.pyd",
    "pyside6/qtopenglwidgets.pyd",
}


def _keep_runtime_binary(binary_entry):
    """Drop Qt binary modules that Syllavox never imports."""
    destination = str(binary_entry[0]).replace("\\", "/").lower()
    return not any(
        destination.endswith(suffix)
        for suffix in excluded_qt_binary_suffixes
    )

analysis = Analysis(
    [str(PROJECT_ROOT / "packaging" / "entrypoint.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=(
        piper_binaries
        + g2pw_binaries
        + onnx_binaries
        + sherpa_binaries
        + sapi_binaries
        + linux_binaries
    ),
    datas=(
        piper_datas
        + g2pw_datas
        + unicode_rbnf_datas
        + tray_icon_datas
        + sherpa_datas
        + sapi_datas
        + linux_datas
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
        *sapi_hiddenimports,
        *linux_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(PROJECT_ROOT / "packaging" / "pyside6_runtime_hook.py")],
    excludes=runtime_excludes,
    noarchive=False,
)

analysis.binaries = [
    binary_entry
    for binary_entry in analysis.binaries
    if _keep_runtime_binary(binary_entry)
]

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

if IS_MACOS:
    macos_info_plist = {}
    info_plist_path = os.environ.get("SYLLAVOX_MACOS_INFO_PLIST")
    if info_plist_path:
        with open(info_plist_path, "rb") as info_plist_file:
            macos_info_plist = plistlib.load(info_plist_file)

    macos_icon_path = os.environ.get("SYLLAVOX_MACOS_ICON")
    app = BUNDLE(
        executable,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=False,
        name=f"{APPLICATION_NAME}.app",
        version=PROJECT_VERSION,
        icon=(macos_icon_path if macos_icon_path else None),
        bundle_identifier="com.ruben-crespo-blanco.syllavox",
        info_plist=macos_info_plist,
    )
else:
    COLLECT(
        executable,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APPLICATION_NAME,
    )
