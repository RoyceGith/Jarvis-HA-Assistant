from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.21 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


def patch_backend(backend: str) -> str:
    defaults_marker = '    "voice_volume": 0.9,\n}'
    backend = replace_once(
        backend,
        defaults_marker,
        '    "voice_volume": 0.9,\n    "auto_sync_releases_to_workshop_memory": True,\n}',
        "release sync preference default",
    )

    model_marker = '    voice_volume: float = Field(default=0.9, ge=0.0, le=1.0)'
    backend = replace_once(
        backend,
        model_marker,
        model_marker + '\n    auto_sync_releases_to_workshop_memory: bool = True',
        "release sync settings validation",
    )

    save_marker = '                "voice_volume": request.voice_volume,\n            }'
    backend = replace_once(
        backend,
        save_marker,
        '                "voice_volume": request.voice_volume,\n'
        '                "auto_sync_releases_to_workshop_memory": request.auto_sync_releases_to_workshop_memory,\n'
        '            }',
        "release sync preference persistence",
    )

    startup_marker = '@app.on_event("startup")\nasync def start_ha_websocket() -> None:'
    release_sync_backend = r'''RELEASE_MANIFEST_PATH = APP_DIR.parent / "release_manifest.json"
RELEASE_SYNC_STATE_PATH = Path("/data/zbrano_release_sync.json")
RELEASE_SYNC_TASK: asyncio.Task | None = None
RELEASE_SYNC_STATUS: dict[str, Any] = {
    "state": "pending",
    "version": None,
    "target": "ZBRANO Workshop Assistant/Release and Change Log.md",
    "attempts": 0,
    "last_error": None,
    "last_success_at": None,
    "already_present": False,
}


def restore_release_sync_status() -> None:
    try:
        stored = json.loads(RELEASE_SYNC_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(stored, dict):
        return
    for key in ("version", "state", "last_error", "last_success_at", "already_present"):
        if key in stored:
            RELEASE_SYNC_STATUS[key] = stored[key]


restore_release_sync_status()


def load_release_manifest() -> dict[str, Any]:
    try:
        manifest = json.loads(RELEASE_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Release manifest unavailable: {exc}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("Release manifest must contain a JSON object")
    version = str(manifest.get("version") or "").strip()
    if version != str(app.version):
        raise RuntimeError(f"Release manifest version {version or 'missing'} does not match runtime {app.version}")
    return manifest


def release_sync_enabled() -> bool:
    return bool(load_preferences().get("auto_sync_releases_to_workshop_memory", True))


def release_sync_status() -> dict[str, Any]:
    status = dict(RELEASE_SYNC_STATUS)
    status["enabled"] = release_sync_enabled()
    status["task_active"] = bool(RELEASE_SYNC_TASK and not RELEASE_SYNC_TASK.done())
    return status


def persist_release_sync_status() -> None:
    payload = {
        "version": RELEASE_SYNC_STATUS.get("version"),
        "state": RELEASE_SYNC_STATUS.get("state"),
        "last_error": RELEASE_SYNC_STATUS.get("last_error"),
        "last_success_at": RELEASE_SYNC_STATUS.get("last_success_at"),
        "already_present": RELEASE_SYNC_STATUS.get("already_present", False),
    }
    try:
        RELEASE_SYNC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = RELEASE_SYNC_STATE_PATH.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(RELEASE_SYNC_STATE_PATH)
    except OSError:
        pass


def release_marker(version: str) -> str:
    return f"<!-- zbrano-release:{version} -->"


def render_release_entry(manifest: dict[str, Any]) -> str:
    version = str(manifest["version"])
    installed_at = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    lines = [
        release_marker(version),
        f"### v{version} — Installed {installed_at}",
        "",
        f"- **Runtime status:** Started successfully as v{version}",
        f"- **Source:** {str(manifest.get('source') or 'ZBRANO release manifest')}",
        f"- **Summary:** {str(manifest.get('summary') or 'ZBRANO application update')}",
    ]
    for heading, key in (("New features", "features"), ("Fixes and reliability", "fixes"), ("Validation", "validation")):
        values = [str(item).strip() for item in manifest.get(key, []) if str(item).strip()]
        if values:
            lines.extend(("", f"#### {heading}"))
            lines.extend(f"- {item}" for item in values)
    return "\n".join(lines).rstrip()


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


async def synchronize_release_to_workshop_memory_once() -> dict[str, Any]:
    if not release_sync_enabled():
        RELEASE_SYNC_STATUS.update({"state": "disabled", "last_error": None})
        persist_release_sync_status()
        return release_sync_status()

    manifest = load_release_manifest()
    version = str(manifest["version"])
    project = str(manifest.get("project") or "ZBRANO Workshop Assistant")
    note = str(manifest.get("note") or "Release and Change Log.md")
    relative_path = f"{project}/{note}"
    RELEASE_SYNC_STATUS.update({
        "state": "synchronizing",
        "version": version,
        "target": relative_path,
        "last_error": None,
        "already_present": False,
    })

    current = await call_workshop_memory_tool("read_project_note", {"relative_path": relative_path})
    content = str(current.get("content") or "")
    marker = release_marker(version)
    if marker in content:
        RELEASE_SYNC_STATUS.update({
            "state": "synchronized",
            "last_success_at": time.time(),
            "already_present": True,
        })
        persist_release_sync_status()
        return release_sync_status()

    updated = insert_release_history(content, render_release_entry(manifest))
    result = await call_workshop_memory_tool(
        "write_project_note",
        {
            "relative_path": relative_path,
            "content": updated,
            "mode": "replace",
            "create_folders": False,
        },
    )
    status = str(result.get("status") or "")
    if status not in {"replaced", "updated", "ok"}:
        raise RuntimeError(f"Workshop Memory returned an unexpected release write status: {status or 'missing'}")
    RELEASE_SYNC_STATUS.update({
        "state": "synchronized",
        "last_success_at": time.time(),
        "last_error": None,
        "already_present": False,
    })
    persist_release_sync_status()
    return release_sync_status()


async def release_sync_worker() -> None:
    delays = (0, 10, 30, 120)
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            await asyncio.sleep(delay)
        RELEASE_SYNC_STATUS["attempts"] = attempt
        try:
            await synchronize_release_to_workshop_memory_once()
            return
        except asyncio.CancelledError:
            raise
        except (MCPError, httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
            RELEASE_SYNC_STATUS.update({
                "state": "retrying" if attempt < len(delays) else "failed",
                "last_error": str(exc)[:1000],
            })
            persist_release_sync_status()


def schedule_release_sync() -> asyncio.Task | None:
    global RELEASE_SYNC_TASK
    if not release_sync_enabled():
        RELEASE_SYNC_STATUS.update({"state": "disabled", "last_error": None})
        persist_release_sync_status()
        return None
    if RELEASE_SYNC_TASK is None or RELEASE_SYNC_TASK.done():
        RELEASE_SYNC_TASK = asyncio.create_task(release_sync_worker(), name="zbrano-release-memory-sync")
    return RELEASE_SYNC_TASK


@app.get("/api/release-memory-sync")
async def get_release_memory_sync() -> dict[str, Any]:
    return release_sync_status()


@app.post("/api/release-memory-sync/retry")
async def retry_release_memory_sync() -> dict[str, Any]:
    if not release_sync_enabled():
        raise HTTPException(status_code=409, detail="Automatic release synchronization is disabled in Settings")
    schedule_release_sync()
    return {**release_sync_status(), "scheduled": True}


'''
    backend = replace_once(
        backend,
        startup_marker,
        release_sync_backend + startup_marker,
        "release synchronization service",
    )

    endpoint_probe = '''        await probe(
            "Conversations API operational",'''
    release_probe = '''        await probe(
            "Release memory synchronization",
            "/api/release-memory-sync",
            lambda payload: (
                (
                    "operational" if payload.get("state") in {"synchronized", "disabled"}
                    else "degraded" if payload.get("state") in {"pending", "synchronizing", "retrying"}
                    else "failed"
                ) if isinstance(payload, dict) else "failed",
                (
                    f"state={payload.get('state')}; version={payload.get('version') or app.version}; "
                    f"enabled={payload.get('enabled')}; target={payload.get('target')}"
                    if isinstance(payload, dict) else "invalid release synchronization payload"
                ),
            ),
            "workshop_memory",
            repair_hint="Verify Workshop Memory connectivity, the ZBRANO project name, and Release and Change Log.md.",
        )

'''
    backend = replace_once(backend, endpoint_probe, release_probe + endpoint_probe, "release sync diagnostic")

    connection_marker = '            "cache_entries": len(MCP_TOOL_CACHE),\n        },'
    backend = replace_once(
        backend,
        connection_marker,
        '            "cache_entries": len(MCP_TOOL_CACHE),\n'
        '            "release_sync": release_sync_status(),\n'
        '        },',
        "connection status release sync",
    )

    startup_schedule_marker = '''    with contextlib.suppress(MCPError, httpx.HTTPError, OSError, RuntimeError):
        await select_workshop_memory_endpoint(force=True)

    if not SUPERVISOR_TOKEN:'''
    backend = replace_once(
        backend,
        startup_schedule_marker,
        '''    with contextlib.suppress(MCPError, httpx.HTTPError, OSError, RuntimeError):
        await select_workshop_memory_endpoint(force=True)
    schedule_release_sync()

    if not SUPERVISOR_TOKEN:''',
        "startup release synchronization",
    )

    shutdown_global = '    global PLUGIN_OAUTH_REFRESH_TASK\n    if PLUGIN_OAUTH_REFRESH_TASK is not None:'
    backend = replace_once(
        backend,
        shutdown_global,
        '''    global PLUGIN_OAUTH_REFRESH_TASK, RELEASE_SYNC_TASK
    if RELEASE_SYNC_TASK is not None:
        RELEASE_SYNC_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await RELEASE_SYNC_TASK
        RELEASE_SYNC_TASK = None
    if PLUGIN_OAUTH_REFRESH_TASK is not None:''',
        "release synchronization shutdown",
    )

    settings_return = '''    return {
        "saved": True,
        "general_instructions": instructions,
        "elevenlabs_voice_settings": voice,
        "preferences": preferences,
    }'''
    backend = replace_once(
        backend,
        settings_return,
        '''    if preferences["auto_sync_releases_to_workshop_memory"]:
        schedule_release_sync()
    elif RELEASE_SYNC_TASK is not None and not RELEASE_SYNC_TASK.done():
        RELEASE_SYNC_TASK.cancel()
    return {
        "saved": True,
        "general_instructions": instructions,
        "elevenlabs_voice_settings": voice,
        "preferences": preferences,
        "release_sync": release_sync_status(),
    }''',
        "settings-triggered release synchronization",
    )

    backend = backend.replace('version="0.12.20"', 'version="0.12.21"')
    backend = backend.replace('"version": "0.12.20"', '"version": "0.12.21"')
    return backend


def patch_frontend(frontend: str) -> str:
    memory_tab = '      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="memory">Memory</button>'
    frontend = replace_once(
        frontend,
        memory_tab,
        memory_tab + '\n      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="updates">Updates</button>',
        "updates settings tab",
    )

    save_actions = '''    <div class="settings-actions">
      <button id="save-settings" type="button">Save All Settings</button>'''
    release_card = '''    <div class="settings-card" data-settings-category="updates" hidden>
      <h2>RELEASE MEMORY</h2>
      <p>Keep the ZBRANO Workshop Assistant project synchronized with every successfully installed version.</p>
      <label class="toggle-row"><input id="release-memory-auto-sync" type="checkbox"> Automatically sync installed releases to Workshop Memory</label>
      <p class="setting-note">Enabling this grants standing authorization only for ZBRANO's own Release and Change Log.md. Existing content is preserved and Workshop Memory creates a backup before replacement.</p>
      <div class="release-sync-status" id="release-memory-sync-status" role="status" aria-live="polite">Checking synchronization status…</div>
      <div class="settings-actions"><button id="release-memory-sync-retry" type="button">Sync Current Release Now</button></div>
    </div>
'''
    frontend = replace_once(frontend, save_actions, release_card + save_actions, "release memory settings card")

    style_close = frontend.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.21 patch missing: style close")
    css = r'''
    .release-sync-status {
      margin-top: .9rem;
      padding: .75rem .85rem;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: color-mix(in srgb, var(--surface-strong) 82%, transparent);
      color: var(--text-muted);
      overflow-wrap: anywhere;
    }
    .release-sync-status[data-state="synchronized"] { border-color: rgba(92,236,255,.38); color: var(--cyan); }
    .release-sync-status[data-state="failed"] { border-color: rgba(255,120,110,.42); color: #ffb4ad; }
'''
    frontend = frontend[:style_close] + css + frontend[style_close:]

    reduced_const = 'const reducedMotionSetting = document.getElementById("reduced-motion");'
    frontend = replace_once(
        frontend,
        reduced_const,
        reduced_const + r'''
const releaseMemoryAutoSync = document.getElementById("release-memory-auto-sync");
const releaseMemorySyncStatus = document.getElementById("release-memory-sync-status");
const releaseMemorySyncRetry = document.getElementById("release-memory-sync-retry");''',
        "release memory controls",
    )

    load_function = 'async function loadSettings() {'
    release_js = r'''function renderReleaseSyncStatus(status = {}) {
  const state = String(status.state || "pending");
  releaseMemorySyncStatus.dataset.state = state;
  const version = status.version ? `v${status.version}` : "current release";
  const detail = status.last_error ? ` · ${status.last_error}` : "";
  releaseMemorySyncStatus.textContent = status.enabled === false
    ? "Automatic release synchronization is disabled."
    : `${version} · ${state}${status.already_present ? " · already recorded" : ""}${detail}`;
}

async function refreshReleaseSyncStatus() {
  try {
    const response = await fetch("api/release-memory-sync", {cache: "no-store"});
    const status = await response.json();
    if (!response.ok) throw new Error(status.detail || `HTTP ${response.status}`);
    renderReleaseSyncStatus(status);
  } catch (error) {
    renderReleaseSyncStatus({state: "failed", last_error: error.message || String(error)});
  }
}

releaseMemorySyncRetry.addEventListener("click", async () => {
  releaseMemorySyncRetry.disabled = true;
  releaseMemorySyncStatus.textContent = "Scheduling release synchronization…";
  try {
    const response = await fetch("api/release-memory-sync/retry", {method: "POST"});
    const status = await response.json();
    if (!response.ok) throw new Error(status.detail || `HTTP ${response.status}`);
    renderReleaseSyncStatus(status);
    window.setTimeout(refreshReleaseSyncStatus, 1500);
  } catch (error) {
    renderReleaseSyncStatus({state: "failed", last_error: error.message || String(error)});
  } finally {
    releaseMemorySyncRetry.disabled = false;
  }
});

'''
    frontend = replace_once(frontend, load_function, release_js + load_function, "release sync frontend controller")

    load_pref = '    reducedMotionSetting.checked = Boolean(jarvisPreferences.reduced_motion);'
    frontend = replace_once(
        frontend,
        load_pref,
        '    releaseMemoryAutoSync.checked = jarvisPreferences.auto_sync_releases_to_workshop_memory !== false;\n' + load_pref,
        "release sync preference load",
    )

    load_finish = '''    saveVoiceSettings();
    settingsSaveState.textContent = "";'''
    frontend = replace_once(
        frontend,
        load_finish,
        '''    saveVoiceSettings();
    await refreshReleaseSyncStatus();
    settingsSaveState.textContent = "";''',
        "release sync status load",
    )

    save_pref = '        voice_volume: Number(voiceVolume.value),\n      }),'
    frontend = replace_once(
        frontend,
        save_pref,
        '        voice_volume: Number(voiceVolume.value),\n'
        '        auto_sync_releases_to_workshop_memory: releaseMemoryAutoSync.checked,\n'
        '      }),',
        "release sync preference save",
    )

    save_finish = '''    saveVoiceSettings();
    settingsSaveState.textContent = "Saved. New replies and speech will use these settings.";'''
    frontend = replace_once(
        frontend,
        save_finish,
        '''    saveVoiceSettings();
    renderReleaseSyncStatus(data.release_sync || {});
    settingsSaveState.textContent = "Saved. New replies, speech, and release synchronization will use these settings.";''',
        "release sync saved status",
    )

    frontend = frontend.replace("HUD 0.12.20", "HUD 0.12.21")
    return frontend


def verify() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    for marker in (
        'version="0.12.21"',
        '"version": "0.12.21"',
        "def insert_release_history(",
        "def restore_release_sync_status(",
        'release_marker(version)',
        '"write_project_note"',
        '"mode": "replace"',
        "schedule_release_sync()",
        '@app.get("/api/release-memory-sync")',
        '@app.post("/api/release-memory-sync/retry")',
        '"auto_sync_releases_to_workshop_memory": True',
        "Release memory synchronization",
    ):
        require(backend, marker, marker)
    for marker in (
        "HUD 0.12.21",
        'data-settings-target="updates"',
        'data-settings-category="updates" hidden',
        'id="release-memory-auto-sync"',
        'id="release-memory-sync-status"',
        'id="release-memory-sync-retry"',
        "refreshReleaseSyncStatus",
        "auto_sync_releases_to_workshop_memory",
    ):
        require(frontend, marker, marker)


def main() -> None:
    backend = patch_backend(MAIN.read_text(encoding="utf-8"))
    frontend = patch_frontend(INDEX.read_text(encoding="utf-8"))
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")
    verify()


if __name__ == "__main__":
    main()
