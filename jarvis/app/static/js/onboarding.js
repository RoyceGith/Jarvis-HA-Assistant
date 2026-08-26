"use strict";

(() => {
  const setupTab = document.querySelector('[data-settings-target="setup"]');
  const list = document.getElementById("onboarding-step-list");
  const progress = document.querySelector(".onboarding-progress");
  const progressBar = document.getElementById("onboarding-progress-bar");
  const progressLabel = document.getElementById("onboarding-progress-label");
  const message = document.getElementById("onboarding-message");
  const recheck = document.getElementById("onboarding-recheck");
  const complete = document.getElementById("onboarding-complete");
  const dismiss = document.getElementById("onboarding-dismiss");
  if (!setupTab || !list || !progress || !progressBar || !progressLabel || !message || !recheck || !complete || !dismiss) return;

  function openTarget(target) {
    if (target === "entities") return document.getElementById("entities-tab")?.click();
    if (target === "plugins") return document.getElementById("plugins-tab")?.click();
    if (target === "notifications") {
      document.getElementById("automations-tab")?.click();
      window.setTimeout(() => document.querySelector('[data-auto-view="notifications"]')?.click(), 0);
      return;
    }
    if (target === "model") {
      message.textContent = "Open the ZBRANO app Configuration page in Home Assistant to add or change the OpenAI API key.";
      return;
    }
    document.querySelector(`[data-settings-target="${CSS.escape(target)}"]`)?.click();
  }

  function render(data) {
    const steps = Array.isArray(data.steps) ? data.steps : [];
    const percentage = steps.length ? Math.round((Number(data.ready_count || 0) / steps.length) * 100) : 0;
    progressBar.style.width = `${percentage}%`;
    progress.setAttribute("aria-valuenow", String(percentage));
    progressLabel.textContent = `${data.ready_count || 0} of ${data.total_count || steps.length} ready`;
    list.replaceChildren();
    for (const step of steps) {
      const row = document.createElement("article");
      row.className = `onboarding-step${step.ready ? " is-ready" : ""}`;
      const state = document.createElement("span");
      state.className = "onboarding-step-state";
      state.textContent = step.ready ? "✓" : "•";
      state.setAttribute("aria-label", step.ready ? "Ready" : "Needs attention");
      const copy = document.createElement("div");
      copy.className = "onboarding-step-copy";
      const title = document.createElement("strong");
      title.textContent = step.title || step.id;
      if (step.required) {
        const required = document.createElement("span");
        required.className = "onboarding-required";
        required.textContent = "REQUIRED";
        title.append(required);
      }
      const description = document.createElement("small");
      description.textContent = step.description || "";
      copy.append(title, description);
      const action = document.createElement("button");
      action.type = "button";
      action.textContent = step.ready ? "Review" : "Configure";
      action.addEventListener("click", () => openTarget(String(step.target || "setup")));
      row.append(state, copy, action);
      list.append(row);
    }
    complete.disabled = Boolean(data.completed) || !data.core_ready;
    complete.textContent = data.completed ? "Setup complete" : "Finish setup";
    dismiss.hidden = Boolean(data.completed || data.dismissed || data.legacy_installation);
    message.textContent = data.legacy_installation
      ? "Existing installation detected. Your configuration was preserved; use this checklist whenever you want to review setup."
      : data.completed
        ? "Core setup is complete. Optional connections can be added at any time."
        : data.dismissed
          ? "Automatic setup is disabled. This guide remains available in Settings."
          : data.core_ready
            ? "Required services are ready. Finish setup now or continue with optional connections."
            : "Complete the required steps before finishing setup.";
  }

  async function load({openIfNeeded = false} = {}) {
    const response = await fetch("api/onboarding", {cache: "no-store"});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    render(data);
    if (openIfNeeded && data.show_on_startup) {
      document.getElementById("settings-tab")?.click();
      window.setTimeout(() => setupTab.click(), 0);
    }
    return data;
  }

  async function update(action) {
    const response = await fetch("api/onboarding", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({action}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    render(data);
  }

  setupTab.addEventListener("click", () => load().catch(error => { message.textContent = `Setup unavailable: ${error.message || error}`; }));
  recheck.addEventListener("click", () => load().catch(error => { message.textContent = `Recheck failed: ${error.message || error}`; }));
  complete.addEventListener("click", () => update("complete").catch(error => { message.textContent = error.message || String(error); }));
  dismiss.addEventListener("click", () => update("dismiss").catch(error => { message.textContent = error.message || String(error); }));
  load({openIfNeeded: true}).catch(() => {});
})();
