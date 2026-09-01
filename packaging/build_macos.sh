#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${PROJECT_ROOT}/build/macos"
DIST_ROOT="${BUILD_ROOT}/dist"
WORK_ROOT="${BUILD_ROOT}/work"
APP_PATH="${DIST_ROOT}/Syllavox.app"

INCLUDE_SHERPA=0
SKIP_PYINSTALLER=0
SKIP_DMG=0

usage() {
    cat <<'EOF'
Usage: packaging/build_macos.sh [options]

Build the Syllavox macOS application bundle and distributable archives.

Options:
  --include-sherpa    Include the optional Sherpa-ONNX runtime.
  --skip-pyinstaller  Reuse the existing app bundle in build/macos/dist.
  --skip-dmg          Create the ZIP only; do not create a DMG.
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
        --skip-dmg)
            SKIP_DMG=1
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

[[ "$(uname -s)" == "Darwin" ]] || die "this script must run on macOS"

for required_command in sips iconutil ditto shasum; do
    command -v "${required_command}" >/dev/null 2>&1 || \
        die "required macOS command is missing: ${required_command}"
done

if [[ "${SKIP_DMG}" -eq 0 ]]; then
    command -v hdiutil >/dev/null 2>&1 || \
        die "required macOS command is missing: hdiutil"
fi

PYTHON="${PYTHON:-${PROJECT_ROOT}/.venv/bin/python}"
[[ -x "${PYTHON}" ]] || die "Python executable not found: ${PYTHON}"

VERSION="$("${PYTHON}" -c 'import pathlib, sys, tomllib; print(tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["project"]["version"])' \
    "${PROJECT_ROOT}/pyproject.toml")"
ARCH="$(uname -m)"
ARTIFACT_STEM="Syllavox-${VERSION}-macos-${ARCH}"
APP_ZIP="${BUILD_ROOT}/${ARTIFACT_STEM}.zip"
DMG_PATH="${BUILD_ROOT}/${ARTIFACT_STEM}.dmg"
CHECKSUM_PATH="${BUILD_ROOT}/${ARTIFACT_STEM}.sha256"

mkdir -p "${BUILD_ROOT}" "${DIST_ROOT}" "${WORK_ROOT}"

ICON_SOURCE="${PROJECT_ROOT}/src/syllavox/assets/tray_icon.png"
ICONSET_ROOT="${BUILD_ROOT}/Syllavox.iconset"
ICON_PATH="${BUILD_ROOT}/Syllavox.icns"
[[ -f "${ICON_SOURCE}" ]] || die "icon source not found: ${ICON_SOURCE}"

rm -rf "${ICONSET_ROOT}"
mkdir -p "${ICONSET_ROOT}"

for size in 16 32 128 256 512; do
    sips -z "${size}" "${size}" "${ICON_SOURCE}" \
        --out "${ICONSET_ROOT}/icon_${size}x${size}.png" >/dev/null
    double_size=$((size * 2))
    sips -z "${double_size}" "${double_size}" "${ICON_SOURCE}" \
        --out "${ICONSET_ROOT}/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "${ICONSET_ROOT}" -o "${ICON_PATH}"

if [[ "${SKIP_PYINSTALLER}" -eq 0 ]]; then
    export SYLLAVOX_INCLUDE_SHERPA="${INCLUDE_SHERPA}"
    export SYLLAVOX_INCLUDE_SAPI=0
    export SYLLAVOX_MACOS_INFO_PLIST="${PROJECT_ROOT}/packaging/macos/Info.plist"
    export SYLLAVOX_MACOS_ICON="${ICON_PATH}"
    export MACOSX_DEPLOYMENT_TARGET="11.0"

    "${PYTHON}" -m PyInstaller \
        --noconfirm \
        --clean \
        --distpath "${DIST_ROOT}" \
        --workpath "${WORK_ROOT}" \
        "${PROJECT_ROOT}/packaging/syllavox.spec"
fi

[[ -d "${APP_PATH}" ]] || die "PyInstaller did not create ${APP_PATH}"

RESOURCE_ROOT="${APP_PATH}/Contents/Resources"
mkdir -p "${RESOURCE_ROOT}"
for document in LICENSE THIRD_PARTY_NOTICES.md CHANGELOG.md; do
    [[ -f "${PROJECT_ROOT}/${document}" ]] || die "missing release document: ${document}"
    cp "${PROJECT_ROOT}/${document}" "${RESOURCE_ROOT}/${document}"
done

if [[ -n "${SIGN_IDENTITY:-}" ]]; then
    codesign \
        --deep \
        --force \
        --options runtime \
        --timestamp \
        --sign "${SIGN_IDENTITY}" \
        "${APP_PATH}"
fi

rm -f "${APP_ZIP}" "${DMG_PATH}" "${CHECKSUM_PATH}"
ditto -c -k --sequesterRsrc --keepParent "${APP_PATH}" "${APP_ZIP}"

if [[ "${SKIP_DMG}" -eq 0 ]]; then
    hdiutil create \
        -volname "Syllavox ${VERSION}" \
        -srcfolder "${APP_PATH}" \
        -ov \
        -format UDZO \
        "${DMG_PATH}" >/dev/null

    if [[ -n "${NOTARY_PROFILE:-}" ]]; then
        xcrun notarytool submit "${DMG_PATH}" \
            --keychain-profile "${NOTARY_PROFILE}" \
            --wait
        xcrun stapler staple "${DMG_PATH}"
    fi
fi

{
    shasum -a 256 "${APP_ZIP}"
    if [[ "${SKIP_DMG}" -eq 0 ]]; then
        shasum -a 256 "${DMG_PATH}"
    fi
} > "${CHECKSUM_PATH}"

printf 'Created macOS artifacts in %s:\n' "${BUILD_ROOT}"
printf '  %s\n' "${APP_ZIP}"
if [[ "${SKIP_DMG}" -eq 0 ]]; then
    printf '  %s\n' "${DMG_PATH}"
fi
printf '  %s\n' "${CHECKSUM_PATH}"
