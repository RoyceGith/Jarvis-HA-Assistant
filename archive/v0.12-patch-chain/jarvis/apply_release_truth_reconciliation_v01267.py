from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.67 expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''    "already_present": False,
}''',
        '''    "already_present": False,
    "updated_notes": [],
    "already_current_notes": [],
    "missing_notes": [],
    "failed_notes": [],
}''',
        "release status note lists",
    )
    backend = replace_once(
        backend,
        '''    for key in ("version", "state", "last_error", "last_success_at", "already_present"):
        if key in stored:''',
        '''    for key in (
        "version", "state", "last_error", "last_success_at", "already_present",
        "updated_notes", "already_current_notes", "missing_notes", "failed_notes",
    ):
        if key in stored:''',
        "release status restoration",
    )
    backend = replace_once(
        backend,
        '''        "already_present": RELEASE_SYNC_STATUS.get("already_present", False),
    }''',
        '''        "already_present": RELEASE_SYNC_STATUS.get("already_present", False),
        "updated_notes": RELEASE_SYNC_STATUS.get("updated_notes", []),
        "already_current_notes": RELEASE_SYNC_STATUS.get("already_current_notes", []),
        "missing_notes": RELEASE_SYNC_STATUS.get("missing_notes", []),
        "failed_notes": RELEASE_SYNC_STATUS.get("failed_notes", []),
    }''',
        "release status persistence",
    )

    helpers = r'''

RELEASE_SYNC_PRIMARY_NOTES = (
    "Project Overview.md",
    "Requirements.md",
    "Deployment and Operations.md",
    "Release and Change Log.md",
    "Session Handoff.md",
)
RELEASE_SYNC_AUDIT_NOTES = (
    "Architecture.md",
    "Design Decisions.md",
    "API and Integrations.md",
    "Data and Storage.md",
    "Security and Permissions.md",
    "Test Log.md",
)
CURRENT_RELEASE_BLOCK_START = "<!-- zbrano-current-release:start -->"
CURRENT_RELEASE_BLOCK_END = "<!-- zbrano-current-release:end -->"
CURRENT_VERSION_LABELS = (
    "source and runtime version|current version|current source version|"
    "current runtime version|current release|source version|runtime version|"
    "running version|installed version|deployed version"
)


def render_current_release_truth(manifest: dict[str, Any], *, release_log: bool) -> str:
    version = str(manifest["version"])
    summary = " ".join(str(manifest.get("summary") or "ZBRANO application update").split())
    source = " ".join(str(manifest.get("source") or "ZBRANO release manifest").split())
    heading = "## Current Release" if release_log else "## Current Release Source of Truth"
    return "\n".join((
        CURRENT_RELEASE_BLOCK_START,
        heading,
        "",
        f"- **Source and runtime version:** {version}",
        "- **Runtime status:** Started successfully",
        f"- **Source:** {source}",
        f"- **Summary:** {summary}",
        CURRENT_RELEASE_BLOCK_END,
    ))


def _insert_after_title(content: str, block: str) -> str:
    title = re.search(r"(?m)^#\s+.+$", content)
    if not title:
        return block + "\n\n" + content.lstrip()
    before = content[:title.end()].rstrip()
    after = content[title.end():].lstrip("\n")
    return before + "\n\n" + block + ("\n\n" + after if after else "\n")


def upsert_current_release_truth(content: str, manifest: dict[str, Any], *, release_log: bool) -> str:
    block = render_current_release_truth(manifest, release_log=release_log)
    managed = re.compile(
        re.escape(CURRENT_RELEASE_BLOCK_START) + r".*?" + re.escape(CURRENT_RELEASE_BLOCK_END),
        re.DOTALL,
    )
    if managed.search(content):
        return managed.sub(block, content, count=1)
    if release_log:
        heading = re.search(r"(?im)^##\s+Current Release(?:\s+Source of Truth)?\s*$", content)
        if heading:
            next_heading = re.search(r"(?m)^##\s+", content[heading.end():])
            end = heading.end() + (next_heading.start() if next_heading else len(content[heading.end():]))
            before = content[:heading.start()].rstrip()
            after = content[end:].lstrip("\n")
            return before + "\n\n" + block + ("\n\n" + after if after else "\n")
    return _insert_after_title(content, block)


def reconcile_explicit_current_versions(content: str, version: str) -> str:
    version_token = r"v?\d+\.\d+\.\d+"
    bold = re.compile(
        rf"(?im)^(\s*(?:[-*]\s*)?\*\*(?:{CURRENT_VERSION_LABELS}):\*\*\s*)(v?){version_token[2:]}"
    )
    plain = re.compile(
        rf"(?im)^(\s*(?:[-*]\s*)?(?:{CURRENT_VERSION_LABELS})\s*:\s*)(v?){version_token[2:]}"
    )
    table = re.compile(
        rf"(?im)^(\s*\|\s*(?:{CURRENT_VERSION_LABELS})\s*\|\s*)(v?){version_token[2:]}"
    )

    def replace_labeled(match: re.Match[str]) -> str:
        return match.group(1) + ("v" if match.group(2) else "") + version

    updated = bold.sub(replace_labeled, content)
    updated = plain.sub(replace_labeled, updated)
    updated = table.sub(replace_labeled, updated)
    updated = re.sub(
        rf"(?i)(\bcurrent(?: source| runtime| installed| deployed)? version(?:\s+is|\s*:)\s*)(v?){version_token[2:]}",
        lambda match: match.group(1) + ("v" if match.group(2) else "") + version,
        updated,
    )
    updated = re.sub(
        rf"(?i)(v?){version_token[2:]}(\s+is\s+(?:the\s+)?current(?: source| runtime| installed| deployed)?(?:\s+version|\s+release)?)",
        lambda match: ("v" if match.group(1) else "") + version + match.group(2),
        updated,
    )

    lines = updated.splitlines(keepends=True)
    in_current_section = False
    for index, line in enumerate(lines):
        heading = re.match(r"^##\s+(.+?)\s*$", line.strip("\r\n"))
        if heading:
            normalized = heading.group(1).strip().casefold()
            in_current_section = normalized in {
                "current source truth", "current release", "current release source of truth",
                "current state", "source truth",
            }
            continue
        if not in_current_section or re.search(r"(?i)historical|previous|superseded|legacy|old version", line):
            continue
        if re.match(r"^\s*(?:[-*]\s*)?(?:\*\*)?(?:version|source version|runtime version|release version)", line, re.I):
            lines[index] = re.sub(version_token, lambda match: ("v" if match.group(0).startswith("v") else "") + version, line, count=1)
    return "".join(lines)
'''
    sync_start = backend.find("\n\nasync def synchronize_release_to_workshop_memory_once()")
    sync_end = backend.find("\n\nasync def release_sync_worker()", sync_start)
    if sync_start < 0 or sync_end < 0:
        raise RuntimeError("ZBRANO v0.12.67 could not isolate release synchronization")
    backend = backend[:sync_start] + helpers + backend[sync_start:sync_end] + backend[sync_end:]

    replacement_sync = r'''async def synchronize_release_to_workshop_memory_once() -> dict[str, Any]:
    if not release_sync_enabled():
        RELEASE_SYNC_STATUS.update({"state": "disabled", "last_error": None})
        persist_release_sync_status()
        return release_sync_status()

    manifest = load_release_manifest()
    version = str(manifest["version"])
    project = str(manifest.get("project") or "ZBRANO Workshop Assistant")
    release_note = str(manifest.get("note") or "Release and Change Log.md")
    note_names = tuple(dict.fromkeys(RELEASE_SYNC_PRIMARY_NOTES + RELEASE_SYNC_AUDIT_NOTES))
    updated_notes: list[str] = []
    already_current_notes: list[str] = []
    missing_notes: list[str] = []
    failed_notes: list[str] = []
    release_history_present = False
    RELEASE_SYNC_STATUS.update({
        "state": "synchronizing",
        "version": version,
        "target": f"{project}/canonical release truth",
        "last_error": None,
        "already_present": False,
        "updated_notes": [],
        "already_current_notes": [],
        "missing_notes": [],
        "failed_notes": [],
    })

    for note_name in note_names:
        relative_path = f"{project}/{note_name}"
        try:
            current = await call_workshop_memory_tool("read_project_note", {"relative_path": relative_path})
            content = str(current.get("content") or "")
        except (MCPError, httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
            if note_name not in RELEASE_SYNC_PRIMARY_NOTES and "not found" in str(exc).casefold():
                missing_notes.append(note_name)
                continue
            failed_notes.append(f"{note_name}: read failed: {str(exc)[:240]}")
            continue

        updated = reconcile_explicit_current_versions(content, version)
        if note_name == release_note:
            release_history_present = release_marker(version) in content
            updated = upsert_current_release_truth(updated, manifest, release_log=True)
            updated = insert_release_history(updated, render_release_entry(manifest))
        elif note_name in RELEASE_SYNC_PRIMARY_NOTES:
            updated = upsert_current_release_truth(updated, manifest, release_log=False)

        if updated == content:
            already_current_notes.append(note_name)
            continue
        try:
            result = await call_workshop_memory_tool(
                "write_project_note",
                {
                    "relative_path": relative_path,
                    "content": updated,
                    "mode": "replace",
                    "create_folders": False,
                },
            )
            status = str(result.get("status") or "")
            if status not in {"replaced", "updated", "ok"}:
                raise RuntimeError(f"unexpected write status: {status or 'missing'}")
            updated_notes.append(note_name)
        except (MCPError, httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
            failed_notes.append(f"{note_name}: write failed: {str(exc)[:240]}")

    RELEASE_SYNC_STATUS.update({
        "updated_notes": updated_notes,
        "already_current_notes": already_current_notes,
        "missing_notes": missing_notes,
        "failed_notes": failed_notes,
        "already_present": release_history_present,
    })
    if failed_notes:
        raise RuntimeError("Canonical release reconciliation failed: " + " | ".join(failed_notes))
    RELEASE_SYNC_STATUS.update({
        "state": "synchronized",
        "last_success_at": time.time(),
        "last_error": None,
    })
    persist_release_sync_status()
    return release_sync_status()
'''
    start = backend.find("async def synchronize_release_to_workshop_memory_once()")
    end = backend.find("\n\nasync def release_sync_worker()", start)
    if start < 0 or end < 0:
        raise RuntimeError("ZBRANO v0.12.67 lost release synchronization boundary")
    backend = backend[:start] + replacement_sync + backend[end:]

    frontend = replace_once(
        frontend,
        "Enabling this grants standing authorization only for ZBRANO's own Release and Change Log.md. Existing content is preserved and Workshop Memory creates a backup before replacement.",
        "Enabling this grants standing authorization only for ZBRANO's canonical current-release fields and Release History. Historical entries are preserved, replacements are limited to the ZBRANO project, and Workshop Memory creates backups.",
        "release sync authority description",
    )

    backend = backend.replace('version="0.12.66"', 'version="0.12.67"')
    backend = backend.replace('"version": "0.12.66"', '"version": "0.12.67"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.66"', '"X-ZBRANO-Frontend-Version": "0.12.67"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.66"', '"name": "ZBRANO Developer Mode", "version": "0.12.67"')
    frontend = frontend.replace("HUD 0.12.66", "HUD 0.12.67")

    required_backend = (
        "RELEASE_SYNC_PRIMARY_NOTES", "CURRENT_RELEASE_BLOCK_START",
        "def reconcile_explicit_current_versions(", "canonical release truth",
        '"updated_notes": updated_notes', 'version="0.12.67"',
    )
    missing = [marker for marker in required_backend if marker not in backend]
    if missing or "HUD 0.12.67" not in frontend:
        raise RuntimeError("ZBRANO v0.12.67 verification failed: " + ", ".join(missing))
    if 'if marker in content:' in backend:
        raise RuntimeError("ZBRANO v0.12.67 retained the stale release-marker early exit")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
