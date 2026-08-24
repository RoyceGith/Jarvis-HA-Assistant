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
