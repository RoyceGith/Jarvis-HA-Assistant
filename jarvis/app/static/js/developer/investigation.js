(() => {
  const feature = document.getElementById("developer-feature");
  const symptom = document.getElementById("developer-symptom");
  const run = document.getElementById("developer-investigate");
  const summary = document.getElementById("developer-investigation-summary");
  const results = document.getElementById("developer-investigation-results");
  if (!feature || !symptom || !run || !summary || !results) return;

  const runtimeErrors = [];
  const remember = value => {
    const message = String(value?.message || value || "Unknown browser error");
    if (!runtimeErrors.includes(message)) runtimeErrors.push(message);
    while (runtimeErrors.length > 10) runtimeErrors.shift();
  };
  window.addEventListener("error", event => remember(event.message));
  window.addEventListener("unhandledrejection", event => remember(event.reason));

  async function loadFeatures() {
    const response = await fetch("api/developer/features", {cache: "no-store"});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    for (const item of data.features || []) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.title;
      feature.appendChild(option);
    }
  }

  function controllerEvidence(featureId) {
    if (featureId === "attachments") {
      const controller = window.zbranoAttachmentController || {};
      return {ready: Boolean(controller.ready), lastUploadOk: controller.lastUploadOk, lastError: controller.lastError || ""};
    }
    if (featureId === "shared_files") {
      const controller = window.zbranoSharedFilesController || {};
      return {ready: Boolean(controller.ready), lastAction: controller.lastAction || "", lastActionOk: controller.lastActionOk, lastError: controller.lastError || ""};
    }
    return {};
  }

  function collectBrowserEvidence(featureId) {
    const controlIds = {
      attachments: ["attach-file", "attachment-input", "chat-attachments"],
      shared_files: ["shared-use", "shared-delete", "shared-file-rows"],
      new_chat: ["new-chat-button", "chat-form"],
      plugin_catalog: ["plugins-tab", "catalog-results"],
      plugins: ["plugins-tab", "plugin-list"],
      automations: ["automations-tab", "automations-panel", "automation-library"],
      entities: ["entities-tab", "entities-panel"],
      settings: ["settings-tab", "settings-panel"],
      voice: ["mic-button", "stop-button"],
      developer: ["developer-tab", "developer-panel"],
    };
    const controls = {};
    for (const id of controlIds[featureId] || []) controls[id] = Boolean(document.getElementById(id));
    return {
      errors: [...runtimeErrors],
      controller: controllerEvidence(featureId),
      controls,
      location: window.location.href,
      user_agent: navigator.userAgent,
    };
  }

  function render(data) {
    results.replaceChildren();
    for (const item of data.evidence || []) {
      const row = document.createElement("div");
      row.className = `developer-investigation-result ${item.status || ""}`;
      const title = document.createElement("strong");
      title.textContent = `${item.name} · ${item.status}`;
      const detail = document.createElement("div");
      detail.className = "muted";
      detail.textContent = item.detail || "";
      row.append(title, detail);
      results.appendChild(row);
    }
    const files = (data.relevant_files || []).join(", ");
    const boundary = data.likely_fault_boundary || "unknown";
    summary.textContent = `${data.summary || "Investigation complete"} Fault boundary: ${boundary}. Relevant files: ${files}`;
  }

  async function investigate() {
    const report = symptom.value.trim();
    if (report.length < 3) {
      summary.textContent = "Describe the observed problem before investigating.";
      symptom.focus();
      return;
    }
    run.disabled = true;
    summary.textContent = "Running one targeted adapter (maximum 20 seconds)…";
    results.replaceChildren();
    try {
      const featureId = feature.value;
      const response = await fetch("api/developer/investigate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          feature: featureId,
          symptom: report,
          browser_evidence: collectBrowserEvidence(featureId),
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
      render(data);
      window.zbranoInvestigationEngine.lastResult = data;
    } catch (error) {
      summary.textContent = `Investigation failed: ${error.message || error}`;
    } finally {
      run.disabled = false;
    }
  }

  window.zbranoInvestigationEngine = {
    ready: true,
    investigate,
    collectBrowserEvidence,
    runtimeErrors,
    lastResult: null,
  };
  run.addEventListener("click", investigate);
  loadFeatures().catch(error => { summary.textContent = `Feature list failed: ${error.message || error}`; });
})();
