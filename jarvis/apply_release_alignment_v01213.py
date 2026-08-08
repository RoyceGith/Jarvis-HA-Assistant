from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.13 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    require(backend, 'version="0.12.12"', "backend version")
    require(backend, "summarize_workshop_memory_arguments", "private approval summaries")
    require(backend, "WORKSHOP_TASK_APPROVAL_GRANTS", "task-scoped approvals")
    require(frontend, "HUD 0.12.12", "frontend version")
    backend = backend.replace('version="0.12.12"', 'version="0.12.13"')
    backend = backend.replace('"version": "0.12.12"', '"version": "0.12.13"')
    frontend = frontend.replace("HUD 0.12.12", "HUD 0.12.13")
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


def verify() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    for marker in (
        'version="0.12.13"',
        "summarize_workshop_memory_arguments",
        "WORKSHOP_TASK_APPROVAL_GRANTS",
        "write_project_note",
    ):
        require(backend, marker, marker)
    require(frontend, "HUD 0.12.13", "HUD 0.12.13")


if __name__ == "__main__":
    main()
    verify()
