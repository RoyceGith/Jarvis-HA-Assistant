#!/usr/bin/env python3
"""Export the allowlisted public Home Assistant distribution repository."""

from __future__ import annotations

from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "distribution" / "public-repository"
ALLOWED_FILES = {
    "README.md",
    "repository.yaml",
    "jarvis/CHANGELOG.md",
    "jarvis/README.md",
    "jarvis/config.yaml",
}


def export(destination: Path) -> set[str]:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "repository.yaml", destination / "repository.yaml")
    shutil.copy2(TEMPLATE / "README.md", destination / "README.md")
    app = destination / "jarvis"
    app.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "jarvis" / "config.yaml", app / "config.yaml")
    shutil.copy2(TEMPLATE / "jarvis" / "README.md", app / "README.md")
    shutil.copy2(TEMPLATE / "jarvis" / "CHANGELOG.md", app / "CHANGELOG.md")
    exported = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    unexpected = exported - ALLOWED_FILES
    missing = ALLOWED_FILES - exported
    if unexpected or missing:
        raise RuntimeError(f"invalid public export: unexpected={sorted(unexpected)}, missing={sorted(missing)}")
    return exported


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: export_public_repository.py DESTINATION", file=sys.stderr)
        return 2
    exported = export(Path(sys.argv[1]).resolve())
    print(f"Exported {len(exported)} allowlisted public repository files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
