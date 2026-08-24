(() => {
  const tab = document.getElementById("files-tab");
  const panel = document.getElementById("files-panel");
  const rows = document.getElementById("shared-file-rows");
  const summary = document.getElementById("shared-summary");
  const sort = document.getElementById("shared-sort");
  const order = document.getElementById("shared-order");
  const refresh = document.getElementById("shared-refresh");

  if (!tab || !panel || !rows) return;

  const escHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[char]);

  function activateFilesPanel() {
    for (const id of ["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel", "calendar-panel"]) {
      document.getElementById(id)?.classList.toggle("hidden", id !== "files-panel");
    }
    for (const id of ["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab", "calendar-tab"]) {
      document.getElementById(id)?.classList.toggle("active", id === "files-tab");
    }
  }

  async function loadSharedFiles() {
    if (summary) summary.textContent = "Loading shared files…";
    const params = new URLSearchParams({
      sort: sort?.value || "date",
      order: order?.value || "desc",
      _: String(Date.now()),
    });
    try {
      const response = await fetch(`api/files/shared?${params.toString()}`, {cache: "no-store"});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      const files = Array.isArray(data.files) ? data.files : [];
      rows.replaceChildren();
      for (const file of files) {
        const row = document.createElement("tr");
        row.innerHTML = `<td><input type="checkbox" data-shared-id="${escHtml(file.file_id)}"></td>` +
          `<td>${escHtml(file.name)}</td>` +
          `<td>${new Date(Number(file.created_at || 0) * 1000).toLocaleString()}</td>` +
          `<td>${escHtml(file.mime_type)}</td>` +
          `<td>${Math.round(Number(file.size || 0) / 1024)} KB</td>`;
        rows.appendChild(row);
      }
      if (summary) summary.textContent = `${files.length} shared file${files.length === 1 ? "" : "s"} · available to every chat`;
    } catch (error) {
      rows.replaceChildren();
      if (summary) summary.textContent = `Could not load Shared Files: ${error.message || error}`;
    }
  }

  tab.addEventListener("click", event => {
    event.preventDefault();
    event.stopPropagation();
    activateFilesPanel();
    loadSharedFiles();
  }, true);

  refresh?.addEventListener("click", event => {
    event.preventDefault();
    loadSharedFiles();
  });
  sort?.addEventListener("change", loadSharedFiles);
  order?.addEventListener("change", loadSharedFiles);

  window.zbranoLoadSharedFiles = loadSharedFiles;
})();
