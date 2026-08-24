(() => {
  const tab = document.getElementById("developer-tab");
  const panel = document.getElementById("developer-panel");
  const toggle = document.getElementById("developer-toggle");
  const run = document.getElementById("developer-run-diagnostics");
  const summary = document.getElementById("developer-summary");
  const checks = document.getElementById("developer-checks");
  const interfaceStatus = document.getElementById("developer-interface-status");
  const modeIndicator = document.getElementById("developer-mode-indicator");
  if (!tab || !panel || !toggle || !run || !checks || !modeIndicator) return;

  const clientErrors = [];
  const rememberError = message => {
    const value = String(message || "Unknown client error");
    if (!clientErrors.includes(value)) clientErrors.push(value);
    while (clientErrors.length > 10) clientErrors.shift();
    renderInterfaceStatus();
  };
  window.addEventListener("error", event => rememberError(event.message));
  window.addEventListener("unhandledrejection", event => rememberError(event.reason?.message || event.reason));

  function renderInterfaceStatus() {
    if (!interfaceStatus) return;
    const required = ["new-chat-button", "files-tab", "attach-file", "plugins-tab", "entities-tab", "developer-tab"];
    const missing = required.filter(id => !document.getElementById(id));
    if (!clientErrors.length && !missing.length) {
      interfaceStatus.textContent = "Interface monitor healthy · required controls present · no captured JavaScript errors.";
      return;
    }
    const parts = [];
    if (missing.length) parts.push(`Missing controls: ${missing.join(", ")}`);
    if (clientErrors.length) parts.push(`Recent errors: ${clientErrors.join(" | ")}`);
    interfaceStatus.textContent = parts.join(" · ");
  }

  function hideDeveloperPanel() {
    panel.classList.add("hidden");
    tab.classList.remove("active");
  }

  function activateDeveloperPanel() {
    for (const id of ["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel", "calendar-panel", "developer-panel"]) {
      document.getElementById(id)?.classList.toggle("hidden", id !== "developer-panel");
    }
    for (const id of ["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab", "calendar-tab", "developer-tab"]) {
      document.getElementById(id)?.classList.toggle("active", id === "developer-tab");
    }
  }

  function syncToggle(enabled) {
    toggle.dataset.enabled = enabled ? "true" : "false";
    toggle.setAttribute("aria-pressed", enabled ? "true" : "false");
    toggle.textContent = enabled ? "Disable Developer Mode" : "Enable Developer Mode";
    modeIndicator.hidden = !enabled;
    modeIndicator.textContent = enabled ? "Developer Mode Active" : "";
  }

  async function loadStatus() {
    const response = await fetch("api/developer/status", {cache: "no-store"});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    syncToggle(Boolean(data.enabled));
    return data;
  }

  async function runDiagnostics() {
    summary.textContent = "Running diagnostics…";
    run.disabled = true;
    try {
      const response = await fetch("api/developer/diagnostics", {cache: "no-store"});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      const browserChecks = [
        {
          name: "Attachment controller wired",
          ok: Boolean(window.zbranoAttachRecovery?.installed && window.zbranoAttachmentController?.ready && typeof window.zbranoAttachmentController.uploadSelectedFiles === "function"),
          status: "wired",
          category: "frontend",
          detail: window.zbranoAttachmentController?.ready ? "picker, uploader, pending IDs, and chip renderer active" : "attachment controller unavailable",
        },
        {
          name: "Shared Files action controller wired",
          status: "wired",
          category: "frontend",
          ok: Boolean(window.zbranoSharedFilesController?.ready && typeof window.zbranoSharedFilesController.deleteSelected === "function" && typeof window.zbranoSharedFilesController.attachSelected === "function"),
          detail: window.zbranoSharedFilesController?.ready ? "select, attach, and delete handlers active" : "Shared Files action controller unavailable",
        },
        {
          name: "New Chat runtime available",
          ok: typeof createNewChat === "function" && Boolean(document.getElementById("new-chat-button")),
          detail: typeof createNewChat === "function" ? "createNewChat callable" : "createNewChat unavailable",
        },
        {
          name: "Shared Files runtime available",
          ok: typeof window.zbranoLoadSharedFiles === "function" && Boolean(document.getElementById("files-panel")),
          detail: typeof window.zbranoLoadSharedFiles === "function" ? "recovery loader callable" : "recovery loader unavailable",
        },
        {
          name: "Plugin settings runtime available",
          ok: Boolean(document.querySelector("#zbrano-v01131-plugin-compact")) && Boolean(document.getElementById("plugins-panel")),
          detail: document.querySelector("#zbrano-v01131-plugin-compact") ? "compact settings controller loaded" : "controller unavailable",
        },
        {
          name: "Developer runtime available",
          ok: Boolean(document.querySelector("#zbrano-v0120-developer-mode")) && Boolean(document.getElementById("developer-panel")),
          detail: "developer controller and panel",
        },
      ];
      data.checks = [...(data.checks || []), ...browserChecks];
      for (const item of data.checks) {
        if (!item.status) item.status = item.ok ? "wired" : "failed";
      }
      data.total = data.checks.length;
      data.passed = data.checks.filter(item => item.status !== "failed").length;
      data.failed = data.checks.filter(item => item.status === "failed").length;
      data.degraded = data.checks.filter(item => item.status === "degraded").length;
      data.healthy = data.failed === 0;
      checks.replaceChildren();
      for (const item of data.checks || []) {
        const card = document.createElement("div");
        const status = item.status || (item.ok ? "wired" : "failed");
        card.className = `developer-check ${status === "failed" ? "fail" : status}`;
        const title = document.createElement("strong");
        const symbol = status === "failed" ? "✕" : status === "degraded" ? "!" : "✓";
        title.textContent = `${symbol} ${item.name} · ${status}`;
        const detail = document.createElement("div");
        detail.className = "muted";
        detail.textContent = item.repair_hint
          ? `${item.detail || ""} · Repair hint: ${item.repair_hint}`
          : (item.detail || "");
        card.dataset.diagnosticName = item.name || "Unknown diagnostic";
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
        checks.appendChild(card);
      }
      summary.textContent = `${data.passed}/${data.total} non-failing · ${data.degraded || 0} degraded · ${data.failed || 0} failed`;
      syncToggle(Boolean(data.developer_mode));
      renderInterfaceStatus();
    } catch (error) {
      summary.textContent = `Diagnostics failed: ${error.message || error}`;
    } finally {
      run.disabled = false;
    }
  }

  tab.addEventListener("click", event => {
    event.preventDefault();
    event.stopPropagation();
    activateDeveloperPanel();
    loadStatus().catch(error => { summary.textContent = `Developer status failed: ${error.message || error}`; });
    runDiagnostics();
  }, true);

  // Existing navigation predates Developer Mode. Hide this panel whenever an
  // older navigation control is used so it cannot overlay Chat/Files/Plugins.
  for (const id of ["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab", "new-chat-button"]) {
    document.getElementById(id)?.addEventListener("click", hideDeveloperPanel, true);
  }

  toggle.addEventListener("click", async () => {
    const next = toggle.dataset.enabled !== "true";
    toggle.disabled = true;
    try {
      const response = await fetch("api/developer/mode", {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({enabled: next}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      syncToggle(Boolean(data.enabled));
      summary.textContent = data.enabled
        ? "Developer Mode active. Chat may now maintain the ZBRANO repository using approval-gated GitHub tools."
        : "Developer Mode disabled.";
    } catch (error) {
      summary.textContent = `Could not change Developer Mode: ${error.message || error}`;
    } finally {
      toggle.disabled = false;
    }
  });

  run.addEventListener("click", runDiagnostics);
  renderInterfaceStatus();
  loadStatus().catch(error => {
    modeIndicator.hidden = true;
    summary.textContent = `Developer status failed: ${error.message || error}`;
  });
})();
