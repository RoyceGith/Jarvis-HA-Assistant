import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.51 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.51 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    script_start = frontend.find('<script id="zbrano-v01248-tab-activity">')
    if script_start < 0:
        raise RuntimeError("ZBRANO v0.12.51 could not locate the old tab activity runtime")
    script_end = frontend.find("</script>", script_start)
    if script_end < 0:
        raise RuntimeError("ZBRANO v0.12.51 could not locate the old tab activity runtime end")
    script_end += len("</script>")

    semantic_runtime = r'''<script id="zbrano-v01251-semantic-tab-activity">
(() => {
  const bindings = [];

  function isViewed(button, panel) {
    const selected = button.classList.contains("active") || button.getAttribute("aria-selected") === "true";
    return selected && !panel.hidden && !panel.closest(".hidden");
  }

  function mark(button) {
    if (!button || button.classList.contains("zbrano-tab-unseen")) return;
    button.classList.add("zbrano-tab-unseen");
    if (!button.hasAttribute("aria-label")) {
      button.dataset.zbranoActivityLabel = "generated";
      button.setAttribute("aria-label", `${button.textContent.trim()} · new activity`);
    }
  }

  function clear(button) {
    if (!button) return;
    button.classList.remove("zbrano-tab-unseen");
    if (button.dataset.zbranoActivityLabel === "generated") {
      button.removeAttribute("aria-label");
      delete button.dataset.zbranoActivityLabel;
    }
  }

  function bind(button, panel) {
    if (!button || !panel || bindings.some(item => item.button === button)) return;
    button.addEventListener("click", () => requestAnimationFrame(() => clear(button)));
    bindings.push({button, panel});
  }

  function markIfUnseen(button) {
    const binding = bindings.find(item => item.button === button);
    if (binding && !isViewed(binding.button, binding.panel)) mark(binding.button);
  }

  for (const name of ["chat", "files", "plugins", "entities", "automations", "settings", "developer"]) {
    bind(document.getElementById(`${name}-tab`), document.getElementById(`${name}-panel`));
  }
  for (const button of document.querySelectorAll("[data-auto-view]")) {
    bind(button, document.querySelector(`[data-auto-panel="${CSS.escape(button.dataset.autoView)}"]`));
  }
  for (const button of document.querySelectorAll("[data-notification-view]")) {
    bind(button, document.querySelector(`[data-notification-panel="${CSS.escape(button.dataset.notificationView)}"]`));
  }
  for (const button of document.querySelectorAll(".settings-category-tab[data-settings-target]")) {
    bind(button, document.querySelector(`[data-settings-category="${CSS.escape(button.dataset.settingsTarget)}"]`));
  }
  for (const button of document.querySelectorAll("#plugins-installed-tab, #plugins-browse-tab")) {
    bind(button, document.getElementById(button.getAttribute("aria-controls")));
  }

  window.zbranoMarkTabChanged = tabId => markIfUnseen(document.getElementById(tabId));
  window.zbranoClearTabChanged = tabId => clear(document.getElementById(tabId));

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);
    try {
      const request = args[0];
      const options = args[1] || {};
      const method = String(options.method || (request instanceof Request ? request.method : "GET")).toUpperCase();
      const url = new URL(request instanceof Request ? request.url : String(request), document.baseURI);
      if (response.ok && !["GET", "HEAD", "OPTIONS"].includes(method)) {
        const path = url.pathname;
        if (path.includes("/api/files/")) markIfUnseen(document.getElementById("files-tab"));
        if (path.includes("/api/plugins")) markIfUnseen(document.getElementById("plugins-tab"));
        if (path.includes("/api/automations")) {
          markIfUnseen(document.getElementById("automations-tab"));
          markIfUnseen(document.querySelector('[data-auto-view="library"]'));
        }
        if (path.includes("/api/notifications")) {
          markIfUnseen(document.getElementById("automations-tab"));
          markIfUnseen(document.querySelector('[data-auto-view="notifications"]'));
          if (path.endsWith("/test")) markIfUnseen(document.querySelector('[data-notification-view="logs"]'));
        }
      }
    } catch (_) {}
    return response;
  };

  window.addEventListener("message", event => {
    if (event.origin === window.location.origin && event.data?.type === "zbrano-plugin-oauth") {
      markIfUnseen(document.getElementById("plugins-tab"));
    }
  });

  let notificationSignature = null;
  async function checkNotificationActivity() {
    try {
      const response = await nativeFetch("api/notifications/activity", {cache:"no-store"});
      if (!response.ok) return;
      const activity = await response.json();
      const signature = `${activity.latest_id || ""}:${activity.count || 0}`;
      if (notificationSignature !== null && signature !== notificationSignature) {
        markIfUnseen(document.getElementById("automations-tab"));
        markIfUnseen(document.querySelector('[data-auto-view="notifications"]'));
        markIfUnseen(document.querySelector('[data-notification-view="logs"]'));
      }
      notificationSignature = signature;
    } catch (_) {}
  }

  checkNotificationActivity();
  setInterval(checkNotificationActivity, 15000);
})();
</script>'''
    frontend = frontend[:script_start] + semantic_runtime + frontend[script_end:]

    frontend = replace_once(
        frontend,
        '''    finishResponseActivity(requestState.stopped ? "Stopped" : (answer ? "Completed" : "No response"));
    input.disabled = false;
''',
        '''    finishResponseActivity(requestState.stopped ? "Stopped" : (answer ? "Completed" : "No response"));
    if (!requestState.stopped && answer) window.zbranoMarkTabChanged?.("chat-tab");
    input.disabled = false;
''',
        "completed chat response activity signal",
    )

    backend = backend.replace('version="0.12.50"', 'version="0.12.51"')
    backend = backend.replace('"version": "0.12.50"', '"version": "0.12.51"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.50"', '"X-ZBRANO-Frontend-Version": "0.12.51"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.50"', '"name": "ZBRANO Developer Mode", "version": "0.12.51"')
    frontend = frontend.replace("HUD 0.12.50", "HUD 0.12.51")

    for marker in (
        'version="0.12.51"',
        'service_domain = "telegram_bot" if channel["platform"] == "telegram" else "notify"',
    ):
        require(backend, marker, marker)
    for marker in (
        "HUD 0.12.51",
        'id="zbrano-v01251-semantic-tab-activity"',
        'window.zbranoMarkTabChanged?.("chat-tab")',
        "checkNotificationActivity",
        "const nativeFetch = window.fetch.bind(window)",
        'event.data?.type === "zbrano-plugin-oauth"',
    ):
        require(frontend, marker, marker)

    semantic_block = frontend.split('<script id="zbrano-v01251-semantic-tab-activity">', 1)[1].split("</script>", 1)[0]
    if "MutationObserver" in semantic_block or "observer.observe" in semantic_block:
        raise RuntimeError("ZBRANO v0.12.51 still uses generic DOM mutation activity detection")
    if 'id="zbrano-v01248-tab-activity"' in frontend:
        raise RuntimeError("ZBRANO v0.12.51 retained the obsolete v0.12.48 activity runtime")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
