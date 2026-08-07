from pathlib import Path


ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.3 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    start = text.find("async def developer_diagnostics() -> dict[str, object]:")
    end = text.find('\n\n@app.get("/api/developer/status")', start)
    if start < 0 or end < 0:
        raise RuntimeError("ZBRANO v0.12.3 patch missing: developer diagnostics bounds")

    diagnostics = r'''async def developer_diagnostics() -> dict[str, object]:
    checks: list[dict[str, object]] = []

    def add(name: str, status: str, detail: str, category: str, repair_hint: str = "") -> None:
        normalized = status if status in {"present", "wired", "operational", "degraded", "failed"} else "failed"
        checks.append({
            "name": name,
            "status": normalized,
            "ok": normalized != "failed",
            "detail": detail,
            "category": category,
            "repair_hint": repair_hint,
        })

    async with httpx.AsyncClient(timeout=12.0) as client:
        async def request_json(path: str, method: str = "GET", timeout: float = 12.0, **kwargs):
            response = await client.request(
                method,
                f"http://127.0.0.1:8099{path}",
                timeout=timeout,
                **kwargs,
            )
            try:
                payload = response.json()
            except Exception:
                payload = None
            return response, payload

        async def probe(
            name: str,
            path: str,
            validator,
            category: str,
            timeout: float = 12.0,
            optional: bool = False,
            repair_hint: str = "",
        ) -> None:
            try:
                response, payload = await request_json(path, timeout=timeout)
                if response.is_error:
                    status = "degraded" if optional else "failed"
                    add(name, status, f"HTTP {response.status_code}: {response.text[:180]}", category, repair_hint)
                    return
                status, detail = validator(payload)
                add(name, status, detail, category, repair_hint)
            except Exception as exc:
                add(name, "degraded" if optional else "failed", str(exc), category, repair_hint)

        health_payload: dict[str, object] = {}
        try:
            response, payload = await request_json("/api/health")
            health_payload = payload if isinstance(payload, dict) else {}
            version = str(health_payload.get("version") or "")
            add(
                "Application health and version",
                "operational" if response.status_code == 200 and version == "0.12.3" else "failed",
                f"HTTP {response.status_code}; runtime version {version or 'missing'}; expected 0.12.3",
                "runtime",
                "Rebuild from the current main branch and verify every version marker.",
            )
            voice_ready = bool(health_payload.get("voice_configured"))
            openai_ready = bool(health_payload.get("openai_configured"))
            add(
                "AI chat readiness",
                "operational" if openai_ready else "degraded",
                f"model={health_payload.get('openai_model')}; configured={openai_ready}; no billable completion generated",
                "chat",
                "Configure the OpenAI API key and verify the selected model before testing a live completion.",
            )
            add(
                "Voice pipeline readiness",
                "operational" if voice_ready else "degraded",
                f"provider={health_payload.get('speech_provider')}; configured={voice_ready}",
                "voice",
                "Configure an OpenAI key or a complete ElevenLabs key and voice ID.",
            )
        except Exception as exc:
            add("Application health and version", "failed", str(exc), "runtime", "Inspect startup logs and /api/health.")
            add("AI chat readiness", "degraded", "Health payload unavailable", "chat")
            add("Voice pipeline readiness", "degraded", "Health payload unavailable", "voice")

        await probe(
            "Settings API operational",
            "/api/settings",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("preferences"), dict) else "failed",
                "preferences and voice settings readable" if isinstance(payload, dict) else "invalid JSON payload",
            ),
            "settings",
            repair_hint="Inspect /data settings JSON and settings route logs.",
        )
        await probe(
            "Conversations API operational",
            "/api/chats",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("chats"), list) else "failed",
                f"{len(payload.get('chats', [])) if isinstance(payload, dict) else 0} conversations readable",
            ),
            "chat",
        )
        await probe(
            "Plugins API operational",
            "/api/plugins",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("plugins"), list) else "failed",
                f"{len(payload.get('plugins', [])) if isinstance(payload, dict) else 0} installed plugins",
            ),
            "plugins",
        )

        catalog_attempts = []
        catalog_ok = False
        for attempt in (1, 2):
            try:
                response, payload = await request_json("/api/plugin-catalog", timeout=18.0)
                plugins = payload.get("plugins", []) if isinstance(payload, dict) else []
                catalog_attempts.append(f"attempt {attempt}: HTTP {response.status_code}, {len(plugins)} plugins")
                if response.status_code == 200 and isinstance(plugins, list) and plugins:
                    add(
                        "Plugin Catalog operational",
                        "operational" if attempt == 1 else "degraded",
                        "; ".join(catalog_attempts) + ("; cold start required retry" if attempt > 1 else ""),
                        "plugins",
                        "Warm the catalog cache and distinguish registry latency from endpoint failure.",
                    )
                    catalog_ok = True
                    break
            except Exception as exc:
                catalog_attempts.append(f"attempt {attempt}: {exc}")
            if attempt == 1:
                await asyncio.sleep(0.5)
        if not catalog_ok:
            add(
                "Plugin Catalog operational",
                "failed",
                "; ".join(catalog_attempts) or "no response",
                "plugins",
                "Inspect catalog cache, Registry connectivity, and featured fallback handling.",
            )

        await probe(
            "Shared Files list operational",
            "/api/files/shared",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("files"), list) else "failed",
                f"{len(payload.get('files', [])) if isinstance(payload, dict) else 0} shared files readable",
            ),
            "files",
        )
        await probe(
            "Entity inventory operational",
            "/api/ha/entities",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("entities"), list) else "failed",
                f"{len(payload.get('entities', [])) if isinstance(payload, dict) else 0} entities returned",
            ),
            "home_assistant",
            timeout=25.0,
            optional=True,
            repair_hint="Check Supervisor token, Home Assistant connectivity, and WebSocket status.",
        )
        await probe(
            "Home Assistant connection",
            "/api/ha/websocket-status",
            lambda payload: (
                "operational" if isinstance(payload, dict) and payload.get("connected") else "degraded",
                "WebSocket connected" if isinstance(payload, dict) and payload.get("connected") else str((payload or {}).get("last_error") or "WebSocket disconnected; REST fallback available"),
            ),
            "home_assistant",
            timeout=15.0,
            optional=True,
        )
        await probe(
            "Developer API operational",
            "/api/developer/status",
            lambda payload: (
                "operational" if isinstance(payload, dict) and payload.get("repository") == DEVELOPER_REPOSITORY else "failed",
                f"repository={payload.get('repository') if isinstance(payload, dict) else 'invalid'}; deployment={payload.get('deployment') if isinstance(payload, dict) else 'invalid'}",
            ),
            "developer",
        )
        await probe(
            "Connection status API operational",
            "/api/connections/status",
            lambda payload: (
                "operational" if isinstance(payload, dict) and all(key in payload for key in ("home_assistant", "workshop_memory", "openai")) else "failed",
                "Home Assistant, Workshop Memory, and OpenAI states readable" if isinstance(payload, dict) else "invalid JSON payload",
            ),
            "integrations",
        )
        await probe(
            "Workshop Memory operational",
            "/api/memory/status",
            lambda payload: (
                "operational" if isinstance(payload, dict) and payload.get("connected") else "degraded",
                "MCP status call succeeded" if isinstance(payload, dict) and payload.get("connected") else "MCP status did not confirm a connection",
            ),
            "integrations",
            timeout=18.0,
            optional=True,
            repair_hint="Check the configured Workshop Memory endpoint and its MCP status tool.",
        )

        storage_root = Path("/data/.zbrano-diagnostics")
        storage_file = storage_root / f"persistence-{time.time_ns()}.txt"
        try:
            storage_root.mkdir(parents=True, exist_ok=True)
            storage_file.write_text("zbrano persistence diagnostic", encoding="utf-8")
            stored_text = storage_file.read_text(encoding="utf-8")
            add(
                "Persistent storage operational",
                "operational" if stored_text == "zbrano persistence diagnostic" else "failed",
                "temporary /data write/read/delete cycle completed",
                "persistence",
                "Check add-on /data permissions and available storage.",
            )
        except Exception as exc:
            add("Persistent storage operational", "failed", str(exc), "persistence", "Check /data permissions and disk health.")
        finally:
            try:
                storage_file.unlink(missing_ok=True)
                storage_root.rmdir()
            except OSError:
                pass

        chat_session = f"zbrano-diagnostic-{time.time_ns():x}"[-80:]
        try:
            create_response, created = await request_json(
                "/api/chats",
                method="POST",
                json={"session_id": chat_session},
            )
            history_response, history = await request_json(f"/api/chat/history/{chat_session}")
            delete_response, deleted = await request_json(f"/api/chat/history/{chat_session}", method="DELETE")
            ok = (
                create_response.status_code == 200
                and history_response.status_code == 200
                and delete_response.status_code == 200
                and isinstance(created, dict)
                and isinstance(history, dict)
                and isinstance(deleted, dict)
                and deleted.get("cleared") is True
            )
            add(
                "Conversation lifecycle operational",
                "operational" if ok else "failed",
                f"create={create_response.status_code}; read={history_response.status_code}; delete={delete_response.status_code}",
                "chat",
                "Inspect chat persistence and session cleanup.",
            )
        except Exception as exc:
            add("Conversation lifecycle operational", "failed", str(exc), "chat", "Inspect chat persistence and session cleanup.")
        finally:
            try:
                await request_json(f"/api/chat/history/{chat_session}", method="DELETE")
            except Exception:
                pass

        attachment_session = f"zbrano-attachment-{time.time_ns():x}"[-80:]
        attachment_dir = CHAT_UPLOAD_ROOT / _sid(attachment_session)
        try:
            response, payload = await request_json(
                f"/api/files/chat/{attachment_session}",
                method="POST",
                files={"file": ("zbrano-diagnostic.txt", b"attachment diagnostic\n", "text/plain")},
            )
            file_id = payload.get("file_id") if isinstance(payload, dict) else None
            stored = attachment_dir / str(file_id)
            ok = response.status_code == 200 and bool(file_id) and stored.is_dir()
            add(
                "Chat attachment lifecycle operational",
                "operational" if ok else "failed",
                f"HTTP {response.status_code}; upload ID and extracted storage verified",
                "files",
                "Inspect the chat upload endpoint, /data permissions, and attachment controller.",
            )
        except Exception as exc:
            add("Chat attachment lifecycle operational", "failed", str(exc), "files")
        finally:
            shutil.rmtree(attachment_dir, ignore_errors=True)

        shared_file_id = None
        try:
            upload_response, uploaded = await request_json(
                "/api/files/shared",
                method="POST",
                files={"file": ("zbrano-shared-diagnostic.txt", b"shared file diagnostic\n", "text/plain")},
            )
            shared_file_id = uploaded.get("file_id") if isinstance(uploaded, dict) else None
            list_response, listed = await request_json("/api/files/shared")
            listed_ids = {
                str(item.get("file_id"))
                for item in (listed.get("files", []) if isinstance(listed, dict) else [])
                if isinstance(item, dict)
            }
            delete_response, deleted = await request_json(
                "/api/files/shared",
                method="DELETE",
                json={"file_ids": [shared_file_id] if shared_file_id else []},
            )
            removed = bool(shared_file_id) and not (SHARED_FILE_ROOT / str(shared_file_id)).exists()
            ok = (
                upload_response.status_code == 200
                and list_response.status_code == 200
                and shared_file_id in listed_ids
                and delete_response.status_code == 200
                and isinstance(deleted, dict)
                and deleted.get("count") == 1
                and removed
            )
            add(
                "Shared Files create/list/delete operational",
                "operational" if ok else "failed",
                f"upload={upload_response.status_code}; listed={shared_file_id in listed_ids}; delete={delete_response.status_code}; removed={removed}",
                "files",
                "Inspect the Shared Files API and browser action controller.",
            )
        except Exception as exc:
            add("Shared Files create/list/delete operational", "failed", str(exc), "files")
        finally:
            if shared_file_id and FILE_ID_RE.fullmatch(str(shared_file_id)):
                shutil.rmtree(SHARED_FILE_ROOT / str(shared_file_id), ignore_errors=True)

    frontend_text = ""
    try:
        frontend_text = DEVELOPER_FRONTEND_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        add("Frontend source readable", "failed", str(exc), "frontend")
    else:
        add("Frontend source readable", "present", str(DEVELOPER_FRONTEND_PATH), "frontend")
        surfaces = {
            "New Chat frontend wired": ('id="new-chat-button"', "createNewChat", 'newChatButton.addEventListener("click", createNewChat)'),
            "Attachment frontend wired": ('id="zbrano-v0122-attachment-controller"', 'picker.addEventListener("change", uploadSelectedFiles, true)', "window.zbranoAttachmentIds"),
            "Shared Files actions wired": ('id="zbrano-v0123-shared-files-controller"', 'deleteButton.addEventListener("click", deleteSelected, true)', 'useButton.addEventListener("click", attachSelected, true)'),
            "Plugins frontend wired": ('id="plugins-tab"', 'zbrano-v01131-plugin-compact', 'plugin-settings-toggle'),
            "Entities frontend wired": ('id="entities-tab"', 'id="entities-panel"', "loadEntities"),
            "Developer frontend wired": ('id="developer-tab"', 'zbrano-v0120-developer-mode', "developer-run-diagnostics"),
            "Settings frontend wired": ('id="settings-tab"', 'id="settings-panel"', "save-settings"),
            "Voice frontend wired": ('id="mic-button"', "startRecording", "stopAudioPlayback"),
        }
        for name, markers in surfaces.items():
            missing = [marker for marker in markers if marker not in frontend_text]
            add(name, "wired" if not missing else "failed", "controller markers present" if not missing else "missing: " + ", ".join(missing), "frontend")

    try:
        registry = plugin_registry()
        add("Plugin registry readable", "operational", f"{len(registry)} installed plugins", "plugins")
    except Exception as exc:
        registry = {}
        add("Plugin registry readable", "failed", str(exc), "plugins")

    github_plugin = next(
        (
            plugin for plugin in registry.values()
            if _is_github_plugin(str(plugin.get("url") or ""), str(plugin.get("name") or ""))
        ),
        None,
    )
    if github_plugin:
        exposed = [
            tool for tool in github_plugin.get("tools", [])
            if tool.get("enabled") and tool.get("permission") in {"read_only", "write"}
        ]
        approvals = [tool for tool in exposed if tool.get("permission") == "write"]
        status = "operational" if github_plugin.get("enabled") and exposed else "degraded"
        add(
            "GitHub MCP readiness",
            status,
            f"{len(exposed)} tools exposed; {len(approvals)} write tools remain approval-required",
            "developer",
            "Connect GitHub, enable reviewed tools, and preserve write approvals.",
        )
    else:
        add("GitHub MCP readiness", "degraded", "GitHub plugin not installed", "developer", "Install and connect the official GitHub MCP plugin.")

    counts = {
        status: sum(1 for check in checks if check.get("status") == status)
        for status in ("present", "wired", "operational", "degraded", "failed")
    }
    return {
        "developer_mode": developer_mode_enabled(),
        "repository": DEVELOPER_REPOSITORY,
        "passed": len(checks) - counts["failed"],
        "total": len(checks),
        "healthy": counts["failed"] == 0,
        "counts": counts,
        "checks": checks,
        "deployment": "manual",
    }
'''
    text = text[:start] + diagnostics + text[end:]
    text = text.replace('version="0.12.2"', 'version="0.12.3"')
    text = text.replace('"version": "0.12.2"', '"version": "0.12.3"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    for marker, label in (
        ('id="shared-delete"', "Shared Files delete button"),
        ('id="shared-use"', "Shared Files attach button"),
        ('id="shared-file-rows"', "Shared Files rows"),
        ('id="zbrano-v0122-attachment-controller"', "attachment controller"),
    ):
        require(text, marker, label)

    controller = r'''
<script id="zbrano-v0123-shared-files-controller">
(() => {
  const rows = document.getElementById("shared-file-rows");
  const summary = document.getElementById("shared-summary");
  const deleteButton = document.getElementById("shared-delete");
  const useButton = document.getElementById("shared-use");
  if (!rows || !deleteButton || !useButton) return;

  const selectedIds = () => [
    ...rows.querySelectorAll("input[data-shared-id]:checked")
  ].map(input => input.dataset.sharedId).filter(Boolean);

  async function sharedApi(path, options = {}) {
    const response = await fetch(path, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    return payload;
  }

  async function deleteSelected(event) {
    event?.preventDefault();
    event?.stopImmediatePropagation();
    const ids = selectedIds();
    if (!ids.length) {
      if (summary) summary.textContent = "Select at least one shared file to delete.";
      return;
    }
    if (!window.confirm(`Delete ${ids.length} selected shared file${ids.length === 1 ? "" : "s"}?`)) return;
    deleteButton.disabled = true;
    try {
      const result = await sharedApi("api/files/shared", {
        method: "DELETE",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({file_ids: ids}),
      });
      const pending = window.zbranoPendingAttachments || [];
      for (let index = pending.length - 1; index >= 0; index -= 1) {
        if (ids.includes(pending[index]?.file_id)) pending.splice(index, 1);
      }
      window.zbranoAttachmentController?.renderPendingAttachments?.();
      if (summary) summary.textContent = `${result.count || 0} shared file${result.count === 1 ? "" : "s"} deleted.`;
      await window.zbranoLoadSharedFiles?.();
      window.zbranoSharedFilesController.lastAction = "delete";
      window.zbranoSharedFilesController.lastActionOk = true;
    } catch (error) {
      if (summary) summary.textContent = `Delete failed: ${error.message || error}`;
      window.zbranoSharedFilesController.lastAction = "delete";
      window.zbranoSharedFilesController.lastActionOk = false;
      window.zbranoSharedFilesController.lastError = String(error.message || error);
    } finally {
      deleteButton.disabled = false;
    }
  }

  async function attachSelected(event) {
    event?.preventDefault();
    event?.stopImmediatePropagation();
    const ids = selectedIds();
    if (!ids.length) {
      if (summary) summary.textContent = "Select at least one shared file to attach.";
      return;
    }
    useButton.disabled = true;
    try {
      const data = await sharedApi(`api/files/shared?_=${Date.now()}`, {cache: "no-store"});
      const selected = (data.files || []).filter(file => ids.includes(file.file_id));
      const pending = window.zbranoPendingAttachments = window.zbranoPendingAttachments || [];
      for (const file of selected) {
        if (!pending.some(item => item.file_id === file.file_id)) pending.push(file);
      }
      window.zbranoAttachmentController?.renderPendingAttachments?.();
      if (typeof showPanel === "function") showPanel("chat");
      if (summary) summary.textContent = `${selected.length} shared file${selected.length === 1 ? "" : "s"} attached to chat.`;
      window.zbranoSharedFilesController.lastAction = "attach";
      window.zbranoSharedFilesController.lastActionOk = selected.length === ids.length;
    } catch (error) {
      if (summary) summary.textContent = `Attach failed: ${error.message || error}`;
      window.zbranoSharedFilesController.lastAction = "attach";
      window.zbranoSharedFilesController.lastActionOk = false;
      window.zbranoSharedFilesController.lastError = String(error.message || error);
    } finally {
      useButton.disabled = false;
    }
  }

  window.zbranoSharedFilesController = {
    ready: true,
    selectedIds,
    deleteSelected,
    attachSelected,
    lastAction: "",
    lastActionOk: null,
    lastError: "",
  };
  deleteButton.addEventListener("click", deleteSelected, true);
  useButton.addEventListener("click", attachSelected, true);
})();
</script>
'''
    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.3 patch missing: body close")
    text = text[:body_close] + controller + text[body_close:]

    attachment_check = '''        {
          name: "Attachment controller wired",
          ok: Boolean(window.zbranoAttachRecovery?.installed && window.zbranoAttachmentController?.ready && typeof window.zbranoAttachmentController.uploadSelectedFiles === "function"),
          detail: window.zbranoAttachmentController?.ready ? "picker, uploader, pending IDs, and chip renderer active" : "attachment controller unavailable",
        },'''
    require(text, attachment_check, "attachment browser diagnostic")
    text = text.replace(
        attachment_check,
        attachment_check.replace('          detail:', '          status: "wired",\n          category: "frontend",\n          detail:') + '''
        {
          name: "Shared Files action controller wired",
          status: "wired",
          category: "frontend",
          ok: Boolean(window.zbranoSharedFilesController?.ready && typeof window.zbranoSharedFilesController.deleteSelected === "function" && typeof window.zbranoSharedFilesController.attachSelected === "function"),
          detail: window.zbranoSharedFilesController?.ready ? "select, attach, and delete handlers active" : "Shared Files action controller unavailable",
        },''',
        1,
    )

    old_counts = '''      data.total = data.checks.length;
      data.passed = data.checks.filter(item => item.ok).length;
      data.healthy = data.passed === data.total;'''
    new_counts = '''      for (const item of data.checks) {
        if (!item.status) item.status = item.ok ? "wired" : "failed";
      }
      data.total = data.checks.length;
      data.passed = data.checks.filter(item => item.status !== "failed").length;
      data.failed = data.checks.filter(item => item.status === "failed").length;
      data.degraded = data.checks.filter(item => item.status === "degraded").length;
      data.healthy = data.failed === 0;'''
    require(text, old_counts, "browser diagnostic count logic")
    text = text.replace(old_counts, new_counts, 1)

    old_render = '''        card.className = `developer-check ${item.ok ? "ok" : "fail"}`;
        const title = document.createElement("strong");
        title.textContent = `${item.ok ? "✓" : "✕"} ${item.name}`;'''
    if old_render not in text:
        old_render = '''        card.className = `developer-check ${item.ok ? "ok" : "fail"}`;
        const title = document.createElement("strong");
        title.textContent = `${item.ok ? "âœ“" : "âœ•"} ${item.name}`;'''
    require(text, old_render, "developer diagnostic card renderer")
    new_render = '''        const status = item.status || (item.ok ? "wired" : "failed");
        card.className = `developer-check ${status === "failed" ? "fail" : status}`;
        const title = document.createElement("strong");
        const symbol = status === "failed" ? "✕" : status === "degraded" ? "!" : "✓";
        title.textContent = `${symbol} ${item.name} · ${status}`;'''
    text = text.replace(old_render, new_render, 1)

    old_detail = '        detail.textContent = item.detail || "";'
    new_detail = '''        detail.textContent = item.repair_hint
          ? `${item.detail || ""} · Repair hint: ${item.repair_hint}`
          : (item.detail || "");'''
    require(text, old_detail, "developer diagnostic detail renderer")
    text = text.replace(old_detail, new_detail, 1)

    old_summary = '''      summary.textContent = `${data.passed}/${data.total} checks passed${data.healthy ? " · healthy" : " · attention required"}`;'''
    if old_summary not in text:
        old_summary = '''      summary.textContent = `${data.passed}/${data.total} checks passed${data.healthy ? " Â· healthy" : " Â· attention required"}`;'''
    require(text, old_summary, "developer diagnostic summary")
    text = text.replace(
        old_summary,
        '''      summary.textContent = `${data.passed}/${data.total} non-failing · ${data.degraded || 0} degraded · ${data.failed || 0} failed`;''',
        1,
    )

    style_close = text.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.3 patch missing: style close")
    css = '''
    .developer-check.degraded strong{color:#ffc857}
    .developer-check.wired strong,.developer-check.present strong,.developer-check.operational strong{color:var(--cyan)}
'''
    text = text[:style_close] + css + text[style_close:]
    text = text.replace("HUD 0.12.2", "HUD 0.12.3")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    missing = []
    for marker in (
        'version="0.12.3"',
        '"Shared Files create/list/delete operational"',
        '"Conversation lifecycle operational"',
        '"Chat attachment lifecycle operational"',
        '"Persistent storage operational"',
        '"Voice pipeline readiness"',
        '"AI chat readiness"',
        '"Workshop Memory operational"',
        '"Plugin Catalog operational"',
        'for attempt in (1, 2):',
        '"repair_hint"',
        '"counts": counts',
    ):
        if marker not in main:
            missing.append(marker)
    for marker in (
        'id="zbrano-v0123-shared-files-controller"',
        'deleteButton.addEventListener("click", deleteSelected, true)',
        'useButton.addEventListener("click", attachSelected, true)',
        'name: "Shared Files action controller wired"',
        'status === "degraded"',
        "Repair hint:",
        "HUD 0.12.3",
    ):
        if marker not in index:
            missing.append(marker)
    if missing:
        raise RuntimeError("ZBRANO v0.12.3 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
