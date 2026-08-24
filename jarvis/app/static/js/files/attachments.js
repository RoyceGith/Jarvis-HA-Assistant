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
        const names = files.map(file => file.name).join(", ");
        state.textContent = destination === "shared"
          ? `Attached and added to Shared Files: ${names}`
          : `Attached to this chat: ${names}`;
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
  window.zbranoAttachmentItems = () => pending.map(item => ({
    file_id: item.file_id,
    name: item.name,
    scope: item.scope,
    mime_type: item.mime_type,
    size: item.size,
  }));
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
