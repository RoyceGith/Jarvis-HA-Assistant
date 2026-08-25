from __future__ import annotations

import re
from pathlib import Path


DEVELOPER_REPOSITORY = "RoyceGith/Jarvis-HA-Assistant"
DEVELOPER_FRONTEND_PATH = Path(__file__).resolve().parent.parent / "static/index.html"


def _developer_frontend_source() -> str:
    html = DEVELOPER_FRONTEND_PATH.read_text(encoding="utf-8")
    static_root = DEVELOPER_FRONTEND_PATH.parent.resolve()
    sources = [html]
    for relative_path in re.findall(r'<script\b[^>]*\bsrc="([^"]+\.js)"', html, flags=re.I):
        if "://" in relative_path:
            continue
        source_path = (static_root / relative_path).resolve()
        if not source_path.is_relative_to(static_root):
            raise OSError(f"Frontend script escapes static root: {relative_path}")
        sources.append(source_path.read_text(encoding="utf-8"))
    return "\n".join(sources)


def _developer_check(name: str, ok: bool, detail: str = "") -> dict[str, object]:
    return {"name": name, "ok": bool(ok), "detail": detail}


DEVELOPER_FEATURE_SPECS = {
    "web_search": {
        "title": "Native Web Search",
        "aliases": ("web search", "search web", "internet search", "citation", "sources"),
        "terms": ("native web search", "ai chat", "application health"),
        "layers": ("chat mode", "responses api tool", "stream events", "citations"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "ha_history": {
        "title": "Home Assistant History & Event Timeline",
        "aliases": ("history", "timeline", "logbook", "entity trend", "state changes", "correlation"),
        "terms": ("history API", "logbook API", "approved entities", "bounded query", "timeline interface"),
        "layers": ("entity policy", "Recorder history", "Logbook", "trend summary", "timeline interface"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "fast_memory": {
        "title": "Fast Memory",
        "aliases": ("fast memory", "personal profile", "session memory", "remember", "forget"),
        "terms": ("fast memory", "frontend source", "persistent storage", "application health"),
        "layers": ("SQLite storage", "deduplication", "retrieval", "background extraction", "interface"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "attachments": {
        "title": "Chat attachments",
        "aliases": ("attach", "attachment", "upload", "file picker", "chip"),
        "terms": ("attachment", "frontend source", "application health", "persistent storage"),
        "layers": ("frontend", "api", "persistence", "chat send"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "shared_files": {
        "title": "Shared Files",
        "aliases": ("shared file", "shared files", "delete selected", "attach selected"),
        "terms": ("shared files", "frontend source", "persistent storage", "application health"),
        "layers": ("frontend", "api", "persistence", "selection state"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "new_chat": {
        "title": "New Chat",
        "aliases": ("new chat", "conversation", "chat reset", "chat sidebar"),
        "terms": ("conversation", "new chat", "frontend source", "application health"),
        "layers": ("frontend", "api", "persistence", "request cancellation"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "plugin_catalog": {
        "title": "Plugin Catalog",
        "aliases": ("plugin catalog", "catalog", "registry", "plugin list"),
        "terms": ("plugin catalog", "plugins api", "plugins frontend", "application health"),
        "layers": ("frontend", "api", "cache", "remote registry"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "plugins": {
        "title": "Installed plugins",
        "aliases": ("plugin", "plugins", "plugin settings", "mcp plugin"),
        "terms": ("plugins api", "plugin registry", "plugins frontend", "github mcp"),
        "layers": ("frontend", "registry", "tool exposure", "authentication"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "automations": {
        "title": "Autonomous Automations",
        "aliases": ("automation", "automations", "autonomy", "suggestion", "proactive", "sensor monitoring"),
        "terms": ("automation", "home assistant", "frontend source", "persistent storage", "application health"),
        "layers": ("frontend", "api", "persistence", "entity context", "safety policy"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "entities": {
        "title": "Home Assistant entities",
        "aliases": ("entity", "entities", "home assistant", "device control", "device state"),
        "terms": ("entity", "home assistant", "application health"),
        "layers": ("frontend", "api", "websocket", "entity policy"),
        "files": (
            "jarvis/app/main.py",
            "jarvis/app/static/index.html",
            "jarvis/app/intent_router.py",
        ),
    },
    "settings": {
        "title": "Settings and persistence",
        "aliases": ("setting", "settings", "preference", "backup", "restore", "instruction"),
        "terms": ("settings", "persistent storage", "frontend source", "application health"),
        "layers": ("frontend", "api", "validation", "persistence"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "voice": {
        "title": "Voice",
        "aliases": ("voice", "microphone", "speech", "transcription", "elevenlabs", "tts"),
        "terms": ("voice", "frontend source", "application health"),
        "layers": ("browser permission", "transcription api", "speech provider", "playback"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html", "jarvis/config.yaml"),
    },
    "workshop_memory": {
        "title": "Workshop Memory",
        "aliases": ("workshop memory", "memory", "mcp memory", "project context"),
        "terms": ("workshop memory", "connection status", "application health"),
        "layers": ("configuration", "mcp transport", "tool response", "cache"),
        "files": ("jarvis/app/main.py", "jarvis/config.yaml"),
    },
    "developer": {
        "title": "Developer Mode",
        "aliases": ("developer", "diagnostic", "self fix", "self-fix", "github"),
        "terms": ("developer", "github mcp", "frontend source", "application health"),
        "layers": ("mode state", "diagnostics", "github tools", "approval policy"),
        "files": ("jarvis/app/main.py", "jarvis/app/static/index.html", "jarvis/Dockerfile"),
    },
}


def _resolve_developer_feature(feature: str, symptom: str) -> str:
    requested = feature.strip().lower().replace("-", "_").replace(" ", "_")
    if requested in DEVELOPER_FEATURE_SPECS:
        return requested
    haystack = f"{feature} {symptom}".lower()
    matches = []
    for key, spec in DEVELOPER_FEATURE_SPECS.items():
        for alias in spec["aliases"]:
            if alias in haystack:
                matches.append((len(alias), key))
    matches.sort(reverse=True)
    return matches[0][1] if matches else "developer"


