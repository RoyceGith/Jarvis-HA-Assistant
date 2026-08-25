from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


developer_mode_enabled = None
load_preferences = None


def configure_web_search_service(*, developer_mode_enabled_fn, load_preferences_fn) -> None:
    global developer_mode_enabled, load_preferences
    developer_mode_enabled = developer_mode_enabled_fn
    load_preferences = load_preferences_fn


def native_web_search_tool(search_mode: str = "auto") -> dict[str, Any] | None:
    if developer_mode_enabled() or search_mode == "off":
        return None
    preferences = load_preferences()
    if preferences.get("web_search_enabled") is False:
        return None
    context_size = str(preferences.get("web_search_context_size") or "medium")
    if context_size not in {"low", "medium", "high"}:
        context_size = "medium"
    return {
        "type": "web_search",
        "search_context_size": context_size,
    }


def web_search_quality_instructions(base: str, search_mode: str = "auto") -> str:
    if developer_mode_enabled() or not native_web_search_tool(search_mode):
        return base
    return base + (
        "\n\nWhen using web search, prefer current primary or official sources. "
        "Use secondary reporting for context and community sources only for clearly labelled anecdotal evidence. "
        "Cite factual claims inline, and cite only pages that directly support those claims. "
        "Prefer direct articles or documentation over search, archive, category, or pagination pages. "
        "Check both publication and event dates when recency matters. Keep the cited set concise, normally 3 to 8 sources."
    )


def web_search_tool_choice(search_mode: str = "auto") -> Any:
    search_tool = native_web_search_tool(search_mode)
    return {"type": "web_search"} if search_mode == "search" and search_tool else "auto"


def web_search_include_options(search_mode: str = "auto") -> dict[str, Any]:
    return (
        {"include": ["web_search_call.action.sources"]}
        if native_web_search_tool(search_mode)
        else {}
    )


def canonical_web_source_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw.startswith(("https://", "http://")):
        return ""
    try:
        parts = urlsplit(raw)
    except ValueError:
        return ""
    hostname = str(parts.hostname or "").lower().rstrip(".")
    if not hostname:
        return ""
    try:
        port_number = parts.port
    except ValueError:
        return ""
    port = f":{port_number}" if port_number and port_number not in {80, 443} else ""
    tracking_names = {"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "ref_src"}
    clean_query = [
        (key, query_value)
        for key, query_value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in tracking_names
    ]
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), hostname + port, path, urlencode(clean_query), ""))


def response_web_sources(response: dict[str, Any] | None) -> list[dict[str, str]]:
    cited: list[dict[str, str]] = []
    discovered: list[dict[str, str]] = []
    cited_seen: set[str] = set()
    discovered_seen: set[str] = set()

    def add(bucket: list[dict[str, str]], seen: set[str], url: Any, title: Any = "") -> None:
        normalized_url = canonical_web_source_url(url)
        if not normalized_url or normalized_url in seen:
            return
        seen.add(normalized_url)
        clean_title = " ".join(str(title or normalized_url).split())
        bucket.append({"url": normalized_url[:2000], "title": clean_title[:300]})

    output = (response or {}).get("output", [])
    for item in output:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) if isinstance(item.get("content"), list) else []:
            if not isinstance(content, dict):
                continue
            for annotation in content.get("annotations", []) if isinstance(content.get("annotations"), list) else []:
                if isinstance(annotation, dict) and annotation.get("type") == "url_citation":
                    add(cited, cited_seen, annotation.get("url"), annotation.get("title"))

    for item in output:
        if not isinstance(item, dict):
            continue
        action = item.get("action") if isinstance(item.get("action"), dict) else {}
        for source in action.get("sources", []) if isinstance(action.get("sources"), list) else []:
            if isinstance(source, dict):
                add(discovered, discovered_seen, source.get("url"), source.get("title"))

    return (cited if cited else discovered)[:8]


def web_sources_markdown(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return ""
    lines = ["", "", "### Sources"]
    for source in sources[:8]:
        title = str(source.get("title") or source.get("url") or "Source").replace("[", "").replace("]", "")
        url = canonical_web_source_url(source.get("url"))
        if url:
            lines.append(f"- [{title}]({url})")
    return "\n".join(lines) if len(lines) > 3 else ""


def web_search_progress(event: dict[str, Any]) -> str | None:
    event_type = str(event.get("type") or "")
    item = event.get("item") if isinstance(event.get("item"), dict) else {}
    item_type = str(item.get("type") or "")
    if "web_search_call" not in event_type and item_type != "web_search_call":
        return None
    if event_type.endswith((".completed", ".done")):
        return "Web search complete. Reviewing sources..."
    return "Searching the web..."
