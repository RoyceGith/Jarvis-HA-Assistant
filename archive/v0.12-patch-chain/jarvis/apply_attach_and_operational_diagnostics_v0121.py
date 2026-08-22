from pathlib import Path

ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.1 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    start = text.find("def developer_diagnostics() -> dict[str, object]:")
    end = text.find('\n\n@app.get("/api/developer/status")', start)
    if start < 0 or end < 0:
        raise RuntimeError("ZBRANO v0.12.1 patch missing: developer diagnostics bounds")

    diagnostics = r'''async def developer_diagnostics() -> dict[str, object]:
    checks: list[dict[str, object]] = []

    async def probe(name: str, path: str, validator=None, timeout: float = 8.0) -> None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"http://127.0.0.1:8099{path}")
            if response.is_error:
                checks.append(_developer_check(name, False, f"HTTP {response.status_code}: {response.text[:180]}"))
                return
            try:
                payload = response.json()
            except Exception:
                payload = None
            if validator is None:
                checks.append(_developer_check(name, True, f"HTTP {response.status_code}"))
                return
            ok, detail = validator(payload)
            checks.append(_developer_check(name, ok, detail))
        except Exception as exc:
            checks.append(_developer_check(name, False, str(exc)))

    await probe(
        "Plugin Catalog operational",
        "/api/plugin-catalog",
        lambda payload: (
            isinstance(payload, dict) and isinstance(payload.get("plugins"), list) and len(payload.get("plugins")) > 0,
            f"{len(payload.get('plugins', [])) if isinstance(payload, dict) else 0} plugins returned",
        ),
        timeout=12.0,
    )
    await probe(
        "Plugins API operational",
        "/api/plugins",
        lambda payload: (
            isinstance(payload, dict) and isinstance(payload.get("plugins"), list),
            f"{len(payload.get('plugins', [])) if isinstance(payload, dict) else 0} installed plugins",
        ),
    )
    await probe(
        "Shared Files operational",
        "/api/files/shared",
        lambda payload: (
            isinstance(payload, dict) and isinstance(payload.get("files"), list),
            f"{len(payload.get('files', [])) if isinstance(payload, dict) else 0} shared files",
        ),
    )
    await probe(
        "Chats API operational",
        "/api/chats",
        lambda payload: (
            isinstance(payload, dict) and isinstance(payload.get("chats"), list),
            f"{len(payload.get('chats', [])) if isinstance(payload, dict) else 0} chats",
        ),
    )
    await probe(
        "Entities API operational",
        "/api/ha/entities",
        lambda payload: (
            isinstance(payload, dict) and isinstance(payload.get("entities"), list) and len(payload.get("entities")) > 0,
            f"{len(payload.get('entities', [])) if isinstance(payload, dict) else 0} entities",
        ),
        timeout=12.0,
    )
    await probe("Developer status operational", "/api/developer/status")

    frontend_text = ""
    try:
        frontend_text = DEVELOPER_FRONTEND_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        checks.append(_developer_check("Frontend source readable", False, str(exc)))
    else:
        checks.append(_developer_check("Frontend source readable", True, str(DEVELOPER_FRONTEND_PATH)))
        structural = {
            "New Chat wiring present": ('id="new-chat-button"', "createNewChat", 'newChatButton.addEventListener("click", createNewChat)'),
            "Attach recovery present": ('id="attach-file"', 'id="attachment-input"', 'zbrano-v0121-attach-recovery'),
            "Shared Files recovery present": ('id="files-tab"', 'zbrano-v01130-shared-files-recovery', 'window.zbranoLoadSharedFiles'),
            "Plugins compact settings present": ('id="plugins-tab"', 'zbrano-v01131-plugin-compact', 'plugin-settings-toggle'),
            "Entities interface present": ('id="entities-tab"', 'id="entities-panel"', 'loadEntities'),
            "Developer interface present": ('id="developer-tab"', 'zbrano-v0120-developer-mode', 'developer-run-diagnostics'),
            "Chat attachment send path present": ('attachment_ids: attachmentIds', 'window.zbranoAttachmentIds', 'window.zbranoClearPendingAttachments'),
        }
        for name, markers in structural.items():
            missing = [marker for marker in markers if marker not in frontend_text]
            checks.append(_developer_check(name, not missing, "wired" if not missing else "missing: " + ", ".join(missing)))

    registry = {}
    try:
        registry = plugin_registry()
    except Exception as exc:
        checks.append(_developer_check("Plugin registry operational", False, str(exc)))
    else:
        checks.append(_developer_check("Plugin registry operational", True, f"{len(registry)} installed"))

    github_plugin = next(
        (plugin for plugin in registry.values() if "github" in f"{plugin.get('name', '')} {plugin.get('url', '')}".lower()),
        None,
    ) if isinstance(registry, dict) else None
    if github_plugin:
        tools = list(github_plugin.get("tools") or [])
        exposed = [tool for tool in tools if tool.get("enabled") and tool.get("permission") in {"read_only", "write"}]
        approvals = [tool for tool in exposed if tool.get("permission") == "write"]
        checks.append(_developer_check(
            "GitHub MCP operational",
            bool(github_plugin.get("enabled") and exposed),
            f"{len(exposed)} tools exposed; {len(approvals)} approval-required",
        ))
    else:
        checks.append(_developer_check("GitHub MCP operational", False, "not installed"))

    passed = sum(1 for check in checks if check["ok"])
    return {
        "developer_mode": developer_mode_enabled(),
        "repository": DEVELOPER_REPOSITORY,
        "passed": passed,
        "total": len(checks),
        "healthy": passed == len(checks),
        "checks": checks,
        "deployment": "manual",
    }
'''
    text = text[:start] + diagnostics + text[end:]

    old_route = '''@app.get("/api/developer/diagnostics")
async def get_developer_diagnostics():
    return developer_diagnostics()'''
    new_route = '''@app.get("/api/developer/diagnostics")
async def get_developer_diagnostics():
    return await developer_diagnostics()'''
    require(text, old_route, "developer diagnostics route")
    text = text.replace(old_route, new_route, 1)

    text = text.replace('version="0.12.0"', 'version="0.12.1"')
    text = text.replace('"version": "0.12.0"', '"version": "0.12.1"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    for marker, label in (
        ('id="attach-file"', "Attach button"),
        ('id="attachment-input"', "file input"),
        ('id="developer-checks"', "developer checks"),
    ):
        require(text, marker, label)

    runtime = r'''
<script id="zbrano-v0121-attach-recovery">
(() => {
  const attach = document.getElementById("attach-file");
  const picker = document.getElementById("attachment-input");
  if (!attach || !picker) return;

  window.zbranoAttachRecovery = {
    installed: true,
    attachId: attach.id,
    pickerId: picker.id,
  };

  // Capture phase intentionally owns the picker-open action. The historical
  // upload/change handler remains untouched; this only restores the dead click.
  attach.addEventListener("click", event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    picker.click();
  }, true);
})();
</script>
'''
    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.1 patch missing: body close")
    text = text[:body_close] + runtime + text[body_close:]

    # Add browser-runtime checks to the diagnostics response before rendering.
    needle = '''      checks.replaceChildren();
      for (const item of data.checks || []) {'''
    require(text, needle, "developer diagnostics rendering")
    replacement = '''      const browserChecks = [
        {
          name: "Attach click wiring active",
          ok: Boolean(window.zbranoAttachRecovery?.installed && document.getElementById("attach-file") && document.getElementById("attachment-input")),
          detail: window.zbranoAttachRecovery?.installed ? "late recovery controller active" : "attach controller unavailable",
        },
        {
          name: "New Chat runtime available",
          ok: typeof createNewChat === "function" && Boolean(document.getElementById("new-chat-button")),
          detail: typeof createNewChat === "function" ? "createNewChat callable" : "createNewChat unavailable",
        },
        {
          name: "Shared Files runtime available",
          ok: typeof window.zbranoLoadSharedFiles === "function" && Boolean(document.getElementById("files-panel")),
          detail: typeof window.zbranoLoadSharedFiles === "function" ? "recovery loader callable" : "recovery loader unavailable",
        },
        {
          name: "Plugin settings runtime available",
          ok: Boolean(document.querySelector("#zbrano-v01131-plugin-compact")) && Boolean(document.getElementById("plugins-panel")),
          detail: document.querySelector("#zbrano-v01131-plugin-compact") ? "compact settings controller loaded" : "controller unavailable",
        },
        {
          name: "Developer runtime available",
          ok: Boolean(document.querySelector("#zbrano-v0120-developer-mode")) && Boolean(document.getElementById("developer-panel")),
          detail: "developer controller and panel",
        },
      ];
      data.checks = [...(data.checks || []), ...browserChecks];
      data.total = data.checks.length;
      data.passed = data.checks.filter(item => item.ok).length;
      data.healthy = data.passed === data.total;
      checks.replaceChildren();
      for (const item of data.checks || []) {'''
    text = text.replace(needle, replacement, 1)

    text = text.replace("HUD 0.12.0", "HUD 0.12.1")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    missing = []
    for marker in (
        'async def developer_diagnostics()',
        'http://127.0.0.1:8099',
        '"Plugin Catalog operational"',
        '"Shared Files operational"',
        '"Entities API operational"',
        'return await developer_diagnostics()',
        'version="0.12.1"',
    ):
        if marker not in main:
            missing.append(marker)
    for marker in (
        'id="zbrano-v0121-attach-recovery"',
        'window.zbranoAttachRecovery',
        'event.stopImmediatePropagation()',
        '"Attach click wiring active"',
        '"Shared Files runtime available"',
        'HUD 0.12.1',
    ):
        if marker not in index:
            missing.append(marker)
    if missing:
        raise RuntimeError("ZBRANO v0.12.1 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
