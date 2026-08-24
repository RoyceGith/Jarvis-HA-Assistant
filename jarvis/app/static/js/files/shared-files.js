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
