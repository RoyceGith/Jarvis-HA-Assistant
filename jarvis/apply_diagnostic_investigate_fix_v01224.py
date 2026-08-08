import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.24 patch expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.24 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''        card.append(title, detail);
        checks.appendChild(card);''',
        '''        card.dataset.diagnosticName = item.name || "Unknown diagnostic";
        card.append(title, detail);
        if (status === "failed") {
          const fixButton = document.createElement("button");
          fixButton.type = "button";
          fixButton.className = "diagnostic-investigate-fix";
          fixButton.textContent = "Investigate & Fix";
          fixButton.addEventListener("click", () => {
            window.zbranoInvestigateFailedDiagnostic?.(item, fixButton);
          });
          card.appendChild(fixButton);
        }
        checks.appendChild(card);''',
        "failed diagnostic action",
    )

    workflow_style = '''
<style id="zbrano-v01224-diagnostic-fix-style">
  .diagnostic-investigate-fix { margin-top: .65rem; width: 100%; }
  .diagnostic-investigate-fix:disabled { cursor: wait; opacity: .72; }
  .diagnostic-return-banner {
    display: flex; align-items: center; justify-content: space-between; gap: .75rem;
    margin: .55rem .75rem 0; padding: .55rem .7rem; border: 1px solid var(--line);
    border-radius: 8px; background: color-mix(in srgb, var(--surface) 86%, transparent);
  }
  .diagnostic-return-banner span { min-width: 0; overflow-wrap: anywhere; }
  .diagnostic-return-banner button { flex: 0 0 auto; }
</style>
'''
    frontend = replace_once(
        frontend,
        "</head>",
        workflow_style + "</head>",
        "diagnostic workflow style",
    )

    workflow_script = r'''
<script id="zbrano-v01224-diagnostic-fix">
(() => {
  let launchInProgress = false;

  function conciseEvidence(item) {
    return [item?.detail, item?.repair_hint ? `Repair hint: ${item.repair_hint}` : ""]
      .filter(Boolean)
      .join(". ")
      .slice(0, 1400);
  }

  function showReturnBanner(item) {
    const stage = document.querySelector("#chat-panel .core-stage");
    const messages = document.getElementById("messages");
    if (!stage || !messages) return;
    let banner = document.getElementById("diagnostic-return-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "diagnostic-return-banner";
      banner.className = "diagnostic-return-banner";
      const label = document.createElement("span");
      label.id = "diagnostic-return-label";
      const back = document.createElement("button");
      back.type = "button";
      back.textContent = "Return to diagnostic";
      back.addEventListener("click", () => {
        document.getElementById("developer-tab")?.click();
        window.setTimeout(() => {
          const name = banner.dataset.diagnosticName || "";
          const card = [...document.querySelectorAll(".developer-check")]
            .find(node => node.dataset.diagnosticName === name);
          card?.scrollIntoView({behavior: "smooth", block: "center"});
        }, 250);
      });
      banner.append(label, back);
      stage.insertBefore(banner, messages);
    }
    banner.dataset.diagnosticName = String(item?.name || "");
    document.getElementById("diagnostic-return-label").textContent =
      `Developer investigation: ${item?.name || "failed diagnostic"}`;
  }

  async function enableDeveloperMode() {
    const response = await fetch("api/developer/mode", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({enabled: true}),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.enabled) {
      throw new Error(data.detail || `Developer Mode could not be enabled (HTTP ${response.status})`);
    }
    const toggle = document.getElementById("developer-toggle");
    if (toggle) {
      toggle.dataset.enabled = "true";
      toggle.setAttribute("aria-pressed", "true");
      toggle.textContent = "Disable Developer Mode";
    }
    const indicator = document.getElementById("developer-mode-indicator");
    if (indicator) {
      indicator.hidden = false;
      indicator.textContent = "Developer Mode Active";
    }
  }

  window.zbranoInvestigateFailedDiagnostic = async (item, button) => {
    const developerSummary = document.getElementById("developer-summary");
    if (launchInProgress || activeRequest) {
      if (developerSummary) {
        developerSummary.textContent = "Finish or stop the current Chat request before starting another investigation.";
      }
      return;
    }
    launchInProgress = true;
    const originalLabel = button?.textContent || "Investigate & Fix";
    if (button) {
      button.disabled = true;
      button.textContent = "Opening Chat...";
    }
    try {
      await enableDeveloperMode();
      const diagnosticName = String(item?.name || "Unknown diagnostic");
      const evidence = conciseEvidence(item);
      const prompt = `Investigate and fix this failed ZBRANO diagnostic: ${diagnosticName}.${evidence ? ` Evidence: ${evidence}` : ""}`;
      showReturnBanner(item);
      document.getElementById("chat-tab")?.click();
      const composer = document.getElementById("message");
      const chatForm = document.getElementById("chat-form");
      if (!composer || !chatForm) throw new Error("Chat composer is unavailable");
      composer.value = prompt;
      composer.dispatchEvent(new Event("input", {bubbles: true}));
      chatForm.requestSubmit();
      if (button) button.textContent = "Investigation opened in Chat";
    } catch (error) {
      if (developerSummary) developerSummary.textContent = `Could not start investigation: ${error.message || error}`;
      if (button) {
        button.disabled = false;
        button.textContent = originalLabel;
      }
    } finally {
      launchInProgress = false;
    }
  };
})();
</script>
'''
    frontend = replace_once(
        frontend,
        '<script id="zbrano-v0121-attach-recovery">',
        workflow_script + '\n<script id="zbrano-v0121-attach-recovery">',
        "diagnostic-to-chat workflow",
    )

    backend = backend.replace('version="0.12.23"', 'version="0.12.24"')
    backend = backend.replace('"version": "0.12.23"', '"version": "0.12.24"')
    frontend = frontend.replace("HUD 0.12.23", "HUD 0.12.24")

    require(frontend, 'fixButton.textContent = "Investigate & Fix"', "failed-check button")
    require(frontend, "await enableDeveloperMode();", "automatic Developer Mode")
    require(frontend, 'document.getElementById("chat-tab")?.click()', "Chat launch")
    require(frontend, "chatForm.requestSubmit();", "automatic investigation submission")
    require(frontend, "Return to diagnostic", "return action")
    require(backend, 'version="0.12.24"', "backend version")
    require(frontend, "HUD 0.12.24", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
