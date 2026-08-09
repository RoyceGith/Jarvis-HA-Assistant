import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.36 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.36 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    inspect_start = backend.find("async def inspect_zbrano_ui_with_playwright(")
    inspect_end = backend.find("\n\nasync def playwright_builtin_plugin(", inspect_start)
    if inspect_start < 0 or inspect_end < 0:
        raise RuntimeError("ZBRANO v0.12.36 patch could not locate Playwright inspection")

    bounded_inspection = '''async def inspect_zbrano_ui_with_playwright(
    path: str = "/",
    surface: str = "chat",
    wait_ms: int = 750,
) -> dict[str, Any]:
    """Collect browser-only evidence with a 30-second end-to-end deadline."""
    if not developer_mode_enabled():
        raise RuntimeError("Developer Mode must be enabled before Playwright inspection")
    url = _playwright_local_url(path)
    normalized_surface = str(surface or "chat").strip().lower()
    if normalized_surface not in PLAYWRIGHT_SURFACE_SELECTORS:
        raise ValueError("Unknown ZBRANO surface requested for Playwright inspection")
    bounded_wait_ms = max(0, min(int(wait_ms), 5000))
    step = {"name": "session initialization"}

    async def collect() -> dict[str, Any]:
        async with _playwright_session() as (client, headers):
            step["name"] = "tool inventory"
            inventory = await _playwright_rpc(client, headers, 2, "tools/list")
            names = {
                str(tool.get("name") or "")
                for tool in inventory.get("tools") or []
                if isinstance(tool, dict)
            }
            missing = sorted(PLAYWRIGHT_REQUIRED_TOOLS - names)
            if missing:
                raise RuntimeError(f"Playwright MCP is missing required tools: {', '.join(missing)}")
            step["name"] = "browser navigation"
            navigation = await _playwright_rpc(
                client,
                headers,
                3,
                "tools/call",
                {"name": "browser_navigate", "arguments": {"url": url}},
            )
            _playwright_text(navigation, 1000)
            selector = PLAYWRIGHT_SURFACE_SELECTORS[normalized_surface]
            if selector:
                step["name"] = f"{normalized_surface} tab navigation"
                tab_result = await _playwright_rpc(
                    client,
                    headers,
                    4,
                    "tools/call",
                    {
                        "name": "browser_click",
                        "arguments": {
                            "target": selector,
                            "element": f"ZBRANO {normalized_surface.replace('_', ' ')} navigation tab",
                        },
                    },
                )
                _playwright_text(tab_result, 1000)
            if bounded_wait_ms:
                step["name"] = "post-navigation wait"
                await asyncio.sleep(bounded_wait_ms / 1000)
            step["name"] = "accessibility snapshot"
            snapshot = await _playwright_rpc(
                client, headers, 5, "tools/call", {"name": "browser_snapshot", "arguments": {}}
            )
            step["name"] = "console error collection"
            console = await _playwright_rpc(
                client,
                headers,
                6,
                "tools/call",
                {"name": "browser_console_messages", "arguments": {"level": "error"}},
            )
            step["name"] = "network request collection"
            network = await _playwright_rpc(
                client,
                headers,
                7,
                "tools/call",
                {"name": "browser_network_requests", "arguments": {"static": False}},
            )
        return {
            "success": True,
            "scope": "zbrano_local_ui",
            "url": url,
            "surface": normalized_surface,
            "wait_ms": bounded_wait_ms,
            "snapshot": _playwright_text(snapshot, PLAYWRIGHT_OUTPUT_LIMITS["snapshot"]),
            "console_errors": _playwright_text(console, PLAYWRIGHT_OUTPUT_LIMITS["console"]),
            "network_requests": _playwright_text(network, PLAYWRIGHT_OUTPUT_LIMITS["network"]),
            "interaction_scope": "navigation_tab_only" if selector else "navigation_only",
        }

    try:
        return await asyncio.wait_for(collect(), timeout=30.0)
    except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
        raise RuntimeError(
            f"Playwright inspection timed out during {step['name']}; "
            f"{playwright_preflight_summary(include_log=True)}"
        ) from exc
'''
    backend = backend[:inspect_start] + bounded_inspection + backend[inspect_end:]

    backend = replace_once(
        backend,
        '''            "Open ZBRANO's own local UI in a headless Chromium browser and return a bounded "
            "accessibility snapshot, console errors, and network requests. It can switch only "
            "among known ZBRANO navigation tabs; it cannot browse external sites or operate feature controls."''',
        '''            "Use only when the user reports a visible ZBRANO browser symptom involving DOM layout, "
            "rendering, browser console errors, or browser network requests. Never call this tool for "
            "backend APIs, MCP approval payloads, versions, repository source, or non-visual tool execution. "
            "It inspects only ZBRANO's local UI and returns bounded browser evidence."''',
        "Playwright tool routing description",
    )

    backend = replace_once(
        backend,
        '''After the single targeted diagnostic, use Playwright when the reported symptom requires browser DOM, console, or network evidence. Treat an inconclusive result as an open defect:''',
        '''After the single targeted diagnostic, use Playwright only when the user reported a visible DOM, layout, rendering, browser-console, or browser-network defect. Never use Playwright for backend API behavior, MCP approval payloads, version checks, repository source verification, or non-visual tool execution. Treat an inconclusive result as an open defect:''',
        "Developer Playwright routing policy",
    )

    backend = replace_once(
        backend,
        '''        hard_timeout = 40.0 if "investigate_zbrano_feature" in tool_names_list else 90.0''',
        '''        hard_timeout = (
            40.0 if "investigate_zbrano_feature" in tool_names_list
            else 35.0 if "inspect_zbrano_ui_with_playwright" in tool_names_list
            else 90.0
        )''',
        "Playwright outer deadline",
    )

    backend = backend.replace('version="0.12.35"', 'version="0.12.36"')
    backend = backend.replace('"version": "0.12.35"', '"version": "0.12.36"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.35"', '"X-ZBRANO-Frontend-Version": "0.12.36"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.35"', '"name": "ZBRANO Developer Mode", "version": "0.12.36"')
    frontend = frontend.replace("HUD 0.12.35", "HUD 0.12.36")

    require(backend, "return await asyncio.wait_for(collect(), timeout=30.0)", "bounded Playwright inspection")
    require(backend, "Playwright inspection timed out during", "step-specific timeout evidence")
    require(backend, "Never call this tool for", "tool routing boundary")
    require(backend, "else 35.0 if", "outer Playwright deadline")
    require(backend, 'version="0.12.36"', "backend version")
    require(frontend, "HUD 0.12.36", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
