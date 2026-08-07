from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.11.30 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    # Put the password field in an actual form. Keep all existing IDs and the
    # existing click handler so authentication behavior does not change.
    plugin_form_marker = '<div class="plugin-form">'
    require(text, plugin_form_marker, "plugin install form")
    form_start = text.find(plugin_form_marker)
    installed_heading = '<h2>INSTALLED PLUGINS</h2>'
    installed_pos = text.find(installed_heading, form_start)
    if installed_pos < 0:
        raise RuntimeError("ZBRANO v0.11.30 patch missing: installed plugins heading")
    closing = text.rfind('</div>', form_start, installed_pos)
    if closing < 0:
        raise RuntimeError("ZBRANO v0.11.30 patch missing: plugin form close")
    text = text[:form_start] + '<form id="plugin-install-form" class="plugin-form">' + text[form_start + len(plugin_form_marker):]
    # Positions shifted, find the heading and last div before it again.
    installed_pos = text.find(installed_heading)
    closing = text.rfind('</div>', 0, installed_pos)
    if closing < 0:
        raise RuntimeError("ZBRANO v0.11.30 patch missing: rewritten plugin form close")
    text = text[:closing] + '</form>' + text[closing + len('</div>'):]

    # A form submit should use the existing install button logic. This removes
    # the browser password-field warning and makes Enter behave consistently.
    submit_bridge = r'''
<script id="zbrano-v01130-plugin-form">
(() => {
  const form = document.getElementById("plugin-install-form");
  const button = document.getElementById("install-plugin");
  form?.addEventListener("submit", event => {
    event.preventDefault();
    button?.click();
  });
})();
</script>
'''

    # Shared Files gets a self-contained late controller. Do not depend on the
    # historical closure's private list() function or on showPanel().
    shared_recovery = r'''
<script id="zbrano-v01130-shared-files-recovery">
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
    for (const id of ["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel"]) {
      document.getElementById(id)?.classList.toggle("hidden", id !== "files-panel");
    }
    for (const id of ["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab"]) {
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
</script>
'''

    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.11.30 patch missing: body close")
    text = text[:body_close] + submit_bridge + shared_recovery + text[body_close:]

    text = text.replace("HUD 0.11.29", "HUD 0.11.30")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.29"', 'version="0.11.30"')
    text = text.replace('"version": "0.11.29"', '"version": "0.11.30"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    missing = []
    for marker in (
        'id="plugin-install-form"',
        'id="plugin-token" type="password"',
        'zbrano-v01130-shared-files-recovery',
        'function activateFilesPanel()',
        'api/files/shared?',
        'window.zbranoLoadSharedFiles',
        'id="files-tab"',
        'id="files-panel"',
        'HUD 0.11.30',
    ):
        if marker not in index:
            missing.append(marker)
    for marker in (
        '@app.get("/api/files/shared")',
        '@app.post("/api/files/shared")',
        'version="0.11.30"',
    ):
        if marker not in main:
            missing.append(marker)
    if '<div class="plugin-form">' in index:
        missing.append("standalone plugin password form remains")
    if missing:
        raise RuntimeError("ZBRANO v0.11.30 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
