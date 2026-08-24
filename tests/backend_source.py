from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"


def load_backend_source() -> str:
    """Return the entry point plus direct backend service sources for tests."""
    sources = [(APP / "main.py").read_text(encoding="utf-8")]
    schema_source = (APP / "schemas.py").read_text(encoding="utf-8")
    sources.append(schema_source.replace("from __future__ import annotations\n", "", 1))
    for directory in (APP / "services", APP / "domains"):
        for path in sorted(directory.glob("*.py")):
            if path.name == "__init__.py":
                continue
            source = path.read_text(encoding="utf-8")
            source = source.replace("from __future__ import annotations\n", "", 1)
            sources.append(source)
    return "\n".join(sources)
