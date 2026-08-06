from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.10.2 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    require(text, "</style>", "style close")
    css = r'''
    :root[data-theme="light"] .message h2,
    :root[data-theme="light"] .message h3,
    :root[data-theme="light"] .message h4 {
      color: #111111 !important;
    }

    .entity-load-error {
      padding: .8rem;
      color: #8a2020;
      font-weight: 700;
    }
'''
    text = text.replace("</style>", css + "</style>", 1)

    require(text, "</body>", "body close")
    recovery_script = r'''
<script id="jarvis-v0102-tab-recovery">
(() => {
  const byId = id => document.getElementById(id);
  const tabs = {
    chat: byId("chat-tab"),
    entities: byId("entities-tab"),
    settings: byId("settings-tab"),
    plugins: byId("plugins-tab"),
  };
  const panels = {
    chat: byId("chat-panel"),
    entities: byId("entities-panel"),
    settings: byId("settings-panel"),
    plugins: byId("plugins-panel"),
  };

  function activatePanel(name) {
    for (const [panelName, panel] of Object.entries(panels)) {
      if (panel) panel.classList.toggle("hidden", panelName !== name);
    }
    for (const [tabName, tab] of Object.entries(tabs)) {
      if (tab) tab.classList.toggle("active", tabName === name);
    }
  }

  async function recoverEntities() {
    activatePanel("entities");
    const summary = byId("entity-summary");
    try {
      if (typeof loadEntities === "function") {
        await loadEntities();
      } else {
        throw new Error("Entity loader is unavailable");
      }
      const rows = byId("entity-rows");
      if (rows && rows.children.length === 0 && summary && !/0 total/i.test(summary.textContent || "")) {
        summary.textContent = "No entity rows were rendered. Select Refresh or check the Jarvis add-on logs.";
      }
    } catch (error) {
      if (summary) {
        summary.classList.add("entity-load-error");
        summary.textContent = `Could not load Home Assistant entities: ${error.message || error}`;
      }
    }
  }

  async function recoverPlugins() {
    activatePanel("plugins");
    const state = byId("plugin-state");
    try {
      if (typeof loadPlugins !== "function") {
        throw new Error("Plugin loader is unavailable");
      }
      await loadPlugins();
    } catch (error) {
      if (state) state.textContent = `Could not load plugins: ${error.message || error}`;
    }
  }

  tabs.chat?.addEventListener("click", () => activatePanel("chat"), true);
  tabs.settings?.addEventListener("click", () => activatePanel("settings"), true);
  tabs.entities?.addEventListener("click", event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    recoverEntities();
  }, true);
  tabs.plugins?.addEventListener("click", event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    recoverPlugins();
  }, true);

  byId("refresh-entities")?.addEventListener("click", event => {
    event.preventDefault();
    recoverEntities();
  }, true);

  window.jarvisActivatePanel = activatePanel;
})();
</script>
'''
    text = text.replace("</body>", recovery_script + "\n</body>", 1)
    text = text.replace("HUD 0.10.1", "HUD 0.10.2")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.10.1"', 'version="0.10.2"')
    text = text.replace('"version": "0.10.1"', '"version": "0.10.2"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    required_index = (
        'id="jarvis-v0102-tab-recovery"',
        'recoverEntities()',
        'recoverPlugins()',
        'color: #111111 !important',
    )
    missing = [value for value in required_index if value not in index]
    if "0.10.2" not in main:
        missing.append("backend version 0.10.2")
    if missing:
        raise RuntimeError("Jarvis v0.10.2 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
