"""Release metadata consistency checks."""

from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib

from syllavox.constants import APP_NAME, PACKAGE_NAME, PROJECT_VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _project_version_from_pyproject() -> str:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match is not None
    return match.group(1)


def test_release_version_is_consistent_across_project_metadata() -> None:
    assert PROJECT_VERSION == "0.6.0"
    assert _project_version_from_pyproject() == PROJECT_VERSION

    for manifest_name in ("manifest.json", "manifest.firefox.json"):
        manifest = json.loads(
            (PROJECT_ROOT / "extension" / manifest_name).read_text(
                encoding="utf-8"
            )
        )
        assert manifest["version"] == PROJECT_VERSION


def test_public_package_name_is_syllavox() -> None:
    assert APP_NAME == "Syllavox"
    assert PACKAGE_NAME == "syllavox"

    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "syllavox"' in pyproject
    assert 'syllavox = ["assets/*.png"]' in pyproject


def test_development_dependencies_declare_the_test_runner() -> None:
    project = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    development_requirements = project["project"]["optional-dependencies"]["dev"]

    assert any(
        requirement.startswith("pytest")
        for requirement in development_requirements
    )


def test_macos_packaging_metadata_and_build_script_are_present() -> None:
    project = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    macos_requirements = project["project"]["optional-dependencies"]["macos"]

    assert any(
        requirement.startswith("pyobjc-framework-Cocoa")
        for requirement in macos_requirements
    )
    assert any(
        requirement.startswith("pyobjc-framework-ServiceManagement")
        for requirement in macos_requirements
    )

    info_plist = (PROJECT_ROOT / "packaging" / "macos" / "Info.plist").read_text(
        encoding="utf-8"
    )
    macos_build_script = (PROJECT_ROOT / "packaging" / "build_macos.sh").read_text(
        encoding="utf-8"
    )

    assert "com.ruben-crespo-blanco.syllavox" in info_plist
    assert "LSMinimumSystemVersion" in info_plist
    assert ">11.0<" in info_plist
    assert 'PySide6>=6.5.2,<6.12' in project["project"]["dependencies"]
    assert '[[ "$(uname -s)" == "Darwin" ]]' in macos_build_script
    assert 'MACOSX_DEPLOYMENT_TARGET="11.0"' in macos_build_script
    assert "hdiutil create" in macos_build_script
    assert "notarytool submit" in macos_build_script


def test_windows_installer_is_per_user_and_uses_the_portable_output() -> None:
    installer_script = (PROJECT_ROOT / "packaging" / "Syllavox.iss").read_text(
        encoding="utf-8"
    )
    build_script = (PROJECT_ROOT / "packaging" / "build_installer.ps1").read_text(
        encoding="utf-8"
    )

    assert "PrivilegesRequired=lowest" in installer_script
    assert "DefaultDirName={localappdata}\\Programs\\Syllavox" in installer_script
    assert 'Source: "{#SourceDir}\\*"' in installer_script
    assert "StartupRegistrySubkey" in installer_script
    assert "DelTree(UserDataPath" in installer_script
    assert "-IncludeSapi" in build_script
    assert "-IncludeSherpa" in build_script
    assert "INNO_SETUP_COMPILER" in build_script
    assert "Get-FileHash" in build_script
