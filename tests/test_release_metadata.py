"""Release metadata consistency checks."""

from __future__ import annotations

import json
from pathlib import Path
import re

from syllavox.constants import APP_NAME, PACKAGE_NAME, PROJECT_VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _project_version_from_pyproject() -> str:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match is not None
    return match.group(1)


def test_release_version_is_consistent_across_project_metadata() -> None:
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
