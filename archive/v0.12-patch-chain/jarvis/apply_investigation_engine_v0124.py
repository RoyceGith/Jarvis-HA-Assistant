from pathlib import Path


ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.4 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    route_marker = '\n\n@app.get("/api/developer/status")'
    require(text, route_marker, "Developer status route")

    investigation_backend = r'''

DEVELOPER_FEATURE_SPECS = {
    "attachments": {
        "title": "Chat attachments",
        "aliases": ("attach", "attachment", "upload", "file picker", "chip"),
        "terms": ("attachment", "frontend source", "application health", "persistent storage"),
        "layers": ("frontend", "api", "persistence", "chat send"),
        "files": (
            "jarvis/apply_attachment_upload_fix_v0122.py",
            "jarvis/apply_shared_files_and_diagnostics_v0123.py",
            "jarvis/app/main.py",
            "jarvis/app/static/index.html",
        ),
    },
    "shared_files": {
        "title": "Shared Files",
        "aliases": ("shared file", "shared files", "delete selected", "attach selected"),
        "terms": ("shared files", "frontend source", "persistent storage", "application health"),
        "layers": ("frontend", "api", "persistence", "selection state"),
        "files": (
            "jarvis/apply_shared_files_and_diagnostics_v0123.py",
            "jarvis/apply_shared_files_runtime_recovery_v01130.py",
            "jarvis/app/main.py",
            "jarvis/app/static/index.html",
        ),
    },
    "new_chat": {
        "title": "New Chat",
        "aliases": ("new chat", "conversation", "chat reset", "chat sidebar"),
        "terms": ("conversation", "new chat", "frontend source", "application health"),
        "layers": ("frontend", "api", "persistence", "request cancellation"),
        "files": (
            "jarvis/apply_new_chat_draft_fix_v01121.py",
            "jarvis/apply_new_chat_shared_files_fix_v01122.py",
            "jarvis/apply_new_chat_sidebar_draft_v01123.py",
            "jarvis/app/static/index.html",
        ),
    },
    "plugin_catalog": {
        "title": "Plugin Catalog",
        "aliases": ("plugin catalog", "catalog", "registry", "plugin list"),
        "terms": ("plugin catalog", "plugins api", "plugins frontend", "application health"),
        "layers": ("frontend", "api", "cache", "remote registry"),
        "files": (
            "jarvis/apply_plugin_catalog_v0110.py",
            "jarvis/apply_plugin_manager_recovery_v01128.py",
            "jarvis/apply_catalog_and_plugin_compact_v01131.py",
            "jarvis/app/main.py",
        ),
    },
    "plugins": {
        "title": "Installed plugins",
        "aliases": ("plugin", "plugins", "plugin settings", "mcp plugin"),
        "terms": ("plugins api", "plugin registry", "plugins frontend", "github mcp"),
        "layers": ("frontend", "registry", "tool exposure", "authentication"),
        "files": (
            "jarvis/apply_plugin_manager_recovery_v01128.py",
            "jarvis/apply_github_tool_approval_policy_v01129.py",
            "jarvis/app/static/index.html",
        ),
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
        "files": (
            "jarvis/apply_developer_mode_self_diagnostics_v0120.py",
            "jarvis/apply_shared_files_and_diagnostics_v0123.py",
            "jarvis/app/main.py",
        ),
    },
}


class DeveloperInvestigationRequest(BaseModel):
    feature: str = Field(default="auto", max_length=80)
    symptom: str = Field(min_length=3, max_length=2000)
    browser_evidence: dict[str, Any] = Field(default_factory=dict)


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


def developer_runtime_tools() -> list[dict[str, Any]]:
    if not developer_mode_enabled():
        return []
    return [{
        "type": "function",
        "name": "investigate_zbrano_feature",
        "description": (
            "Run a targeted, read-only investigation of a reported ZBRANO feature failure. "
            "Use this whenever the user says a ZBRANO feature is broken, even when general "
            "diagnostics are healthy. Return evidence and fault boundaries before proposing code changes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "feature": {
                    "type": "string",
                    "description": "Feature name such as shared_files, attachments, new_chat, plugin_catalog, plugins, entities, settings, voice, workshop_memory, or developer.",
                },
                "symptom": {
                    "type": "string",
                    "description": "Exact observed behavior, reproduction steps, and expected behavior supplied by the user.",
                },
            },
            "required": ["feature", "symptom"],
            "additionalProperties": False,
        },
        "strict": True,
    }]


async def investigate_zbrano_feature(
    feature: str,
    symptom: str,
    browser_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not developer_mode_enabled():
        raise RuntimeError("Developer Mode must be enabled before investigating ZBRANO itself")

    feature_key = _resolve_developer_feature(feature, symptom)
    spec = DEVELOPER_FEATURE_SPECS[feature_key]
    diagnostics = await developer_diagnostics()
    evidence = []
    terms = tuple(str(term).lower() for term in spec["terms"])
    for check in diagnostics.get("checks", []):
        name = str(check.get("name") or "")
        if any(term in name.lower() for term in terms):
            evidence.append({
                "source": "server_diagnostic",
                "name": name,
                "status": check.get("status") or ("operational" if check.get("ok") else "failed"),
                "detail": check.get("detail") or "",
                "category": check.get("category") or "",
                "repair_hint": check.get("repair_hint") or "",
            })

    runtime = browser_evidence if isinstance(browser_evidence, dict) else {}
    browser_errors = [str(item)[:500] for item in runtime.get("errors", []) if str(item).strip()][:10]
    controller = runtime.get("controller") if isinstance(runtime.get("controller"), dict) else {}
    controls = runtime.get("controls") if isinstance(runtime.get("controls"), dict) else {}
    if runtime:
        evidence.append({
            "source": "browser_runtime",
            "name": f"{spec['title']} browser evidence",
            "status": "failed" if browser_errors or controller.get("lastActionOk") is False or controller.get("lastUploadOk") is False else "wired",
            "detail": json.dumps({
                "errors": browser_errors,
                "controller": controller,
                "controls": controls,
                "location": str(runtime.get("location") or "")[:300],
            }, ensure_ascii=False),
            "category": "browser",
            "repair_hint": "Trace the captured controller error and the last failed action through its API request and response.",
        })

    failed = [item for item in evidence if item.get("status") == "failed"]
    degraded = [item for item in evidence if item.get("status") == "degraded"]
    runtime_failure = bool(browser_errors or controller.get("lastActionOk") is False or controller.get("lastUploadOk") is False)
    general_checks_healthy = not failed and not degraded

    if failed or runtime_failure:
        status = "failed"
        fault_layers = sorted({str(item.get("category") or item.get("source")) for item in failed})
        likely_fault_boundary = ", ".join(fault_layers) or "browser runtime/controller"
        summary = f"Targeted evidence reproduced or detected a failure in {spec['title']}."
    elif degraded:
        status = "degraded"
        likely_fault_boundary = ", ".join(sorted({str(item.get("category") or "integration") for item in degraded}))
        summary = f"{spec['title']} is available but targeted evidence found degraded dependencies."
    else:
        status = "inconclusive"
        likely_fault_boundary = "unreproduced browser sequence, transient state, or behavior not covered by the current adapter"
        summary = (
            f"Targeted checks for {spec['title']} passed, but the reported symptom remains valid and was not reproduced. "
            "Do not close the issue from green diagnostics alone."
        )

    repair_plan = [
        f"Reproduce exactly: {symptom.strip()}",
        f"Trace layers in order: {' -> '.join(spec['layers'])}",
        "Inspect the relevant generated runtime and repository patch-chain source before editing.",
        "Add a regression test that fails for the reported behavior, then implement the smallest repair.",
        "Build an isolated candidate and rerun targeted plus full diagnostics before requesting repository approval.",
    ]
    if not runtime:
        repair_plan.insert(1, "Collect browser controller state, console errors, and the failing request/response during reproduction.")

    return {
        "feature": feature_key,
        "title": spec["title"],
        "reported_symptom": symptom.strip(),
        "status": status,
        "summary": summary,
        "general_checks_healthy": general_checks_healthy,
        "likely_fault_boundary": likely_fault_boundary,
        "evidence": evidence,
        "relevant_files": list(spec["files"]),
        "repair_plan": repair_plan,
        "automatic_changes_made": False,
        "repository_writes_require_approval": True,
        "deployment": "manual",
    }


@app.get("/api/developer/features")
async def developer_features():
    return {
        "features": [
            {"id": key, "title": spec["title"], "layers": list(spec["layers"])}
            for key, spec in DEVELOPER_FEATURE_SPECS.items()
        ]
    }


@app.post("/api/developer/investigate")
async def developer_investigate(request: DeveloperInvestigationRequest):
    if not developer_mode_enabled():
        raise HTTPException(status_code=403, detail="Enable Developer Mode before running an investigation")
    return await investigate_zbrano_feature(
        request.feature,
        request.symptom,
        request.browser_evidence,
    )
'''
    text = text.replace(route_marker, investigation_backend + route_marker, 1)

    allowed = '    allowed_names = {tool["name"] for tool in WORKSHOP_TOOLS}'
    require(text, allowed, "tool allow-list")
    text = text.replace(
        allowed,
        '    allowed_names = {tool["name"] for tool in WORKSHOP_TOOLS + developer_runtime_tools()}',
        1,
    )

    handler = '''                elif name == "save_general_instruction":
                    result = append_general_instruction(arguments["instruction"])'''
    require(text, handler, "tool execution insertion point")
    text = text.replace(
        handler,
        '''                elif name == "investigate_zbrano_feature":
                    result = await investigate_zbrano_feature(
                        arguments["feature"],
                        arguments["symptom"],
                    )
                elif name == "save_general_instruction":
                    result = append_general_instruction(arguments["instruction"])''',
        1,
    )

    tool_expression = "WORKSHOP_TOOLS + active_mcp_tools()"
    require(text, tool_expression, "Responses API tool expression")
    text = text.replace(
        tool_expression,
        "WORKSHOP_TOOLS + developer_runtime_tools() + active_mcp_tools()",
    )

    instruction = "Do not claim a Home Assistant deployment or restart occurred unless the running system confirms it."
    require(text, instruction, "Developer Mode system instruction")
    text = text.replace(
        instruction,
        "When the user reports that a ZBRANO feature is not working, call investigate_zbrano_feature even if general diagnostics are healthy. Treat an inconclusive result as an open defect: use its evidence and relevant_files to inspect the repository with read tools, identify a supported root cause, add a regression test, and propose a versioned repair. Never invent successful reproduction.\n" + instruction,
        1,
    )

    text = text.replace('version="0.12.3"', 'version="0.12.4"')
    text = text.replace('"version": "0.12.3"', '"version": "0.12.4"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    warning = '<div class="developer-warning">Developer Mode never bypasses GitHub approval. Repository changes can be prepared here; Home Assistant deployment remains explicit.</div>'
    require(text, warning, "Developer warning")
    investigator = r'''
      <div class="developer-investigator">
        <h3>Targeted investigation</h3>
        <p class="muted">Describe a broken feature even when general diagnostics are green. ZBRANO will trace targeted layers and preserve approval boundaries.</p>
        <div class="developer-investigation-form">
          <label><span>Feature</span><select id="developer-feature"><option value="auto">Detect automatically</option></select></label>
          <label class="developer-symptom"><span>Observed problem</span><textarea id="developer-symptom" rows="3" placeholder="Example: I select files in Shared Files and press Delete selected, but nothing happens."></textarea></label>
          <button id="developer-investigate" type="button">Investigate feature</button>
        </div>
        <p id="developer-investigation-summary" class="muted">No targeted investigation run yet.</p>
        <div id="developer-investigation-results" class="developer-investigation-results"></div>
      </div>'''
    text = text.replace(warning, warning + investigator, 1)

    style_close = text.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.4 patch missing: style close")
    css = r'''
    .developer-investigator{border:1px solid var(--line);border-radius:8px;padding:.75rem;background:var(--surface);display:grid;gap:.6rem}
    .developer-investigator h3{margin:0}
    .developer-investigation-form{display:grid;grid-template-columns:minmax(180px,.4fr) minmax(260px,1fr) auto;gap:.6rem;align-items:end}
    .developer-investigation-form label{display:grid;gap:.3rem}
    .developer-investigation-form textarea{resize:vertical;min-height:4.5rem}
    .developer-investigation-results{display:grid;gap:.45rem}
    .developer-investigation-result{border-left:3px solid var(--cyan);padding:.45rem .6rem;background:rgba(0,0,0,.12)}
    .developer-investigation-result.failed{border-left-color:#ff6b6b}.developer-investigation-result.degraded{border-left-color:#ffc857}
    .developer-investigation-result strong{display:block;margin-bottom:.2rem}
    @media(max-width:800px){.developer-investigation-form{grid-template-columns:1fr}.developer-investigation-form button{width:100%}}
'''
    text = text[:style_close] + css + text[style_close:]

    runtime = r'''
<script id="zbrano-v0124-investigation-engine">
(() => {
  const feature = document.getElementById("developer-feature");
  const symptom = document.getElementById("developer-symptom");
  const run = document.getElementById("developer-investigate");
  const summary = document.getElementById("developer-investigation-summary");
  const results = document.getElementById("developer-investigation-results");
  if (!feature || !symptom || !run || !summary || !results) return;

  const runtimeErrors = [];
  const remember = value => {
    const message = String(value?.message || value || "Unknown browser error");
    if (!runtimeErrors.includes(message)) runtimeErrors.push(message);
    while (runtimeErrors.length > 10) runtimeErrors.shift();
  };
  window.addEventListener("error", event => remember(event.message));
  window.addEventListener("unhandledrejection", event => remember(event.reason));

  async function loadFeatures() {
    const response = await fetch("api/developer/features", {cache: "no-store"});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    for (const item of data.features || []) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.title;
      feature.appendChild(option);
    }
  }

  function controllerEvidence(featureId) {
    if (featureId === "attachments") {
      const controller = window.zbranoAttachmentController || {};
      return {ready: Boolean(controller.ready), lastUploadOk: controller.lastUploadOk, lastError: controller.lastError || ""};
    }
    if (featureId === "shared_files") {
      const controller = window.zbranoSharedFilesController || {};
      return {ready: Boolean(controller.ready), lastAction: controller.lastAction || "", lastActionOk: controller.lastActionOk, lastError: controller.lastError || ""};
    }
    return {};
  }

  function collectBrowserEvidence(featureId) {
    const controlIds = {
      attachments: ["attach-file", "attachment-input", "chat-attachments"],
      shared_files: ["shared-use", "shared-delete", "shared-file-rows"],
      new_chat: ["new-chat-button", "chat-form"],
      plugin_catalog: ["plugins-tab", "catalog-results"],
      plugins: ["plugins-tab", "plugin-list"],
      entities: ["entities-tab", "entities-panel"],
      settings: ["settings-tab", "settings-panel"],
      voice: ["mic-button", "stop-button"],
      developer: ["developer-tab", "developer-panel"],
    };
    const controls = {};
    for (const id of controlIds[featureId] || []) controls[id] = Boolean(document.getElementById(id));
    return {
      errors: [...runtimeErrors],
      controller: controllerEvidence(featureId),
      controls,
      location: window.location.href,
      user_agent: navigator.userAgent,
    };
  }

  function render(data) {
    results.replaceChildren();
    for (const item of data.evidence || []) {
      const row = document.createElement("div");
      row.className = `developer-investigation-result ${item.status || ""}`;
      const title = document.createElement("strong");
      title.textContent = `${item.name} · ${item.status}`;
      const detail = document.createElement("div");
      detail.className = "muted";
      detail.textContent = item.detail || "";
      row.append(title, detail);
      results.appendChild(row);
    }
    const files = (data.relevant_files || []).join(", ");
    const boundary = data.likely_fault_boundary || "unknown";
    summary.textContent = `${data.summary || "Investigation complete"} Fault boundary: ${boundary}. Relevant files: ${files}`;
  }

  async function investigate() {
    const report = symptom.value.trim();
    if (report.length < 3) {
      summary.textContent = "Describe the observed problem before investigating.";
      symptom.focus();
      return;
    }
    run.disabled = true;
    summary.textContent = "Running targeted investigation…";
    results.replaceChildren();
    try {
      const featureId = feature.value;
      const response = await fetch("api/developer/investigate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          feature: featureId,
          symptom: report,
          browser_evidence: collectBrowserEvidence(featureId),
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      render(data);
      window.zbranoInvestigationEngine.lastResult = data;
    } catch (error) {
      summary.textContent = `Investigation failed: ${error.message || error}`;
    } finally {
      run.disabled = false;
    }
  }

  window.zbranoInvestigationEngine = {
    ready: true,
    investigate,
    collectBrowserEvidence,
    runtimeErrors,
    lastResult: null,
  };
  run.addEventListener("click", investigate);
  loadFeatures().catch(error => { summary.textContent = `Feature list failed: ${error.message || error}`; });
})();
</script>
'''
    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.4 patch missing: body close")
    text = text[:body_close] + runtime + text[body_close:]
    text = text.replace("HUD 0.12.3", "HUD 0.12.4")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    missing = []
    for marker in (
        'version="0.12.4"',
        "DEVELOPER_FEATURE_SPECS",
        "async def investigate_zbrano_feature(",
        'name": "investigate_zbrano_feature"',
        'developer_runtime_tools() + active_mcp_tools()',
        '@app.post("/api/developer/investigate")',
        '@app.get("/api/developer/features")',
        '"automatic_changes_made": False',
        '"repository_writes_require_approval": True',
        "Do not close the issue from green diagnostics alone",
    ):
        if marker not in main:
            missing.append(marker)
    for marker in (
        'id="developer-investigate"',
        'id="developer-symptom"',
        'id="zbrano-v0124-investigation-engine"',
        "collectBrowserEvidence",
        'fetch("api/developer/investigate"',
        "HUD 0.12.4",
    ):
        if marker not in index:
            missing.append(marker)
    if missing:
        raise RuntimeError("ZBRANO v0.12.4 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
