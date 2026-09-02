#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${PROJECT_ROOT}/build/linux"
DIST_ROOT="${BUILD_ROOT}/dist"
WORK_ROOT="${BUILD_ROOT}/work"
APP_ROOT="${DIST_ROOT}/Syllavox"

INCLUDE_SHERPA=0
SKIP_PYINSTALLER=0
SKIP_APPIMAGE=0

usage() {
    cat <<'EOF'
Usage: packaging/build_linux.sh [options]

Build the Syllavox Ubuntu-first Linux application artifacts.

Options:
  --include-sherpa    Include the optional Sherpa-ONNX runtime.
  --skip-pyinstaller  Reuse the existing build/linux/dist/Syllavox folder.
  --skip-appimage     Create the Debian package only.
EOF
}

die() {
    printf 'error: %s\n' "$1" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --include-sherpa)
            INCLUDE_SHERPA=1
            ;;
        --skip-pyinstaller)
            SKIP_PYINSTALLER=1
            ;;
        --skip-appimage)
            SKIP_APPIMAGE=1
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            die "unknown option: $1"
            ;;
    esac
    shift
done

[[ "$(uname -s)" == "Linux" ]] || die "this script must run on Linux"
command -v dpkg-deb >/dev/null 2>&1 || die "required command is missing: dpkg-deb"

PYTHON="${PYTHON:-${PROJECT_ROOT}/.venv/bin/python}"
[[ -x "${PYTHON}" ]] || die "Python executable not found: ${PYTHON}"

VERSION="$(${PYTHON} -c 'import pathlib, sys; toml = __import__("tomllib") if sys.version_info >= (3, 11) else __import__("tomli"); print(toml.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["project"]["version"])' \
    "${PROJECT_ROOT}/pyproject.toml")"
MACHINE_ARCH="$(uname -m)"
case "${MACHINE_ARCH}" in
    x86_64|amd64)
        DEB_ARCH="amd64"
        ;;
    aarch64|arm64)
        DEB_ARCH="arm64"
        ;;
    *)
        die "unsupported Linux architecture: ${MACHINE_ARCH}"
        ;;
esac

ARTIFACT_STEM="Syllavox-${VERSION}-linux-${DEB_ARCH}"
DEB_PATH="${BUILD_ROOT}/${ARTIFACT_STEM}.deb"
APPIMAGE_PATH="${BUILD_ROOT}/${ARTIFACT_STEM}.AppImage"

mkdir -p "${BUILD_ROOT}" "${DIST_ROOT}" "${WORK_ROOT}"

if [[ "${SKIP_PYINSTALLER}" -eq 0 ]]; then
    export SYLLAVOX_INCLUDE_SHERPA="${INCLUDE_SHERPA}"
    export SYLLAVOX_INCLUDE_SAPI=0
    export SYLLAVOX_INCLUDE_LINUX=1

    "${PYTHON}" -m PyInstaller \
        --noconfirm \
        --clean \
        --distpath "${DIST_ROOT}" \
        --workpath "${WORK_ROOT}" \
        "${PROJECT_ROOT}/packaging/syllavox.spec"
fi

[[ -x "${APP_ROOT}/Syllavox" ]] || die "PyInstaller did not create ${APP_ROOT}/Syllavox"

DESKTOP_FILE="${PROJECT_ROOT}/packaging/linux/com.ruben-crespo-blanco.syllavox.desktop"
METAINFO_FILE="${PROJECT_ROOT}/packaging/linux/com.ruben-crespo-blanco.syllavox.metainfo.xml"
ICON_SOURCE="${PROJECT_ROOT}/src/syllavox/assets/tray_icon.png"
[[ -f "${DESKTOP_FILE}" ]] || die "desktop file not found: ${DESKTOP_FILE}"
[[ -f "${METAINFO_FILE}" ]] || die "AppStream metadata not found: ${METAINFO_FILE}"
[[ -f "${ICON_SOURCE}" ]] || die "icon source not found: ${ICON_SOURCE}"

DEB_ROOT="${BUILD_ROOT}/debroot"
rm -rf "${DEB_ROOT}"
mkdir -p \
    "${DEB_ROOT}/DEBIAN" \
    "${DEB_ROOT}/usr/lib/syllavox" \
    "${DEB_ROOT}/usr/share/applications" \
    "${DEB_ROOT}/usr/share/metainfo" \
    "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps" \
    "${DEB_ROOT}/usr/share/doc/syllavox"
cp -a "${APP_ROOT}/." "${DEB_ROOT}/usr/lib/syllavox/"
cp "${DESKTOP_FILE}" \
    "${DEB_ROOT}/usr/share/applications/com.ruben-crespo-blanco.syllavox.desktop"
cp "${METAINFO_FILE}" \
    "${DEB_ROOT}/usr/share/metainfo/com.ruben-crespo-blanco.syllavox.metainfo.xml"
cp "${ICON_SOURCE}" \
    "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps/com.ruben-crespo-blanco.syllavox.png"
for document in LICENSE THIRD_PARTY_NOTICES.md CHANGELOG.md; do
    [[ -f "${PROJECT_ROOT}/${document}" ]] || die "missing release document: ${document}"
    cp "${PROJECT_ROOT}/${document}" "${DEB_ROOT}/usr/share/doc/syllavox/${document}"
done

cat > "${DEB_ROOT}/DEBIAN/control" <<EOF
Package: syllavox
Version: ${VERSION}
Section: sound
Priority: optional
Architecture: ${DEB_ARCH}
Maintainer: Rubén Crespo Blanco <rcresb@gmail.com>
Depends: libc6, libglib2.0-0, libfontconfig1, libfreetype6, libx11-6, libx11-xcb1, libxcb1, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-shm0, libxcb-xfixes0, libxcb-xkb1, libxkbcommon0, libxkbcommon-x11-0, libasound2 | libasound2t64
Description: Local offline text-to-speech reader
 Syllavox reads text aloud locally using installed offline speech engines.
 Piper is included in the application runtime; voice models are downloaded
 separately by the user.
EOF

rm -f "${DEB_PATH}"
dpkg-deb --build --root-owner-group "${DEB_ROOT}" "${DEB_PATH}" >/dev/null

if [[ "${SKIP_APPIMAGE}" -eq 0 ]]; then
    APPIMAGE_TOOL="${APPIMAGE_TOOL:-}"
    if [[ -z "${APPIMAGE_TOOL}" ]]; then
        APPIMAGE_TOOL="$(command -v appimagetool || true)"
    fi
    [[ -x "${APPIMAGE_TOOL}" ]] || die "appimagetool not found; install it or use --skip-appimage"

    APPDIR="${BUILD_ROOT}/AppDir"
    rm -rf "${APPDIR}"
    mkdir -p \
        "${APPDIR}/usr/lib/syllavox" \
        "${APPDIR}/usr/share/applications" \
        "${APPDIR}/usr/share/metainfo" \
        "${APPDIR}/usr/share/icons/hicolor/256x256/apps"
    cp -a "${APP_ROOT}/." "${APPDIR}/usr/lib/syllavox/"
    cp "${DESKTOP_FILE}" \
        "${APPDIR}/usr/share/applications/com.ruben-crespo-blanco.syllavox.desktop"
    sed -i 's#^Exec=.*#Exec=Syllavox#' \
        "${APPDIR}/usr/share/applications/com.ruben-crespo-blanco.syllavox.desktop"
    cp "${METAINFO_FILE}" \
        "${APPDIR}/usr/share/metainfo/com.ruben-crespo-blanco.syllavox.metainfo.xml"
    cp "${ICON_SOURCE}" \
        "${APPDIR}/usr/share/icons/hicolor/256x256/apps/com.ruben-crespo-blanco.syllavox.png"
    cat > "${APPDIR}/AppRun" <<'EOF'
#!/bin/sh
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec "${HERE}/usr/lib/syllavox/Syllavox" "$@"
EOF
    chmod +x "${APPDIR}/AppRun"

    rm -f "${APPIMAGE_PATH}"
    "${APPIMAGE_TOOL}" "${APPDIR}" "${APPIMAGE_PATH}"
fi

printf 'Created Linux artifacts in %s:\n' "${BUILD_ROOT}"
printf '  %s\n' "${DEB_PATH}"
if [[ "${SKIP_APPIMAGE}" -eq 0 ]]; then
    printf '  %s\n' "${APPIMAGE_PATH}"
fi
