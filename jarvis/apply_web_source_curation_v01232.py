import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.32 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.32 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    source_start = backend.find("def response_web_sources(")
    source_end = backend.find("\n\ndef web_search_progress(", source_start)
    if source_start < 0 or source_end < 0:
        raise RuntimeError("ZBRANO v0.12.32 patch could not locate web source helpers")

    curated_sources = '''def canonical_web_source_url(value: Any) -> str:
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
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

    # Search calls expose every candidate considered by the model. Use these
    # only as a bounded fallback when the final answer contains no citations.
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
    return "\\n".join(lines) if len(lines) > 3 else ""
'''
    backend = backend[:source_start] + curated_sources + backend[source_end:]

    instruction_helper = '''def web_search_quality_instructions(base: str, search_mode: str = "auto") -> str:
    if developer_mode_enabled() or not native_web_search_tool(search_mode):
        return base
    return base + (
        "\\n\\nWhen using web search, prefer current primary or official sources. "
        "Use secondary reporting for context and community sources only for clearly labelled anecdotal evidence. "
        "Cite factual claims inline, and cite only pages that directly support those claims. "
        "Prefer direct articles or documentation over search, archive, category, or pagination pages. "
        "Check both publication and event dates when recency matters. Keep the cited set concise, normally 3 to 8 sources."
    )


'''
    backend = replace_once(
        backend,
        "def web_search_tool_choice(search_mode: str = \"auto\") -> Any:\n",
        instruction_helper + "def web_search_tool_choice(search_mode: str = \"auto\") -> Any:\n",
        "web quality instructions",
    )

    stream_start = backend.find("async def _run_jarvis_stream_events(")
    stream_end = backend.find("\n\nasync def run_jarvis_stream(", stream_start)
    if stream_start < 0 or stream_end < 0:
        raise RuntimeError("ZBRANO v0.12.32 patch could not locate streaming function")
    stream_section = backend[stream_start:stream_end]
    old_instruction = "developer_system_instructions(effective_system_instructions())"
    instruction_count = stream_section.count(old_instruction)
    if instruction_count != 3:
        raise RuntimeError(
            f"ZBRANO v0.12.32 patch expected three streaming instruction payloads; found {instruction_count}"
        )
    stream_section = stream_section.replace(
        old_instruction,
        "web_search_quality_instructions(developer_system_instructions(effective_system_instructions()), search_mode)",
    )
    backend = backend[:stream_start] + stream_section + backend[stream_end:]

    frontend = replace_once(
        frontend,
        '''      const unique = sources.filter((source, index, items) => source?.url && items.findIndex(item => item?.url === source.url) === index);''',
        '''      const unique = sources.filter((source, index, items) => source?.url && items.findIndex(item => item?.url === source.url) === index).slice(0, 8);''',
        "frontend source cap",
    )

    backend = backend.replace('version="0.12.31"', 'version="0.12.32"')
    backend = backend.replace('"version": "0.12.31"', '"version": "0.12.32"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.31"', '"X-ZBRANO-Frontend-Version": "0.12.32"')
    frontend = frontend.replace("HUD 0.12.31", "HUD 0.12.32")

    require(backend, "def canonical_web_source_url", "source URL canonicalization")
    require(backend, "return (cited if cited else discovered)[:8]", "citation-first source selection")
    require(backend, "def web_search_quality_instructions", "primary-source search guidance")
    require(frontend, ").slice(0, 8);", "defensive frontend source cap")
    require(backend, 'version="0.12.32"', "backend version")
    require(frontend, "HUD 0.12.32", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
