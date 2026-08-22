from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.18 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    require(backend, 'version="0.12.17"', "backend version")
    require(frontend, "HUD 0.12.17", "frontend version")

    run_marker = "\nasync def run_jarvis("
    capacity_helper = r'''

def runtime_tool_round_limit(session_id: str) -> int:
    """Bound tool loops while giving approved multi-note tasks enough capacity."""
    if developer_mode_enabled():
        return 12
    if workshop_memory_task_approval_active(session_id):
        return 24
    return 12
'''
    backend = replace_once(
        backend,
        run_marker,
        capacity_helper + run_marker,
        "runtime tool-loop entry",
    )

    old_limit = "    max_tool_rounds = 12 if developer_mode_enabled() else 5"
    require(backend, old_limit, "normal tool round limits")
    if backend.count(old_limit) != 2:
        raise RuntimeError(
            "ZBRANO v0.12.18 expected exactly two normal/stream tool round limits"
        )
    backend = backend.replace(
        old_limit,
        "    max_tool_rounds = runtime_tool_round_limit(session_id)",
    )

    policy_marker = '''that tool can create missing folders and the note in one approved operation.'''
    policy_replacement = policy_marker + r'''
For project-wide content edits, discover and read each relevant note only once,
then batch independent write calls into as few response rounds as possible. Do
not repeatedly reread a note after a successful write merely to confirm it. If
the Workshop Memory server has no bulk replacement tool, update each relevant
note exactly once under task approval and report the completed scope.'''
    backend = replace_once(
        backend,
        policy_marker,
        policy_replacement,
        "Workshop Memory bulk-edit guidance",
    )

    backend = backend.replace('version="0.12.17"', 'version="0.12.18"')
    backend = backend.replace('"version": "0.12.17"', '"version": "0.12.18"')
    frontend = frontend.replace("HUD 0.12.17", "HUD 0.12.18")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


def verify() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    required_backend = (
        'version="0.12.18"',
        '"version": "0.12.18"',
        "def runtime_tool_round_limit(session_id: str) -> int:",
        "if workshop_memory_task_approval_active(session_id):",
        "return 24",
        "max_tool_rounds = runtime_tool_round_limit(session_id)",
        "batch independent write calls",
        "update each relevant",
        "note exactly once under task approval",
    )
    for marker in required_backend:
        require(backend, marker, marker)
    if backend.count("max_tool_rounds = runtime_tool_round_limit(session_id)") != 2:
        raise RuntimeError("ZBRANO v0.12.18 did not update both chat execution paths")
    require(frontend, "HUD 0.12.18", "HUD version")


if __name__ == "__main__":
    main()
    verify()
