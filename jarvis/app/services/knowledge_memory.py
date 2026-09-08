from __future__ import annotations

import contextlib
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any


KNOWLEDGE_ROOT = Path("/data/knowledge-memory")
SPACES_FOLDER = "Spaces"
LEGACY_PROJECTS_FOLDER = "Projects"
TEMPLATES_FOLDER = "Templates"
CATEGORIES_FILE = "categories.json"

DEFAULT_CATEGORIES = [
    {"name": "Personal", "icon": "person", "description": "Things that matter to you."},
    {"name": "Home", "icon": "home", "description": "Household knowledge, routines, and reference."},
    {"name": "Work", "icon": "work", "description": "Work, clients, and professional reference."},
    {"name": "Learning", "icon": "study", "description": "Study, research, and ideas."},
]

BUILTIN_TEMPLATES = {
    "blank": {"name": "Blank", "description": "Start with an empty space.", "icon": "blank", "category": "Personal"},
    "home": {"name": "Home", "description": "Household information, routines, and important details.", "icon": "home", "category": "Home"},
    "work": {"name": "Work", "description": "Decisions and next actions for everyday work.", "icon": "work", "category": "Work"},
    "project": {"name": "Project", "description": "Overview, decisions, progress, and next actions.", "icon": "project", "category": "Work"},
    "study": {"name": "Study", "description": "Learning notes, questions, and an overview.", "icon": "study", "category": "Learning"},
    "recipes": {"name": "Recipes", "description": "Favorite recipes and cooking reference.", "icon": "recipes", "category": "Personal"},
}


def configure_knowledge_memory(*, root: Path) -> None:
    global KNOWLEDGE_ROOT
    KNOWLEDGE_ROOT = Path(root).resolve()


def _initialize() -> None:
    KNOWLEDGE_ROOT.mkdir(parents=True, exist_ok=True)
    (KNOWLEDGE_ROOT / SPACES_FOLDER).mkdir(exist_ok=True)
    (KNOWLEDGE_ROOT / LEGACY_PROJECTS_FOLDER).mkdir(exist_ok=True)
    (KNOWLEDGE_ROOT / TEMPLATES_FOLDER).mkdir(exist_ok=True)


def _safe_component(value: str, label: str) -> str:
    cleaned = " ".join(str(value or "").strip().split())
    if not cleaned or len(cleaned) > 100 or cleaned in {".", ".."}:
        raise ValueError(f"Invalid {label}")
    if any(character in cleaned for character in '<>:"/\\|?*'):
        raise ValueError(f"Invalid {label}")
    return cleaned


def _safe_relative_path(relative_path: str) -> Path:
    normalized = str(relative_path or "").strip().replace("\\", "/").lstrip("/")
    if not normalized or len(normalized) > 500:
        raise ValueError("A relative Markdown note path is required")
    pieces = normalized.split("/")
    if any(not piece or piece in {".", ".."} for piece in pieces):
        raise ValueError("The note path must stay inside Knowledge Memory")
    candidate = (KNOWLEDGE_ROOT / normalized).resolve()
    if KNOWLEDGE_ROOT != candidate and KNOWLEDGE_ROOT not in candidate.parents:
        raise ValueError("The note path must stay inside Knowledge Memory")
    if candidate.suffix.lower() != ".md":
        raise ValueError("Knowledge Memory notes must use the .md extension")
    return candidate


def _space_path(space: str) -> Path:
    return KNOWLEDGE_ROOT / SPACES_FOLDER / _safe_component(space, "space name")


def _space_metadata(path: Path) -> dict[str, Any]:
    metadata_path = path / ".space.json"
    if metadata_path.is_file():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except (OSError, json.JSONDecodeError):
            pass
    return {"name": path.name, "purpose": "", "template": "blank", "category": "Personal"}


def _categories_path() -> Path:
    return KNOWLEDGE_ROOT / CATEGORIES_FILE


def _custom_categories() -> list[dict[str, str]]:
    path = _categories_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in payload if isinstance(item, dict) and item.get("name")] if isinstance(payload, list) else []


def list_memory_categories() -> dict[str, Any]:
    _initialize()
    categories = [dict(item, built_in=True) for item in DEFAULT_CATEGORIES]
    existing = {item["name"].casefold() for item in categories}
    categories.extend(dict(item, built_in=False) for item in _custom_categories() if str(item.get("name", "")).casefold() not in existing)
    return {"categories": categories, "count": len(categories)}


def create_memory_category(name: str, icon: str, description: str) -> dict[str, Any]:
    _initialize()
    clean_name = _safe_component(name, "category name")
    if any(item["name"].casefold() == clean_name.casefold() for item in list_memory_categories()["categories"]):
        raise ValueError(f"Memory category already exists: {clean_name}")
    item = {
        "name": clean_name,
        "icon": _safe_component(icon or "custom", "category icon")[:30],
        "description": str(description or "").strip()[:300],
    }
    custom = _custom_categories()
    custom.append(item)
    _categories_path().write_text(json.dumps(custom, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"created": True, "category": dict(item, built_in=False)}


def _template_path(name: str) -> Path:
    return KNOWLEDGE_ROOT / TEMPLATES_FOLDER / _safe_component(name, "template name") / ".template.json"


def _validate_template_notes(notes: Any) -> list[dict[str, str]]:
    if not isinstance(notes, list) or len(notes) > 30:
        raise ValueError("A template can contain up to 30 note cards")
    validated: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in notes:
        if not isinstance(item, dict):
            raise ValueError("Each template note must be a note card")
        name = str(item.get("name") or "").strip().replace("\\", "/")
        if not name.lower().endswith(".md"):
            name += ".md"
        relative = _safe_relative_path(f"{SPACES_FOLDER}/Template preview/{name}")
        normalized = str(relative.relative_to(KNOWLEDGE_ROOT / SPACES_FOLDER / "Template preview")).replace("\\", "/")
        if normalized.casefold() in seen:
            raise ValueError(f"Duplicate template note: {normalized}")
        seen.add(normalized.casefold())
        content = str(item.get("content") or "")
        if len(content.encode("utf-8")) > 200_000:
            raise ValueError(f"Template note is too large: {normalized}")
        validated.append({"name": normalized, "purpose": str(item.get("purpose") or "").strip()[:300], "content": content})
    return validated


def _custom_templates() -> list[dict[str, Any]]:
    _initialize()
    templates: list[dict[str, Any]] = []
    for path in (KNOWLEDGE_ROOT / TEMPLATES_FOLDER).glob("*/.template.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(item, dict) and item.get("name"):
            templates.append(item)
    return sorted(templates, key=lambda item: str(item.get("name", "")).casefold())


def list_memory_templates() -> dict[str, Any]:
    built_in = []
    for key, metadata in BUILTIN_TEMPLATES.items():
        notes = [{"name": name, "purpose": "", "content": content} for name, content in _template_notes(key, metadata["name"], "").items()]
        built_in.append({"id": key, **metadata, "notes": notes, "built_in": True})
    custom = [dict(item, id=f"custom:{item['name']}", built_in=False) for item in _custom_templates()]
    return {"templates": built_in + custom, "count": len(built_in) + len(custom)}


def save_memory_template(name: str, description: str, category: str, icon: str, notes: Any, original_name: str = "") -> dict[str, Any]:
    _initialize()
    clean_name = _safe_component(name, "template name")
    if clean_name.casefold() in BUILTIN_TEMPLATES:
        raise ValueError("Built-in templates cannot be replaced")
    validated_notes = _validate_template_notes(notes)
    old_name = _safe_component(original_name, "template name") if original_name else ""
    old_path = _template_path(old_name) if old_name else None
    target = _template_path(clean_name)
    if target.exists() and (not old_path or target != old_path):
        raise ValueError(f"Memory template already exists: {clean_name}")
    payload = {
        "name": clean_name,
        "description": str(description or "").strip()[:500],
        "category": _safe_component(category or "Personal", "category name"),
        "icon": _safe_component(icon or "template", "template icon")[:30],
        "notes": validated_notes,
        "updated_at": time.time(),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if old_path and old_path != target and old_path.is_file():
        old_path.unlink()
        with contextlib.suppress(OSError):
            old_path.parent.rmdir()
    return {"saved": True, "template": dict(payload, id=f"custom:{clean_name}", built_in=False)}


def delete_memory_template(name: str) -> dict[str, Any]:
    path = _template_path(name.removeprefix("custom:"))
    if not path.is_file():
        raise ValueError(f"Custom memory template not found: {name}")
    path.unlink()
    with contextlib.suppress(OSError):
        path.parent.rmdir()
    return {"deleted": True, "template": name}


def knowledge_memory_tool_catalog() -> dict[str, dict[str, Any]]:
    object_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    return {
        "list_memory_spaces": {
            "name": "list_memory_spaces", "permission": "read_only",
            "description": "List the user's customizable Knowledge Memory spaces, such as Home, Work, Study, Recipes, or Projects.",
            "parameters": object_schema,
        },
        "list_memory_templates": {
            "name": "list_memory_templates", "permission": "read_only",
            "description": "List built-in and user-created reusable Knowledge Memory templates.",
            "parameters": object_schema,
        },
        "create_memory_category": {
            "name": "create_memory_category", "permission": "write",
            "description": "Create a user-defined category for related Knowledge Memory spaces and templates after approval.",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"}, "icon": {"type": "string"}, "description": {"type": "string"},
            }, "required": ["name", "icon", "description"], "additionalProperties": False},
        },
        "create_memory_template": {
            "name": "create_memory_template", "permission": "write",
            "description": "Create a reusable Knowledge Memory template with named Markdown note cards after approval.",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"}, "description": {"type": "string"}, "category": {"type": "string"},
                "notes": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "purpose": {"type": "string"}, "content": {"type": "string"},
                }, "required": ["name", "purpose", "content"], "additionalProperties": False}},
            }, "required": ["name", "description", "category", "notes"], "additionalProperties": False},
        },
        "create_memory_space": {
            "name": "create_memory_space", "permission": "write",
            "description": "Create a customizable Knowledge Memory space only after the user asks to create it.",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"}, "purpose": {"type": "string"},
                "template": {"type": "string", "description": "A built-in template ID or exact user-created template name."},
                "category": {"type": "string"},
            }, "required": ["name", "purpose", "template", "category"], "additionalProperties": False},
        },
        "list_memory_notes": {
            "name": "list_memory_notes", "permission": "read_only",
            "description": "List Markdown notes saved in one Knowledge Memory space.",
            "parameters": {"type": "object", "properties": {"space": {"type": "string"}}, "required": ["space"], "additionalProperties": False},
        },
        "read_memory_note": {
            "name": "read_memory_note", "permission": "read_only",
            "description": "Read one note from a Knowledge Memory space.",
            "parameters": {"type": "object", "properties": {"space": {"type": "string"}, "note": {"type": "string"}}, "required": ["space", "note"], "additionalProperties": False},
        },
        "write_memory_note": {
            "name": "write_memory_note", "permission": "write",
            "description": "Create, append, or replace a note in a Knowledge Memory space after explicit approval.",
            "parameters": {"type": "object", "properties": {
                "space": {"type": "string"}, "note": {"type": "string"}, "content": {"type": "string"},
                "mode": {"type": "string", "enum": ["create", "append", "replace"]},
            }, "required": ["space", "note", "content", "mode"], "additionalProperties": False},
        },
        "search_knowledge_memory": {
            "name": "search_knowledge_memory", "permission": "read_only",
            "description": "Search all user-created Knowledge Memory spaces and return matching note excerpts.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, "required": ["query", "limit"], "additionalProperties": False},
        },
    }


def _template_notes(template: str, name: str, purpose: str) -> dict[str, str]:
    heading = f"# {name}\n\n{purpose.strip()}\n" if purpose.strip() else f"# {name}\n"
    templates = {
        "blank": {}, "custom": {},
        "home": {"Overview.md": heading, "Routines.md": f"# {name} routines\n", "Important information.md": "# Important information\n"},
        "work": {"Overview.md": heading, "Decisions.md": "# Decisions\n", "Next actions.md": "# Next actions\n"},
        "project": {"Overview.md": heading, "Decisions.md": "# Decisions\n", "Progress.md": "# Progress\n", "Next actions.md": "# Next actions\n"},
        "study": {"Overview.md": heading, "Notes.md": "# Notes\n", "Questions.md": "# Questions\n"},
        "recipes": {"Overview.md": heading, "Favorites.md": "# Favorites\n"},
    }
    return templates.get(template, {})


def create_memory_space(name: str, purpose: str, template: str, category: str = "") -> dict[str, Any]:
    _initialize()
    clean_name = _safe_component(name, "space name")
    requested = str(template or "blank").strip()
    selected = requested.casefold()
    custom_template = None
    if selected.startswith("custom:"):
        selected = selected.split(":", 1)[1]
    if selected not in BUILTIN_TEMPLATES:
        custom_template = next((item for item in _custom_templates() if str(item.get("name", "")).casefold() == selected), None)
        if custom_template is None:
            raise ValueError("Unknown Knowledge Memory template")
    path = _space_path(clean_name)
    if path.exists():
        raise ValueError(f"Knowledge Memory space already exists: {clean_name}")
    path.mkdir(parents=True)
    selected_name = selected if custom_template is None else str(custom_template["name"])
    selected_category = str(category or (custom_template or BUILTIN_TEMPLATES[selected]).get("category") or "Personal")
    metadata = {"name": clean_name, "purpose": str(purpose or "").strip()[:1000], "template": selected_name, "category": _safe_component(selected_category, "category name"), "created_at": time.time()}
    (path / ".space.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    template_notes = _template_notes(selected, clean_name, metadata["purpose"]) if custom_template is None else {item["name"]: item.get("content", "") for item in custom_template.get("notes", [])}
    for filename, content in template_notes.items():
        note_path = _space_note_path(clean_name, filename)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(content, encoding="utf-8")
    return {"created": True, "space": metadata, "notes_created": sorted(template_notes)}


def list_memory_spaces() -> dict[str, Any]:
    _initialize()
    spaces = []
    for path in sorted((KNOWLEDGE_ROOT / SPACES_FOLDER).iterdir(), key=lambda item: item.name.casefold()):
        if path.is_dir():
            spaces.append({**_space_metadata(path), "note_count": sum(1 for note in path.rglob("*.md") if note.is_file())})
    return {"spaces": spaces, "count": len(spaces), "storage": "local"}


def list_memory_notes(space: str) -> dict[str, Any]:
    path = _space_path(space)
    if not path.is_dir():
        raise ValueError(f"Knowledge Memory space not found: {space}")
    notes = [str(note.relative_to(path)).replace("\\", "/") for note in path.rglob("*.md") if note.is_file()]
    return {"space": path.name, "notes": sorted(notes, key=str.casefold), "count": len(notes)}


def _space_note_path(space: str, note: str) -> Path:
    clean_space = _safe_component(space, "space name")
    clean_note = str(note or "").strip().replace("\\", "/")
    if not clean_note.lower().endswith(".md"):
        clean_note += ".md"
    return _safe_relative_path(f"{SPACES_FOLDER}/{clean_space}/{clean_note}")


def _legacy_note_path(relative_path: str) -> Path:
    relative = str(relative_path or "").strip().replace("\\", "/").lstrip("/")
    if relative.startswith(f"{LEGACY_PROJECTS_FOLDER}/"):
        return _safe_relative_path(relative)
    return _safe_relative_path(f"{LEGACY_PROJECTS_FOLDER}/{relative}")


def read_memory_note(space: str, note: str) -> dict[str, Any]:
    path = _space_note_path(space, note)
    if not path.is_file():
        raise ValueError(f"Knowledge Memory note not found: {space}/{note}")
    return {"space": _safe_component(space, "space name"), "note": str(path.relative_to(_space_path(space))).replace("\\", "/"), "content": path.read_text(encoding="utf-8")}


def _write_path(path: Path, content: str, mode: str, create_folders: bool = True) -> dict[str, Any]:
    text = str(content or "")
    if len(text.encode("utf-8")) > 1_000_000:
        raise ValueError("Knowledge Memory note is too large")
    selected = str(mode or "create").strip().lower()
    if selected not in {"create", "append", "replace"}:
        raise ValueError("Mode must be create, append, or replace")
    if selected == "create" and path.exists():
        raise ValueError(f"Knowledge Memory note already exists: {path.name}")
    if selected in {"append", "replace"} and not path.exists():
        raise ValueError(f"Knowledge Memory note not found: {path.name}")
    if create_folders:
        path.parent.mkdir(parents=True, exist_ok=True)
    elif not path.parent.is_dir():
        raise ValueError("Knowledge Memory note folder does not exist")
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    saved = previous + text if selected == "append" else text
    path.write_text(saved, encoding="utf-8")
    return {"saved": True, "relative_path": str(path.relative_to(KNOWLEDGE_ROOT)).replace("\\", "/"), "mode": selected, "bytes": len(saved.encode("utf-8"))}


def write_memory_note(space: str, note: str, content: str, mode: str) -> dict[str, Any]:
    path = _space_note_path(space, note)
    if not _space_path(space).is_dir():
        raise ValueError(f"Knowledge Memory space not found: {space}")
    return _write_path(path, content, mode)


def delete_memory_note(space: str, note: str) -> dict[str, Any]:
    path = _space_note_path(space, note)
    if not path.is_file():
        raise ValueError(f"Knowledge Memory note not found: {space}/{note}")
    path.unlink()
    parent = path.parent
    space_root = _space_path(space)
    while parent != space_root and space_root in parent.parents:
        with contextlib.suppress(OSError):
            parent.rmdir()
        parent = parent.parent
    return {"deleted": True, "space": space_root.name, "note": note}


def delete_memory_space(space: str) -> dict[str, Any]:
    path = _space_path(space)
    if not path.is_dir():
        raise ValueError(f"Knowledge Memory space not found: {space}")
    shutil.rmtree(path)
    return {"deleted": True, "space": path.name}


def search_knowledge_memory(query: str, limit: int) -> dict[str, Any]:
    needle = " ".join(str(query or "").casefold().split())
    if not needle:
        raise ValueError("A search query is required")
    maximum = max(1, min(50, int(limit)))
    results: list[dict[str, Any]] = []
    for path in KNOWLEDGE_ROOT.rglob("*.md"):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        index = content.casefold().find(needle)
        if index < 0 and needle not in path.name.casefold():
            continue
        start = max(0, index - 180) if index >= 0 else 0
        results.append({"relative_path": str(path.relative_to(KNOWLEDGE_ROOT)).replace("\\", "/"), "excerpt": content[start:start + 500]})
        if len(results) >= maximum:
            break
    return {"query": query, "results": results, "count": len(results)}


def export_knowledge_memory() -> dict[str, Any]:
    _initialize()
    files: list[dict[str, str]] = []
    total_bytes = 0
    for path in sorted(KNOWLEDGE_ROOT.rglob("*")):
        if not path.is_file() or (
            path.suffix.lower() != ".md"
            and path.name not in {".space.json", ".template.json", CATEGORIES_FILE}
        ):
            continue
        content = path.read_text(encoding="utf-8", errors="strict")
        total_bytes += len(content.encode("utf-8"))
        if len(files) >= 2000 or total_bytes > 20_000_000:
            raise ValueError("Knowledge Memory is too large for a settings backup")
        files.append({"path": str(path.relative_to(KNOWLEDGE_ROOT)).replace("\\", "/"), "content": content})
    return {"version": 1, "files": files}


def restore_knowledge_memory(payload: dict[str, Any]) -> dict[str, Any]:
    files = payload.get("files")
    if payload.get("version") != 1 or not isinstance(files, list) or len(files) > 2000:
        raise ValueError("Knowledge Memory backup is malformed")
    restored = 0
    total_bytes = 0
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Knowledge Memory backup is malformed")
        relative = str(item.get("path") or "")
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError("Knowledge Memory backup is malformed")
        total_bytes += len(content.encode("utf-8"))
        if total_bytes > 20_000_000:
            raise ValueError("Knowledge Memory backup is too large")
        parts = relative.replace("\\", "/").split("/")
        if len(parts) == 3 and parts[0] == SPACES_FOLDER and parts[-1] == ".space.json":
            space = _safe_component(parts[1], "space name")
            path = _space_path(space) / ".space.json"
        elif len(parts) == 3 and parts[0] == TEMPLATES_FOLDER and parts[-1] == ".template.json":
            template = _safe_component(parts[1], "template name")
            path = _template_path(template)
        elif parts == [CATEGORIES_FILE]:
            path = _categories_path()
        else:
            path = _safe_relative_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        restored += 1
    return {"restored": restored}


def _legacy_projects() -> list[Path]:
    roots = [KNOWLEDGE_ROOT / LEGACY_PROJECTS_FOLDER, KNOWLEDGE_ROOT / SPACES_FOLDER]
    return [item for root in roots if root.is_dir() for item in root.iterdir() if item.is_dir()]


def _legacy_project_path(project: str) -> Path:
    name = _safe_component(project, "project or space name")
    for root in (KNOWLEDGE_ROOT / LEGACY_PROJECTS_FOLDER, KNOWLEDGE_ROOT / SPACES_FOLDER):
        candidate = root / name
        if candidate.is_dir():
            return candidate
    raise ValueError(f"Knowledge Memory space not found: {name}")


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def call_local_knowledge_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    _initialize()
    if tool_name == "check_server_status":
        return {"status": "ok", "storage": "built_in", "root": str(KNOWLEDGE_ROOT), "spaces": list_memory_spaces()["count"]}
    if tool_name == "list_memory_spaces":
        return list_memory_spaces()
    if tool_name == "list_memory_templates":
        return list_memory_templates()
    if tool_name == "create_memory_category":
        return create_memory_category(arguments["name"], arguments.get("icon", "custom"), arguments.get("description", ""))
    if tool_name == "create_memory_template":
        return save_memory_template(arguments["name"], arguments.get("description", ""), arguments.get("category", "Personal"), "template", arguments.get("notes", []))
    if tool_name == "create_memory_space":
        return create_memory_space(arguments["name"], arguments.get("purpose", ""), arguments.get("template", "blank"), arguments.get("category", ""))
    if tool_name == "list_memory_notes":
        return list_memory_notes(arguments["space"])
    if tool_name == "read_memory_note":
        return read_memory_note(arguments["space"], arguments["note"])
    if tool_name == "write_memory_note":
        return write_memory_note(arguments["space"], arguments["note"], arguments.get("content", ""), arguments.get("mode", "create"))
    if tool_name == "search_knowledge_memory":
        return search_knowledge_memory(arguments["query"], arguments.get("limit", 20))
    if tool_name == "list_projects":
        names = sorted({path.name for path in _legacy_projects()}, key=str.casefold)
        return {"projects": names, "count": len(names), "storage": "built_in"}
    if tool_name == "get_profile_summary":
        return {"content": _read_optional(KNOWLEDGE_ROOT / "Profile" / "Profile Summary.md"), "storage": "built_in"}
    if tool_name == "read_project_note":
        path = _legacy_note_path(arguments["relative_path"])
        if not path.is_file():
            raise ValueError(f"Knowledge Memory note not found: {arguments['relative_path']}")
        return {"relative_path": str(path.relative_to(KNOWLEDGE_ROOT)).replace("\\", "/"), "content": path.read_text(encoding="utf-8")}
    if tool_name == "write_project_note":
        path = _legacy_note_path(arguments["relative_path"])
        return _write_path(path, arguments.get("content", ""), arguments.get("mode", "create"), bool(arguments.get("create_folders", False)))
    if tool_name in {"get_project_context", "get_latest_handoff", "get_open_decisions"}:
        project_path = _legacy_project_path(arguments["project"])
        notes = {path.name: path.read_text(encoding="utf-8") for path in project_path.glob("*.md")}
        if tool_name == "get_latest_handoff":
            handoff = notes.get("Session Handoff.md") or notes.get("Progress.md") or ""
            return {"project": project_path.name, "content": handoff}
        if tool_name == "get_open_decisions":
            content = notes.get("Design Decisions.md") or notes.get("Decisions.md") or ""
            open_lines = [line.strip() for line in content.splitlines() if re.search(r"\b(open|proposed|pending)\b", line, re.I)]
            return {"project": project_path.name, "decisions": open_lines[:100]}
        return {"project": project_path.name, "overview": notes.get("Project Overview.md") or notes.get("Overview.md") or "", "handoff": notes.get("Session Handoff.md") or notes.get("Progress.md") or "", "decisions": notes.get("Design Decisions.md") or notes.get("Decisions.md") or "", "requirements": notes.get("Requirements.md", "") if arguments.get("include_requirements", True) else ""}
    raise ValueError(f"Unknown built-in Knowledge Memory tool: {tool_name}")
