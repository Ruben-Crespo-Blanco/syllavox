"""Audit runtime dependencies and frozen portable-build contents.

The report is intentionally dependency-free so it can run from a source
checkout before the optional Sherpa environment is installed. It combines the
declared runtime requirements with distribution metadata from the selected
bundle or local environment, then reports portable artifact size, file-type
totals, and largest top-level entries.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


_REQUIREMENT_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)")


def _human_size(size: int) -> str:
    value = float(size)
    for suffix in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or suffix == "GiB":
            return f"{value:.1f} {suffix}"
        value /= 1024
    return f"{size} B"


def _requirement_name(requirement: str) -> str:
    match = _REQUIREMENT_NAME.match(requirement.strip())
    return match.group(1) if match else requirement


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size if path.is_file() else 0
    except OSError:
        return 0


def _tree_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(_file_size(child) for child in path.rglob("*"))


def _top_level_sizes(root: Path) -> list[tuple[str, int]]:
    entries: list[tuple[str, int]] = []
    for child in root.iterdir():
        size = _tree_size(child) if child.is_dir() else _file_size(child)
        entries.append((child.name, size))
    return sorted(entries, key=lambda item: item[1], reverse=True)


def _extension_sizes(root: Path) -> list[tuple[str, int, int]]:
    totals: dict[str, tuple[int, int]] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower() or "[no extension]"
        count, size = totals.get(suffix, (0, 0))
        totals[suffix] = (count + 1, size + _file_size(path))
    return sorted(
        ((suffix, count, size) for suffix, (count, size) in totals.items()),
        key=lambda item: item[2],
        reverse=True,
    )


def _dist_info(site_packages: Path) -> list[tuple[str, str]]:
    distributions: list[tuple[str, str]] = []
    for metadata_path in sorted(site_packages.glob("*.dist-info/METADATA")):
        name: str | None = None
        version: str | None = None
        try:
            for line in metadata_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines():
                if line.startswith("Name:"):
                    name = line.partition(":")[2].strip()
                elif line.startswith("Version:"):
                    version = line.partition(":")[2].strip()
        except OSError:
            continue
        if name and version:
            distributions.append((name, version))
    return distributions


def _find_site_packages(project_root: Path) -> Path | None:
    candidates = [
        project_root / ".venv" / "Lib" / "site-packages",
        project_root / ".venv" / "lib",
    ]
    for candidate in candidates:
        if candidate.name == "site-packages" and candidate.is_dir():
            return candidate
        if candidate.is_dir():
            matches = sorted(candidate.glob("python*/site-packages"))
            if matches:
                return matches[0]
    return None


def _declared_requirements(project_root: Path) -> tuple[list[str], dict[str, list[str]]]:
    with (project_root / "pyproject.toml").open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)["project"]
    return list(project.get("dependencies", [])), {
        str(name): list(requirements)
        for name, requirements in project.get("optional-dependencies", {}).items()
    }


def _render_report(
    project_root: Path,
    portable: Path | None,
    compare: Path | None,
    site_packages: Path | None,
    label: str,
) -> str:
    dependencies, optional_dependencies = _declared_requirements(project_root)
    lines = [
        f"# Runtime audit: {label}",
        "",
        "This report combines the declared project metadata with distribution "
        "metadata from the selected bundle or local environment.",
        "",
        "## Declared runtime dependencies",
        "",
    ]
    lines.extend(f"- `{dependency}`" for dependency in dependencies)

    lines.extend(["", "## Optional dependency groups", ""])
    for group, requirements in sorted(optional_dependencies.items()):
        lines.append(f"### `{group}`")
        lines.append("")
        lines.extend(f"- `{requirement}`" for requirement in requirements)
        lines.append("")

    if site_packages is not None:
        distributions = _dist_info(site_packages)
        inventory_title = (
            "Bundled runtime distribution inventory"
            if site_packages.name == "_internal"
            else "Local distribution inventory"
        )
        lines.extend([
            f"## {inventory_title}",
            "",
            f"Source: `{site_packages}`",
            "",
            f"Distributions discovered: **{len(distributions)}**",
            "",
        ])
        lines.extend(
            f"- `{name}=={version}`" for name, version in distributions
        )
        lines.append("")

    if portable is None:
        return "\n".join(lines).rstrip() + "\n"

    total_size = _tree_size(portable)
    file_count = sum(1 for path in portable.rglob("*") if path.is_file())
    lines.extend([
        "## Portable artifact",
        "",
        f"Path: `{portable}`",
        "",
        f"Total size: **{_human_size(total_size)}** ({total_size} bytes)",
        f"File count: **{file_count}**",
        "",
        "### Largest top-level entries",
        "",
        "| Entry | Size |",
        "|---|---:|",
    ])
    lines.extend(
        f"| `{name}` | {_human_size(size)} |"
        for name, size in _top_level_sizes(portable)[:20]
    )
    lines.extend([
        "",
        "### File-type totals",
        "",
        "| Extension | Files | Size |",
        "|---|---:|---:|",
    ])
    lines.extend(
        f"| `{suffix}` | {count} | {_human_size(size)} |"
        for suffix, count, size in _extension_sizes(portable)[:20]
    )

    if compare is not None and compare.exists():
        compare_size = _tree_size(compare)
        delta = total_size - compare_size
        sign = "+" if delta >= 0 else "-"
        lines.extend([
            "",
            "### Comparison",
            "",
            f"Compared with `{compare}`: {_human_size(compare_size)}",
            f"Difference: **{sign}{_human_size(abs(delta))}** ({delta} bytes)",
        ])

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--portable",
        type=Path,
        help="Frozen portable folder to measure.",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        help="Optional second portable folder for a size comparison.",
    )
    parser.add_argument(
        "--site-packages",
        type=Path,
        help="Python site-packages directory to inventory.",
    )
    parser.add_argument(
        "--label",
        default="local",
        help="Report label (default: local).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional Markdown output path.",
    )
    args = parser.parse_args(argv)

    site_packages = args.site_packages
    if site_packages is None and args.portable is not None:
        bundled_runtime = args.portable / "_internal"
        if bundled_runtime.is_dir():
            site_packages = bundled_runtime
    if site_packages is None:
        site_packages = _find_site_packages(project_root)
    report = _render_report(
        project_root=project_root,
        portable=args.portable,
        compare=args.compare,
        site_packages=site_packages,
        label=args.label,
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
