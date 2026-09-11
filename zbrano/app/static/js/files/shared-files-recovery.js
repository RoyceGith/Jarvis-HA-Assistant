(() => {
  const tab = document.getElementById("files-tab");
  const panel = document.getElementById("files-panel");
  const rows = document.getElementById("shared-file-rows");
  const summary = document.getElementById("shared-summary");
  const sort = document.getElementById("shared-sort");
  const order = document.getElementById("shared-order");
  const refresh = document.getElementById("shared-refresh");
  const breadcrumbs = document.getElementById("shared-breadcrumbs");
  const newFolder = document.getElementById("shared-new-folder");
  const uploadHere = document.getElementById("shared-upload-here");
  const uploadInput = document.getElementById("shared-folder-upload");
  const moveTarget = document.getElementById("shared-move-target");
  if (!tab || !panel || !rows) return;

  let currentFolder = "";
  const escHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[char]);
  const api = async (path, options = {}) => {
    const response = await fetch(path, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  };
  const formatBytes = value => {
    const bytes = Math.max(0, Number(value || 0));
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes < 10240 ? 1 : 0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };
  const fileKind = file => {
    const extension = String(file.name || "").split(".").pop().toUpperCase();
    if (extension && extension !== String(file.name || "").toUpperCase() && extension.length <= 5) return extension;
    const subtype = String(file.mime_type || "file").split("/").pop().split(/[+;.]/)[0];
    return (subtype || "FILE").slice(0, 8).toUpperCase();
  };

  function activateFilesPanel() {
    for (const id of ["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel", "contacts-panel", "calendar-panel", "about-panel"]) {
      document.getElementById(id)?.classList.toggle("hidden", id !== "files-panel");
    }
    for (const id of ["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab", "contacts-tab", "calendar-tab", "about-tab"]) {
      document.getElementById(id)?.classList.toggle("active", id === "files-tab");
    }
  }

  function renderBreadcrumbs() {
    if (!breadcrumbs) return;
    const parts = currentFolder ? currentFolder.split("/") : [];
    let path = "";
    breadcrumbs.innerHTML = `<button type="button" data-shared-folder="">Shared Files</button>` + parts.map(part => {
      path = path ? `${path}/${part}` : part;
      return `<button type="button" data-shared-folder="${escHtml(path)}">${escHtml(part)}</button>`;
    }).join("");
  }

  async function loadFolderChoices() {
    if (!moveTarget) return;
    const data = await api(`api/files/shared/folders?_=${Date.now()}`, {cache:"no-store"});
    const folders = Array.isArray(data.folders) ? data.folders : [];
    moveTarget.innerHTML = `<option value="">Move selected to…</option><option value="__root__">Shared Files (main)</option>` + folders
      .filter(folder => folder.path !== currentFolder)
      .map(folder => `<option value="${escHtml(folder.path)}">${escHtml(folder.path)}</option>`).join("");
  }

  async function loadSharedFiles(folder = currentFolder) {
    currentFolder = String(folder || "");
    panel.dataset.sharedFolder = currentFolder;
    if (summary) summary.textContent = "Loading shared files…";
    const params = new URLSearchParams({sort:sort?.value || "date", order:order?.value || "desc", folder:currentFolder, _:String(Date.now())});
    try {
      const data = await api(`api/files/shared?${params.toString()}`, {cache:"no-store"});
      const files = Array.isArray(data.files) ? data.files : [];
      const folders = Array.isArray(data.folders) ? data.folders : [];
      window.zbranoVisibleSharedFiles = files;
      rows.replaceChildren();
      for (const folder of folders) {
        const row = document.createElement("tr");
        row.className = "shared-folder-row";
        const folderCount = Number(folder.file_count || 0);
        row.innerHTML = `<td></td><td><button type="button" class="shared-folder-name" data-shared-folder="${escHtml(folder.path)}"><span class="shared-folder-icon" aria-hidden="true">&#128193;</span>${escHtml(folder.name)}</button></td><td>—</td><td>Folder</td><td>${folderCount} file${folderCount === 1 ? "" : "s"}</td><td><button type="button" class="shared-folder-delete" data-delete-shared-folder="${escHtml(folder.path)}">Delete</button></td>`;
        rows.appendChild(row);
      }
      for (const file of files) {
        const row = document.createElement("tr");
        const kind = fileKind(file);
        row.innerHTML = `<td><input type="checkbox" data-shared-id="${escHtml(file.file_id)}" aria-label="Select ${escHtml(file.name)}"></td><td><span class="shared-file-name"><span class="shared-file-icon" aria-hidden="true">${escHtml(kind)}</span>${escHtml(file.name)}</span></td><td class="shared-file-date">${new Date(Number(file.created_at || 0) * 1000).toLocaleString(window.ZbranoI18n?.locale || undefined)}</td><td>${escHtml(kind)}</td><td>${formatBytes(file.size)}</td><td></td>`;
        rows.appendChild(row);
      }
      if (!folders.length && !files.length) rows.innerHTML = `<tr class="shared-files-empty"><td colspan="6">This folder is empty. Upload files or create a folder here.</td></tr>`;
      renderBreadcrumbs();
      await loadFolderChoices();
      const location = currentFolder || "Shared Files";
      if (summary) summary.textContent = `${folders.length} folder${folders.length === 1 ? "" : "s"} · ${files.length} file${files.length === 1 ? "" : "s"} in ${location}`;
    } catch (error) {
      rows.replaceChildren();
      if (summary) summary.textContent = `Could not load Shared Files: ${error.message || error}`;
    }
  }

  async function createFolder() {
    const name = window.prompt("Name this folder");
    if (!name?.trim()) return;
    try {
      await api("api/files/shared/folders", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({parent:currentFolder,name:name.trim()})});
      await loadSharedFiles();
    } catch (error) {
      if (summary) summary.textContent = `Could not create folder: ${error.message || error}`;
    }
  }

  async function uploadFiles() {
    const files = Array.from(uploadInput?.files || []);
    if (!files.length) return;
    if (summary) summary.textContent = `Uploading ${files.length} file${files.length === 1 ? "" : "s"}…`;
    try {
      for (const file of files) {
        const body = new FormData();
        body.append("file", file);
        body.append("folder", currentFolder);
        await api("api/files/shared", {method:"POST", body});
      }
      uploadInput.value = "";
      await loadSharedFiles();
    } catch (error) {
      if (summary) summary.textContent = `Upload failed: ${error.message || error}`;
    }
  }

  panel.addEventListener("click", async event => {
    const folderButton = event.target.closest("[data-shared-folder]");
    if (folderButton) { event.preventDefault(); await loadSharedFiles(folderButton.dataset.sharedFolder || ""); return; }
    const deleteButton = event.target.closest("[data-delete-shared-folder]");
    if (!deleteButton) return;
    event.preventDefault();
    const folder = deleteButton.dataset.deleteSharedFolder;
    if (!window.confirm(`Delete the empty folder “${folder}”?`)) return;
    try {
      await api("api/files/shared/folders", {method:"DELETE",headers:{"Content-Type":"application/json"},body:JSON.stringify({folder})});
      await loadSharedFiles();
    } catch (error) {
      if (summary) summary.textContent = `Could not delete folder: ${error.message || error}`;
    }
  });
  tab.addEventListener("click", event => { event.preventDefault(); event.stopPropagation(); activateFilesPanel(); loadSharedFiles(); }, true);
  refresh?.addEventListener("click", event => { event.preventDefault(); loadSharedFiles(); });
  newFolder?.addEventListener("click", createFolder);
  uploadHere?.addEventListener("click", () => uploadInput?.click());
  uploadInput?.addEventListener("change", uploadFiles);
  sort?.addEventListener("change", () => loadSharedFiles());
  order?.addEventListener("change", () => loadSharedFiles());
  window.zbranoLoadSharedFiles = loadSharedFiles;
})();
