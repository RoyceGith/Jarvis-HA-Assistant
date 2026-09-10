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
    {"name": "People", "icon": "people", "description": "Useful details about family, friends, and other people."},
    {"name": "Health", "icon": "health", "description": "Health information, appointments, and medication."},
    {"name": "Work", "icon": "work", "description": "Work, clients, and professional reference."},
    {"name": "Travel", "icon": "travel", "description": "Trips, bookings, places, and travel plans."},
    {"name": "Learning", "icon": "study", "description": "Study, research, and ideas."},
    {"name": "Food", "icon": "recipes", "description": "Recipes, meals, restaurants, and food preferences."},
    {"name": "Hobbies", "icon": "hobbies", "description": "Interests, collections, equipment, and activities."},
    {"name": "General", "icon": "personal", "description": "Everything that does not need a special area."},
]

BUILTIN_TEMPLATES = {
    "blank": {"name": "Empty space", "description": "Start without any ready-made notes.", "icon": "blank", "category": "All"},
    "home": {"name": "Household organizer", "description": "Overview, routines, and important household information.", "icon": "home", "category": "Home"},
    "work": {"name": "Work notebook", "description": "Overview, decisions, and next actions for everyday work.", "icon": "work", "category": "Work"},
    "project": {"name": "Project tracker", "description": "Overview, decisions, progress, and next actions for a project.", "icon": "project", "category": "Work"},
    "study": {"name": "Study notebook", "description": "An overview, learning notes, and open questions.", "icon": "study", "category": "Learning"},
    "recipes": {"name": "Recipe collection", "description": "An overview and a place for favorite recipes.", "icon": "recipes", "category": "Personal"},
}

AUTO_MEMORY_AREAS = {
    "home": {
        "area": "Home", "space": "Home", "category": "Home", "icon": "home",
        "purpose": "Household information automatically organized by ZBRANO.",
        "keywords": ("home", "house", "household", "room", "apartment", "appliance", "air conditioner", "boiler", "filter", "maintenance", "repair", "electricity", "water", "wifi", "garage", "garden", "casa", "stanza", "condizionatore", "maison", "pièce", "climatiseur", "filtre"),
    },
    "people": {
        "area": "People", "space": "People", "category": "People", "icon": "people",
        "purpose": "Useful details about family, friends, and other people.",
        "keywords": ("birthday", "family", "friend", "wife", "husband", "partner", "mother", "father", "sister", "brother", "daughter", "son", "contact", "phone number", "email address", "likes", "prefers", "compleanno", "famiglia", "amico", "anniversaire", "famille", "ami"),
    },
    "health": {
        "area": "Health", "space": "Health", "category": "Health", "icon": "health",
        "purpose": "Health information automatically organized by ZBRANO.",
        "keywords": ("health", "doctor", "medical", "medicine", "medication", "tablet", "dose", "allergy", "allergic", "symptom", "hospital", "clinic", "prescription", "blood pressure", "salute", "medico", "farmaco", "allergia", "santé", "médecin", "médicament", "allergie"),
    },
    "work": {
        "area": "Work & projects", "space": "Work & Projects", "category": "Work", "icon": "work",
        "purpose": "Work and project information automatically organized by ZBRANO.",
        "keywords": ("work", "project", "client", "customer", "meeting", "deadline", "decision", "invoice", "proposal", "task", "office", "business", "lavoro", "progetto", "riunione", "scadenza", "travail", "projet", "réunion", "échéance", "décision"),
    },
    "travel": {
        "area": "Travel", "space": "Travel", "category": "Travel", "icon": "travel",
        "purpose": "Trips and travel information automatically organized by ZBRANO.",
        "keywords": ("travel", "trip", "flight", "hotel", "booking", "reservation", "passport", "itinerary", "holiday", "vacation", "airport", "train", "viaggio", "volo", "prenotazione", "passaporto", "voyage", "vol", "hôtel", "réservation", "passeport"),
    },
    "learning": {
        "area": "Learning", "space": "Learning", "category": "Learning", "icon": "study",
        "purpose": "Learning and reference material automatically organized by ZBRANO.",
        "keywords": ("learn", "study", "course", "research", "lesson", "exam", "article", "reference", "tutorial", "training", "studio", "corso", "ricerca", "lezione", "étude", "cours", "recherche", "leçon"),
    },
    "food": {
        "area": "Food & recipes", "space": "Food & Recipes", "category": "Food", "icon": "recipes",
        "purpose": "Food information automatically organized by ZBRANO.",
        "keywords": ("recipe", "ingredient", "meal", "cook", "restaurant", "food", "grocery", "bake", "breakfast", "lunch", "dinner", "soup", "stew", "pasta", "bread", "cake", "dessert", "salad", "ricetta", "ingrediente", "cucinare", "recette", "repas", "cuisiner"),
    },
    "hobbies": {
        "area": "Hobbies", "space": "Hobbies", "category": "Hobbies", "icon": "hobbies",
        "purpose": "Interests and collections automatically organized by ZBRANO.",
        "keywords": ("hobby", "collection", "music", "gaming", "photography", "bicycle", "cycling", "painting", "craft", "fishing", "sport", "musica", "fotografia", "collezione", "musique", "photographie", "vélo"),
    },
    "general": {
        "area": "General", "space": "General", "category": "General", "icon": "personal",
        "purpose": "Useful information automatically organized by ZBRANO.",
        "keywords": (),
    },
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
    custom = _custom_categories()
    overrides = {
        str(item.get("built_in_name") or "").casefold(): item
        for item in custom
        if item.get("built_in_name")
    }
    categories = []
    for default in DEFAULT_CATEGORIES:
        override = overrides.get(default["name"].casefold())
        categories.append(dict(override or default, built_in=True, built_in_name=default["name"]))
    existing = {item["name"].casefold() for item in categories}
    categories.extend(
        dict(item, built_in=False)
        for item in custom
        if not item.get("built_in_name") and str(item.get("name", "")).casefold() not in existing
    )
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


def update_memory_category(original_name: str, name: str, icon: str, description: str) -> dict[str, Any]:
    """Edit a category label and keep all assigned memory spaces connected to it."""
    _initialize()
    original = _safe_component(original_name, "original category name")
    clean_name = _safe_component(name, "category name")
    categories = list_memory_categories()["categories"]
    current = next((item for item in categories if item["name"].casefold() == original.casefold()), None)
    if not current:
        raise ValueError(f"Memory category not found: {original}")
    if any(item["name"].casefold() == clean_name.casefold() and item is not current for item in categories):
        raise ValueError(f"Memory category already exists: {clean_name}")
    item = {
        "name": clean_name,
        "icon": _safe_component(icon or "custom", "category icon")[:30],
        "description": str(description or "").strip()[:300],
    }
    custom = _custom_categories()
    if current.get("built_in"):
        built_in_name = str(current.get("built_in_name") or original)
        item["built_in_name"] = built_in_name
        custom = [entry for entry in custom if str(entry.get("built_in_name") or "").casefold() != built_in_name.casefold()]
        custom.append(item)
    else:
        replaced = False
        for index, entry in enumerate(custom):
            if not entry.get("built_in_name") and str(entry.get("name") or "").casefold() == original.casefold():
                custom[index] = item
                replaced = True
                break
        if not replaced:
            raise ValueError(f"Memory category not found: {original}")
    _categories_path().write_text(json.dumps(custom, indent=2, ensure_ascii=False), encoding="utf-8")
    for space in (KNOWLEDGE_ROOT / SPACES_FOLDER).iterdir():
        if not space.is_dir():
            continue
        metadata = _space_metadata(space)
        if str(metadata.get("category") or "").casefold() != original.casefold():
            continue
        metadata["category"] = clean_name
        (space / ".space.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"saved": True, "original_name": original, "category": dict(item, built_in=bool(current.get("built_in")))}


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
        "save_to_memory_database": {
            "name": "save_to_memory_database", "permission": "write",
            "description": "Save and automatically organize an ordinary memory when the user explicitly asks. Prefer this one-step tool when the user says to remember information and has not requested a specific space or note. Start with organization=auto and destination_note empty. If the result requests an organization choice, ask once, then repeat this tool with the unchanged content and the selected organization and destination_note.",
            "parameters": {"type": "object", "properties": {
                "content": {"type": "string", "maxLength": 40000},
                "title": {"type": "string", "description": "An optional short label when the user supplied one."},
                "preferred_area": {"type": "string", "enum": ["auto", "home", "people", "health", "work", "travel", "learning", "food", "hobbies", "general"]},
                "organization": {"type": "string", "enum": ["auto", "append_existing", "create_new"]},
                "destination_note": {"type": "string", "description": "Empty for automatic filing; otherwise the exact note offered by the choice result."},
            }, "required": ["content", "title", "preferred_area", "organization", "destination_note"], "additionalProperties": False},
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


def _automatic_memory_area(content: str, preferred_area: str = "") -> tuple[str, dict[str, Any]]:
    requested = str(preferred_area or "").strip().casefold().replace(" ", "_")
    aliases = {
        "auto": "", "work_&_projects": "work", "work_and_projects": "work",
        "food_&_recipes": "food", "food_and_recipes": "food",
    }
    requested = aliases.get(requested, requested)
    if requested and requested not in AUTO_MEMORY_AREAS:
        raise ValueError("Unknown automatic memory area")
    if requested:
        return requested, AUTO_MEMORY_AREAS[requested]

    normalized = " ".join(str(content or "").casefold().split())
    scored: list[tuple[int, int, str]] = []
    priority = ("health", "travel", "food", "work", "home", "learning", "people", "hobbies")
    for order, key in enumerate(priority):
        keywords = AUTO_MEMORY_AREAS[key]["keywords"]
        score = sum(2 if " " in keyword else 1 for keyword in keywords if keyword in normalized)
        scored.append((score, -order, key))
    best_score, _, best_key = max(scored)
    selected = best_key if best_score else "general"
    return selected, AUTO_MEMORY_AREAS[selected]


def _automatic_memory_note(area_key: str, content: str) -> str:
    normalized = str(content or "").casefold()
    topics = {
        "home": (
            (("repair", "maintenance", "service", "replace", "filter"), "Maintenance.md"),
            (("appliance", "air conditioner", "boiler", "fridge", "oven", "washing machine"), "Appliances.md"),
            (("routine", "schedule", "every day", "every week"), "Routines.md"),
        ),
        "health": (
            (("medicine", "medication", "tablet", "dose", "prescription"), "Medication.md"),
            (("doctor", "hospital", "clinic", "appointment"), "Appointments.md"),
        ),
        "work": (
            (("decision", "decided", "agreed"), "Decisions.md"),
            (("meeting", "call", "minutes"), "Meetings.md"),
            (("task", "deadline", "next action", "to-do", "todo"), "Next actions.md"),
        ),
        "travel": (
            (("flight", "hotel", "booking", "reservation", "train"), "Bookings.md"),
            (("pack", "packing"), "Packing.md"),
        ),
        "food": (
            (("soup", "broth", "bisque", "chowder"), "Soup Recipes.md"),
            (("stew",), "Stew Recipes.md"),
            (("pasta", "spaghetti", "lasagna"), "Pasta Recipes.md"),
            (("bread", "loaf", "focaccia"), "Bread Recipes.md"),
            (("cake", "cupcake"), "Cake Recipes.md"),
            (("dessert", "pudding", "pie", "tart"), "Dessert Recipes.md"),
            (("salad",), "Salad Recipes.md"),
            (("recipe", "ingredient", "cook", "bake"), "Recipes.md"),
            (("restaurant", "favorite", "prefers"), "Favorites.md"),
        ),
    }
    for keywords, note in topics.get(area_key, ()):
        if any(keyword in normalized for keyword in keywords):
            return note
    return {
        "home": "Household notes.md", "people": "Important information.md",
        "health": "Health notes.md", "work": "Work notes.md", "travel": "Travel plans.md",
        "learning": "Learning notes.md", "food": "Food notes.md", "hobbies": "Hobby notes.md",
        "general": "Notes.md",
    }[area_key]


def _narrower_memory_note(note: str, content: str) -> str:
    """Offer a useful sub-collection only when the content supplies a clear qualifier."""
    normalized = " ".join(str(content or "").casefold().split())
    qualifiers = (
        ("beef", "Beef"), ("chicken", "Chicken"), ("pork", "Pork"),
        ("lamb", "Lamb"), ("seafood", "Seafood"), ("fish", "Fish"),
        ("vegetarian", "Vegetarian"), ("vegan", "Vegan"),
    )
    qualifier = next((label for keyword, label in qualifiers if keyword in normalized), "")
    if not qualifier or not note.endswith(" Recipes.md"):
        return note
    topic = note.removesuffix(" Recipes.md")
    return f"{qualifier} {topic} Recipes.md"


def remember_automatically(
    content: str,
    title: str = "",
    preferred_area: str = "",
    organization: str = "auto",
    destination_note: str = "",
) -> dict[str, Any]:
    """File an explicitly submitted memory without making the user design its storage."""
    clean_content = str(content or "").strip()
    if not clean_content:
        raise ValueError("Tell ZBRANO what it should remember")
    if len(clean_content.encode("utf-8")) > 50_000:
        raise ValueError("This memory is too large to save at once")
    clean_title = " ".join(str(title or "").strip().split())[:160]
    organization = str(organization or "auto").strip().casefold()
    if organization not in {"auto", "append_existing", "create_new"}:
        raise ValueError("Unknown memory organization choice")
    area_key, area = _automatic_memory_area(clean_content, preferred_area)

    spaces = list_memory_spaces()["spaces"]
    configured_category = next(
        (
            str(item["name"])
            for item in list_memory_categories()["categories"]
            if str(item.get("built_in_name") or item.get("name") or "").casefold()
            == str(area["category"]).casefold()
        ),
        str(area["category"]),
    )
    matching = [item for item in spaces if str(item.get("category", "")).casefold() == configured_category.casefold()]
    exact = next((item for item in spaces if str(item.get("name", "")).casefold() == str(area["space"]).casefold()), None)
    destination = exact or (matching[0] if len(matching) == 1 else None)
    created_space = False
    if destination is None:
        created = create_memory_space(area["space"], area["purpose"], "blank", configured_category)
        destination = created["space"]
        created_space = True

    space_name = str(destination["name"])
    automatic_note = _automatic_memory_note(area_key, f"{clean_title}\n{clean_content}")
    narrower_note = _narrower_memory_note(automatic_note, f"{clean_title}\n{clean_content}")
    note = str(destination_note or "").strip() if organization != "auto" else automatic_note
    if note and not note.lower().endswith(".md"):
        note += ".md"
    if organization != "auto" and note not in {automatic_note, narrower_note}:
        raise ValueError("The selected destination note does not match the offered organization choices")
    if organization == "append_existing" and note != automatic_note:
        raise ValueError("Choose the existing note when appending")
    if organization == "create_new" and note != narrower_note:
        raise ValueError("Choose the proposed new note when creating a collection")
    note_path = _space_note_path(space_name, note)
    narrower_path = _space_note_path(space_name, narrower_note)
    if organization == "auto" and narrower_note != automatic_note and narrower_path.is_file():
        note = narrower_note
        note_path = narrower_path
    if organization == "auto" and narrower_note != automatic_note and not narrower_path.is_file():
        return {
            "saved": False,
            "choice_required": True,
            "question": (
                f"Save this in {automatic_note.removesuffix('.md')}, "
                f"or create {narrower_note.removesuffix('.md')}?"
            ),
            "space": space_name,
            "existing_note": automatic_note,
            "new_note": narrower_note,
            "choices": [
                {"id": "append_existing", "label": f"Use {automatic_note.removesuffix('.md')}", "destination_note": automatic_note},
                {"id": "create_new", "label": f"Create {narrower_note.removesuffix('.md')}", "destination_note": narrower_note},
            ],
        }
    previous = note_path.read_text(encoding="utf-8") if note_path.is_file() else ""
    comparable = " ".join(clean_content.casefold().split())
    duplicate = bool(comparable and comparable in " ".join(previous.casefold().split()))
    if not duplicate:
        body = clean_content.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\n  ")
        entry = f"- **{clean_title}:** {body}\n" if clean_title else f"- {body}\n"
        if note_path.is_file():
            separator = "" if previous.endswith("\n") else "\n"
            write_memory_note(space_name, note, f"{separator}{entry}", "append")
        else:
            heading = note.removesuffix(".md")
            write_memory_note(space_name, note, f"# {heading}\n\n{entry}", "create")

    return {
        "saved": True,
        "choice_required": False,
        "duplicate": duplicate,
        "created_space": created_space,
        "area": area["area"],
        "area_key": area_key,
        "icon": area["icon"],
        "space": space_name,
        "note": note,
        "relative_path": f"{SPACES_FOLDER}/{space_name}/{note}",
        "confirmation": f"Saved in {space_name} → {note.removesuffix('.md')}",
    }


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


def update_memory_note(space: str, original_note: str, note: str, content: str) -> dict[str, Any]:
    """Replace an existing note and optionally give it a new user-facing name."""
    original_path = _space_note_path(space, original_note)
    target_path = _space_note_path(space, note)
    if not original_path.is_file():
        raise ValueError(f"Knowledge Memory note not found: {space}/{original_note}")
    if target_path != original_path and target_path.exists():
        raise ValueError(f"Knowledge Memory note already exists: {target_path.name}")
    result = _write_path(original_path, content, "replace")
    if target_path != original_path:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        original_path.replace(target_path)
        result["relative_path"] = str(target_path.relative_to(KNOWLEDGE_ROOT)).replace("\\", "/")
    result["note"] = str(target_path.relative_to(_space_path(space))).replace("\\", "/")
    return result


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
    if tool_name in {"save_to_memory_database", "remember_automatically"}:
        return remember_automatically(
            arguments["content"],
            arguments.get("title", ""),
            arguments.get("preferred_area", "auto"),
            arguments.get("organization", "auto"),
            arguments.get("destination_note", ""),
        )
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
