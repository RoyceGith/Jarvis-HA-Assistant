from pathlib import Path

ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.0 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    # Build-time gates for regressions already observed in the plugin/catalog
    # chain. Do not ship Developer Mode on top of a broken generated backend.
    require(text, "def _mcp_response_json(response):", "MCP response helper")
    require(text, "def _plugin_url_key(url):", "GitHub URL normalization helper")
    require(text, 'async def _fetch_plugin_catalog(force=False):', "catalog backend")
    require(text, '@app.get("/api/plugin-catalog")', "catalog route")

    backend_marker = '@app.get("/api/ha/websocket-status")\n'
    require(text, backend_marker, "developer backend insertion point")

    backend = r'''
DEVELOPER_STATE_PATH = Path("/data/zbrano_developer_mode.json")
DEVELOPER_REPOSITORY = "RoyceGith/Jarvis-HA-Assistant"
DEVELOPER_FRONTEND_PATH = Path(__file__).resolve().parent / "static/index.html"


class DeveloperModeRequest(BaseModel):
    enabled: bool


def developer_mode_enabled() -> bool:
    try:
        payload = json.loads(DEVELOPER_STATE_PATH.read_text(encoding="utf-8"))
        return bool(payload.get("enabled")) if isinstance(payload, dict) else False
    except (OSError, json.JSONDecodeError):
        return False


def set_developer_mode(enabled: bool) -> None:
    DEVELOPER_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEVELOPER_STATE_PATH.write_text(
        json.dumps({"enabled": bool(enabled), "updated_at": time.time()}, indent=2),
        encoding="utf-8",
    )


def developer_system_instructions(base: str) -> str:
    if not developer_mode_enabled():
        return base
    return base + """

ZBRANO DEVELOPER MODE IS ACTIVE.
You are maintaining your own software repository: RoyceGith/Jarvis-HA-Assistant.
You may inspect the repository and use the connected GitHub MCP tools to propose and implement software changes requested by the user.
Treat all GitHub mutations as approval-gated actions. Never bypass, weaken, remove, or silently alter approval rules, authentication, rollback protections, or Developer Mode protections.
Prefer a dedicated development branch for non-trivial changes. Inspect the relevant current source and patch-chain transformations before editing; do not assume generated markers exist.
Before proposing a release, verify the changed Python and JavaScript paths, preserve New Chat, Shared Files, Plugins, Entities, and GitHub integration, and report exactly what was tested.
Do not claim a Home Assistant deployment or restart occurred unless the running system confirms it. This Developer Mode can prepare repository updates; installation remains an explicit deployment step.
""".strip()


def _developer_check(name: str, ok: bool, detail: str = "") -> dict[str, object]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def developer_diagnostics() -> dict[str, object]:
    route_paths = {str(getattr(route, "path", "")) for route in app.routes}
    checks: list[dict[str, object]] = []

    required_routes = [
        "/api/plugin-catalog",
        "/api/plugins",
        "/api/files/shared",
        "/api/chats",
        "/api/developer/status",
        "/api/developer/diagnostics",
    ]
    for path in required_routes:
        checks.append(_developer_check(
            f"Route {path}",
            path in route_paths,
            "registered" if path in route_paths else "missing",
        ))

    checks.append(_developer_check(
        "Catalog backend",
        callable(globals().get("_fetch_plugin_catalog"))
        and callable(globals().get("_plugin_url_key"))
        and callable(globals().get("_mcp_response_json")),
        "catalog and MCP helpers available",
    ))
    checks.append(_developer_check(
        "Frontend source",
        DEVELOPER_FRONTEND_PATH.exists(),
        str(DEVELOPER_FRONTEND_PATH),
    ))

    frontend_text = ""
    try:
        frontend_text = DEVELOPER_FRONTEND_PATH.read_text(encoding="utf-8")
    except OSError:
        pass
    for element_id, label in (
        ("new-chat-button", "New Chat control"),
        ("files-tab", "Shared Files tab"),
        ("attach-file", "Attach control"),
        ("plugins-tab", "Plugins tab"),
        ("entities-tab", "Entities tab"),
        ("developer-tab", "Developer tab"),
    ):
        checks.append(_developer_check(
            label,
            f'id="{element_id}"' in frontend_text,
            element_id,
        ))

    registry = {}
    try:
        registry = plugin_registry()
    except Exception as exc:
        checks.append(_developer_check("Plugin registry", False, str(exc)))
    else:
        checks.append(_developer_check("Plugin registry", True, f"{len(registry)} installed"))

    github_plugin = next(
        (
            plugin for plugin in registry.values()
            if "github" in f"{plugin.get('name', '')} {plugin.get('url', '')}".lower()
        ),
        None,
    ) if isinstance(registry, dict) else None
    if github_plugin:
        tools = list(github_plugin.get("tools") or [])
        exposed = [
            tool for tool in tools
            if tool.get("enabled") and tool.get("permission") in {"read_only", "write"}
        ]
        approvals = [tool for tool in exposed if tool.get("permission") == "write"]
        checks.append(_developer_check(
            "GitHub MCP",
            bool(github_plugin.get("enabled") and exposed),
            f"{len(exposed)} tools exposed; {len(approvals)} approval-required",
        ))
    else:
        checks.append(_developer_check("GitHub MCP", False, "not installed"))

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


@app.get("/api/developer/status")
async def developer_status():
    return {
        "enabled": developer_mode_enabled(),
        "repository": DEVELOPER_REPOSITORY,
        "deployment": "manual",
    }


@app.put("/api/developer/mode")
async def update_developer_mode(request: DeveloperModeRequest):
    set_developer_mode(request.enabled)
    return {
        "enabled": developer_mode_enabled(),
        "repository": DEVELOPER_REPOSITORY,
        "deployment": "manual",
    }


@app.get("/api/developer/diagnostics")
async def get_developer_diagnostics():
    return developer_diagnostics()


'''
    text = text.replace(backend_marker, backend + backend_marker, 1)

    # Route every Responses API instruction payload through the Developer Mode
    # wrapper while leaving the existing base instruction generator intact.
    instruction_line = '"instructions": effective_system_instructions(),'
    replacements = text.count(instruction_line)
    if replacements < 1:
        raise RuntimeError("ZBRANO v0.12.0 patch missing: Responses API instruction call")
    text = text.replace(
        instruction_line,
        '"instructions": developer_system_instructions(effective_system_instructions()),',
    )

    text = text.replace('version="0.11.31"', 'version="0.12.0"')
    text = text.replace('"version": "0.11.31"', '"version": "0.12.0"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    files_tab = '<button id="files-tab">Shared Files</button>'
    require(text, files_tab, "Shared Files tab")
    if 'id="developer-tab"' not in text:
        text = text.replace(
            files_tab,
            '<button id="developer-tab">Developer</button>\n    ' + files_tab,
            1,
        )

    files_panel = '<section id="files-panel" class="panel hidden">'
    require(text, files_panel, "Shared Files panel")
    developer_panel = r'''<section id="developer-panel" class="panel hidden">
    <div class="developer-shell">
      <div class="developer-header">
        <div>
          <h2>DEVELOPER MODE</h2>
          <p class="muted">Inspect ZBRANO, run self-diagnostics, and allow approved GitHub maintenance of its own repository.</p>
        </div>
        <button id="developer-toggle" type="button" aria-pressed="false">Enable Developer Mode</button>
      </div>
      <div class="developer-warning">Developer Mode never bypasses GitHub approval. Repository changes can be prepared here; Home Assistant deployment remains explicit.</div>
      <div class="developer-actions">
        <button id="developer-run-diagnostics" type="button">Run diagnostics</button>
        <span id="developer-summary" class="muted">Diagnostics not run yet.</span>
      </div>
      <div id="developer-checks" class="developer-checks"></div>
      <div class="developer-console">
        <h3>Interface monitor</h3>
        <p id="developer-interface-status" class="muted">No client-side errors captured.</p>
      </div>
    </div>
  </section>

  '''
    if 'id="developer-panel"' not in text:
        text = text.replace(files_panel, developer_panel + files_panel, 1)

    style_close = text.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.0 patch missing: style close")
    css = r'''
    #developer-panel{overflow-y:auto;overflow-x:hidden}
    .developer-shell{display:grid;gap:.8rem;padding-bottom:1rem}
    .developer-header{display:flex;gap:1rem;justify-content:space-between;align-items:flex-start;flex-wrap:wrap}
    .developer-header h2{margin:.1rem 0 .35rem}
    .developer-warning{border:1px solid var(--line);border-radius:8px;padding:.7rem;background:var(--surface)}
    .developer-actions{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
    .developer-checks{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.55rem}
    .developer-check{border:1px solid var(--line);border-radius:8px;padding:.65rem;background:var(--surface)}
    .developer-check strong{display:block;margin-bottom:.2rem}
    .developer-check.ok strong{color:var(--cyan)}
    .developer-check.fail strong{color:#ff8a8a}
    .developer-console{border-top:1px solid var(--line);padding-top:.7rem}
'''
    if ".developer-shell{" not in text:
        text = text[:style_close] + css + "\n" + text[style_close:]

    runtime = r'''
<script id="zbrano-v0120-developer-mode">
(() => {
  const tab = document.getElementById("developer-tab");
  const panel = document.getElementById("developer-panel");
  const toggle = document.getElementById("developer-toggle");
  const run = document.getElementById("developer-run-diagnostics");
  const summary = document.getElementById("developer-summary");
  const checks = document.getElementById("developer-checks");
  const interfaceStatus = document.getElementById("developer-interface-status");
  if (!tab || !panel || !toggle || !run || !checks) return;

  const clientErrors = [];
  const rememberError = message => {
    const value = String(message || "Unknown client error");
    if (!clientErrors.includes(value)) clientErrors.push(value);
    while (clientErrors.length > 10) clientErrors.shift();
    renderInterfaceStatus();
  };
  window.addEventListener("error", event => rememberError(event.message));
  window.addEventListener("unhandledrejection", event => rememberError(event.reason?.message || event.reason));

  function renderInterfaceStatus() {
    if (!interfaceStatus) return;
    const required = ["new-chat-button", "files-tab", "attach-file", "plugins-tab", "entities-tab", "developer-tab"];
    const missing = required.filter(id => !document.getElementById(id));
    if (!clientErrors.length && !missing.length) {
      interfaceStatus.textContent = "Interface monitor healthy · required controls present · no captured JavaScript errors.";
      return;
    }
    const parts = [];
    if (missing.length) parts.push(`Missing controls: ${missing.join(", ")}`);
    if (clientErrors.length) parts.push(`Recent errors: ${clientErrors.join(" | ")}`);
    interfaceStatus.textContent = parts.join(" · ");
  }

  function hideDeveloperPanel() {
    panel.classList.add("hidden");
    tab.classList.remove("active");
  }

  function activateDeveloperPanel() {
    for (const id of ["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel", "developer-panel"]) {
      document.getElementById(id)?.classList.toggle("hidden", id !== "developer-panel");
    }
    for (const id of ["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab", "developer-tab"]) {
      document.getElementById(id)?.classList.toggle("active", id === "developer-tab");
    }
  }

  function syncToggle(enabled) {
    toggle.dataset.enabled = enabled ? "true" : "false";
    toggle.setAttribute("aria-pressed", enabled ? "true" : "false");
    toggle.textContent = enabled ? "Disable Developer Mode" : "Enable Developer Mode";
  }

  async function loadStatus() {
    const response = await fetch("api/developer/status", {cache: "no-store"});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    syncToggle(Boolean(data.enabled));
    return data;
  }

  async function runDiagnostics() {
    summary.textContent = "Running diagnostics…";
    run.disabled = true;
    try {
      const response = await fetch("api/developer/diagnostics", {cache: "no-store"});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      checks.replaceChildren();
      for (const item of data.checks || []) {
        const card = document.createElement("div");
        card.className = `developer-check ${item.ok ? "ok" : "fail"}`;
        const title = document.createElement("strong");
        title.textContent = `${item.ok ? "✓" : "✕"} ${item.name}`;
        const detail = document.createElement("div");
        detail.className = "muted";
        detail.textContent = item.detail || "";
        card.append(title, detail);
        checks.appendChild(card);
      }
      summary.textContent = `${data.passed}/${data.total} checks passed${data.healthy ? " · healthy" : " · attention required"}`;
      syncToggle(Boolean(data.developer_mode));
      renderInterfaceStatus();
    } catch (error) {
      summary.textContent = `Diagnostics failed: ${error.message || error}`;
    } finally {
      run.disabled = false;
    }
  }

  tab.addEventListener("click", event => {
    event.preventDefault();
    event.stopPropagation();
    activateDeveloperPanel();
    loadStatus().catch(error => { summary.textContent = `Developer status failed: ${error.message || error}`; });
    runDiagnostics();
  }, true);

  // Existing navigation predates Developer Mode. Hide this panel whenever an
  // older navigation control is used so it cannot overlay Chat/Files/Plugins.
  for (const id of ["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab", "new-chat-button"]) {
    document.getElementById(id)?.addEventListener("click", hideDeveloperPanel, true);
  }

  toggle.addEventListener("click", async () => {
    const next = toggle.dataset.enabled !== "true";
    toggle.disabled = true;
    try {
      const response = await fetch("api/developer/mode", {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({enabled: next}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      syncToggle(Boolean(data.enabled));
      summary.textContent = data.enabled
        ? "Developer Mode active. Chat may now maintain the ZBRANO repository using approval-gated GitHub tools."
        : "Developer Mode disabled.";
    } catch (error) {
      summary.textContent = `Could not change Developer Mode: ${error.message || error}`;
    } finally {
      toggle.disabled = false;
    }
  });

  run.addEventListener("click", runDiagnostics);
  renderInterfaceStatus();
})();
</script>
'''
    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.0 patch missing: body close")
    if 'id="zbrano-v0120-developer-mode"' not in text:
        text = text[:body_close] + runtime + text[body_close:]

    text = text.replace("HUD 0.11.31", "HUD 0.12.0")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    missing = []

    for marker in (
        'def _mcp_response_json(response):',
        'def _plugin_url_key(url):',
        'async def _fetch_plugin_catalog(force=False):',
        'DEVELOPER_FRONTEND_PATH = Path(__file__).resolve().parent / "static/index.html"',
        'DEVELOPER_STATE_PATH',
        'def developer_system_instructions(base: str)',
        '@app.get("/api/developer/status")',
        '@app.put("/api/developer/mode")',
        '@app.get("/api/developer/diagnostics")',
        'developer_system_instructions(effective_system_instructions())',
        'version="0.12.0"',
    ):
        if marker not in main:
            missing.append(marker)

    for marker in (
        'id="developer-tab"',
        'id="developer-panel"',
        'id="developer-toggle"',
        'id="developer-run-diagnostics"',
        'id="zbrano-v0120-developer-mode"',
        'Interface monitor healthy',
        'hideDeveloperPanel',
        'HUD 0.12.0',
    ):
        if marker not in index:
            missing.append(marker)

    if missing:
        raise RuntimeError("ZBRANO v0.12.0 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
