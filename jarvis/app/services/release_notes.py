from __future__ import annotations

import re
import time
from typing import Any

def release_marker(version: str) -> str:
    return f"<!-- zbrano-release:{version} -->"

def render_release_entry(manifest: dict[str, Any]) -> str:
    version = str(manifest["version"])
    installed_at = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    details = manifest.get("release_entry")
    if not isinstance(details, dict):
        details = manifest
    lines = [
        release_marker(version),
        f"### v{version} — Installed {installed_at}",
        "",
        f"- **Runtime status:** Started successfully as v{version}",
        f"- **Source:** {str(manifest.get('source') or 'ZBRANO release manifest')}",
        f"- **Summary:** {str(manifest.get('summary') or 'ZBRANO application update')}",
    ]
    for heading, key in (("New features", "features"), ("Fixes and reliability", "fixes"), ("Validation", "validation")):
        values = [str(item).strip() for item in details.get(key, []) if str(item).strip()]
        if values:
            lines.extend(("", f"#### {heading}"))
            lines.extend(f"- {item}" for item in values)
    return "\n".join(lines).rstrip()

def render_release_history_backfill(manifest: dict[str, Any]) -> list[str]:
    source = str(manifest.get("source") or "ZBRANO release manifest")
    current_version = str(manifest.get("version") or "")
    records: dict[str, str] = {}
    for item in manifest.get("history_backfill", []):
        if not isinstance(item, dict):
            continue
        version = str(item.get("version") or "").strip()
        summary = " ".join(str(item.get("summary") or "").split())
        if not re.fullmatch(r"\d+\.\d+\.\d+", version) or version == current_version or not summary:
            continue
        records[version] = summary

    def version_key(version: str) -> tuple[int, int, int]:
        return tuple(int(part) for part in version.split("."))

    entries: list[str] = []
    for version in sorted(records, key=version_key):
        entries.append("\n".join((
            release_marker(version),
            f"### v{version} — Canonical release record",
            "",
            f"- **Source:** {source}",
            f"- **Summary:** {records[version]}",
        )))
    return entries

def upsert_marked_release_history_entry(content: str, entry: str) -> str:
    version_match = re.search(r"<!-- zbrano-release:([^>]+) -->", entry)
    if not version_match:
        return content
    marker = release_marker(version_match.group(1).strip())
    marker_match = re.search(rf"(?m)^{re.escape(marker)}[ \t]*\r?$", content)
    if not marker_match:
        return insert_release_history(content, entry)

    scan_start = marker_match.end()
    own_heading = re.match(r"(?:\r?\n)+###\s+[^\r\n]+(?:\r?\n)?", content[scan_start:])
    if own_heading:
        scan_start += own_heading.end()
    boundary = re.search(
        r"(?m)^(?:<!-- zbrano-release:[^>]+ -->|###\s+v?\d+\.\d+\.\d+\b|##\s+)",
        content[scan_start:],
    )
    end = scan_start + boundary.start() if boundary else len(content)
    suffix = content[end:].lstrip("\r\n")
    return content[:marker_match.start()] + entry.rstrip() + "\n\n" + suffix

def reconcile_release_history_backfill(content: str, manifest: dict[str, Any]) -> str:
    updated = content
    for entry in render_release_history_backfill(manifest):
        updated = upsert_marked_release_history_entry(updated, entry)
    return updated

def insert_release_history(content: str, entry: str) -> str:
    version_match = re.search(r"<!-- zbrano-release:([^>]+) -->", entry)
    if version_match and release_marker(version_match.group(1).strip()) in content:
        return content
    heading = re.search(r"(?m)^## Release History\s*$", content)
    if heading:
        before = content[:heading.end()].rstrip()
        after = content[heading.end():].strip("\n")
        return before + "\n\n" + entry + ("\n\n" + after if after else "") + "\n"
    title = content.rstrip()
    return title + ("\n\n" if title else "") + "## Release History\n\n" + entry + "\n"

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

def release_sync_write_status(result: Any) -> str:
    """Read a write status from plain or MCP structured-result envelopes."""
    if not isinstance(result, dict):
        return ""
    candidates = (result, result.get("structuredContent"), result.get("result"))
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("status"):
            return str(candidate["status"]).strip().casefold()
    return ""

def release_sync_content_matches(actual: Any, expected: Any) -> bool:
    """Compare note content while tolerating the writer's final newline policy."""
    normalize = lambda value: str(value or "").replace("\r\n", "\n").rstrip("\n")
    return normalize(actual) == normalize(expected)
