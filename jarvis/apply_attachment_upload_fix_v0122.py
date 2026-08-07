from pathlib import Path


ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.2 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    marker = '    await probe("Developer status operational", "/api/developer/status")\n\n'
    require(text, marker, "developer status diagnostic")

    upload_diagnostic = r'''    diagnostic_session = "__zbrano_attachment_diagnostic__"
    diagnostic_dir = CHAT_UPLOAD_ROOT / _sid(diagnostic_session)
    shutil.rmtree(diagnostic_dir, ignore_errors=True)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://127.0.0.1:8099/api/files/chat/{diagnostic_session}",
                files={"file": ("zbrano-diagnostic.txt", b"attachment diagnostic\n", "text/plain")},
            )
        payload = response.json()
        file_id = payload.get("file_id") if isinstance(payload, dict) else None
        stored = diagnostic_dir / str(file_id)
        ok = response.status_code == 200 and bool(file_id) and stored.is_dir()
        checks.append(_developer_check(
            "Attachment upload operational",
            ok,
            f"HTTP {response.status_code}; temporary file stored and removed" if ok
            else f"HTTP {response.status_code}; valid file ID/storage missing",
        ))
    except Exception as exc:
        checks.append(_developer_check("Attachment upload operational", False, str(exc)))
    finally:
        shutil.rmtree(diagnostic_dir, ignore_errors=True)

'''
    text = text.replace(marker, marker + upload_diagnostic, 1)
    text = text.replace('version="0.12.1"', 'version="0.12.2"')
    text = text.replace('"version": "0.12.1"', '"version": "0.12.2"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    for marker, label in (
        ('id="attach-file"', "Attach button"),
        ('id="attachment-input"', "file input"),
        ('id="chat-attachments"', "attachment strip"),
        ('id="attachment-state"', "attachment status"),
        ('id="zbrano-v0121-attach-recovery"', "v0.12.1 picker recovery"),
    ):
        require(text, marker, label)

    runtime = r'''
<script id="zbrano-v0122-attachment-controller">
(() => {
  const picker = document.getElementById("attachment-input");
  const scope = document.getElementById("attachment-scope");
  const state = document.getElementById("attachment-state");
  const strip = document.getElementById("chat-attachments");
  if (!picker || !strip) return;

  const pending = window.zbranoPendingAttachments = window.zbranoPendingAttachments || [];

  function renderPendingAttachments() {
    strip.replaceChildren();
    for (const item of pending) {
      const chip = document.createElement("span");
      chip.className = "attachment-chip";
      chip.textContent = `${item.scope === "shared" ? "Shared" : "Chat"}: ${item.name}`;
      strip.appendChild(chip);
    }
  }

  function clearPendingAttachments() {
    pending.splice(0, pending.length);
    renderPendingAttachments();
  }

  async function uploadSelectedFiles(event) {
    event.preventDefault();
    event.stopImmediatePropagation();
    const files = Array.from(picker.files || []);
    if (!files.length) return;

    const destination = scope?.value === "shared" ? "shared" : "chat";
    if (state) state.textContent = `Uploading ${files.length} file${files.length === 1 ? "" : "s"}…`;
    try {
      for (const file of files) {
        const body = new FormData();
        body.append("file", file);
        const endpoint = destination === "shared"
          ? "api/files/shared"
          : `api/files/chat/${encodeURIComponent(jarvisChatSessionId)}`;
        const response = await fetch(endpoint, {method: "POST", body});
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
        if (!payload.file_id || !payload.name) throw new Error("Upload response did not include a file ID");
        if (!pending.some(item => item.file_id === payload.file_id)) pending.push(payload);
      }
      renderPendingAttachments();
      if (destination === "shared" && typeof window.zbranoLoadSharedFiles === "function") {
        await window.zbranoLoadSharedFiles();
      }
      if (state) {
        state.textContent = destination === "shared"
          ? `${files.length} file${files.length === 1 ? "" : "s"} attached and added to Shared Files`
          : `${files.length} file${files.length === 1 ? "" : "s"} attached to this chat`;
      }
      window.zbranoAttachmentController.lastUploadOk = true;
      window.zbranoAttachmentController.lastError = "";
    } catch (error) {
      if (state) state.textContent = `Upload failed: ${error.message || error}`;
      window.zbranoAttachmentController.lastUploadOk = false;
      window.zbranoAttachmentController.lastError = String(error.message || error);
    } finally {
      picker.value = "";
    }
  }

  window.zbranoAttachmentIds = () => pending.map(item => item.file_id);
  window.zbranoClearPendingAttachments = clearPendingAttachments;
  window.zbranoAttachmentController = {
    ready: true,
    uploadSelectedFiles,
    renderPendingAttachments,
    lastUploadOk: null,
    lastError: "",
  };
  picker.addEventListener("change", uploadSelectedFiles, true);
  renderPendingAttachments();
})();
</script>
'''
    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.2 patch missing: body close")
    text = text[:body_close] + runtime + text[body_close:]

    old_browser_check = '''          name: "Attach click wiring active",
          ok: Boolean(window.zbranoAttachRecovery?.installed && document.getElementById("attach-file") && document.getElementById("attachment-input")),
          detail: window.zbranoAttachRecovery?.installed ? "late recovery controller active" : "attach controller unavailable",'''
    new_browser_check = '''          name: "Attachment controller wired",
          ok: Boolean(window.zbranoAttachRecovery?.installed && window.zbranoAttachmentController?.ready && typeof window.zbranoAttachmentController.uploadSelectedFiles === "function"),
          detail: window.zbranoAttachmentController?.ready ? "picker, uploader, pending IDs, and chip renderer active" : "attachment controller unavailable",'''
    require(text, old_browser_check, "v0.12.1 attachment browser check")
    text = text.replace(old_browser_check, new_browser_check, 1)

    text = text.replace("HUD 0.12.1", "HUD 0.12.2")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    missing = []
    for marker in (
        '"Attachment upload operational"',
        '"zbrano-diagnostic.txt"',
        "shutil.rmtree(diagnostic_dir, ignore_errors=True)",
        'version="0.12.2"',
    ):
        if marker not in main:
            missing.append(marker)
    for marker in (
        'id="zbrano-v0122-attachment-controller"',
        "window.zbranoPendingAttachments",
        'picker.addEventListener("change", uploadSelectedFiles, true)',
        "pending.splice(0, pending.length)",
        'name: "Attachment controller wired"',
        "HUD 0.12.2",
    ):
        if marker not in index:
            missing.append(marker)
    if missing:
        raise RuntimeError("ZBRANO v0.12.2 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
