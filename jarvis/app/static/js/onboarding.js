"use strict";

(() => {
  const setupTab = document.querySelector('[data-settings-target="setup"]');
  const list = document.getElementById("onboarding-step-list");
  const progress = document.querySelector(".onboarding-progress");
  const progressBar = document.getElementById("onboarding-progress-bar");
  const progressLabel = document.getElementById("onboarding-progress-label");
  const message = document.getElementById("onboarding-message");
  const checkRequired = document.getElementById("onboarding-check-required");
  const recheck = document.getElementById("onboarding-recheck");
  const complete = document.getElementById("onboarding-complete");
  const dismiss = document.getElementById("onboarding-dismiss");
  if (!setupTab || !list || !progress || !progressBar || !progressLabel || !checkRequired || !recheck || !complete || !dismiss) return;

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

  const actionLabels = {
    entities: "Choose entities",
    model: "Configuration help",
    voice: "Open voice test",
    memory: "Open memory",
    plugins: "Open plugins",
    notifications: "Open notification test",
  };

  const checkLabels = {
    home_assistant: "Test connection",
    model: "Verify key",
    entities: "Recheck",
    voice: "Check provider",
    memory: "Check memory",
    plugins: "Check plugins",
    notifications: "Validate channels",
  };

  async function requestCheck(stepId) {
    const response = await fetch(`api/onboarding/check/${encodeURIComponent(stepId)}`, {method: "POST"});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  async function checkStep(step, row, state, description, verification, button) {
    button.disabled = true;
    button.textContent = "Checking…";
    message.textContent = `Checking ${step.title || step.id}…`;
    try {
      const data = await requestCheck(step.id);
      row.classList.toggle("is-ready", Boolean(data.ready));
      state.textContent = data.ready ? "✓" : "•";
      state.setAttribute("aria-label", data.ready ? "Ready" : "Needs attention");
      description.textContent = data.detail || step.description || "";
      verification.textContent = `${data.ready ? "Verified" : "Checked"} just now`;
      message.textContent = data.ready ? `${step.title} check passed.` : `${step.title}: ${data.detail || "needs attention"}`;
    } catch (error) {
      message.textContent = `${step.title || step.id} check failed: ${error.message || error}`;
    } finally {
      button.disabled = false;
      button.textContent = checkLabels[step.id] || "Check";
    }
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
      const verification = document.createElement("small");
      verification.className = "onboarding-verification";
      const lastCheck = step.last_check;
      if (lastCheck && Number(lastCheck.checked_at || 0) > 0) {
        const checked = new Date(Number(lastCheck.checked_at) * 1000);
        verification.textContent = `${lastCheck.ready ? "Verified" : "Last check failed"} ${checked.toLocaleString()}`;
      } else {
        verification.textContent = "Not verified yet";
      }
      copy.append(title, description, verification);
      const actions = document.createElement("div");
      actions.className = "onboarding-step-actions";
      const check = document.createElement("button");
      check.type = "button";
      check.textContent = checkLabels[step.id] || "Check";
      check.addEventListener("click", () => checkStep(step, row, state, description, verification, check));
      const action = document.createElement("button");
      action.type = "button";
      action.textContent = actionLabels[step.target] || (step.ready ? "Review" : "Configure");
      action.addEventListener("click", () => openTarget(String(step.target || "setup")));
      actions.append(check, action);
      row.append(state, copy, actions);
      list.append(row);
    }
    complete.disabled = Boolean(data.completed) || !data.core_ready || !data.required_verified;
    complete.textContent = data.completed ? "Setup complete" : "Finish setup";
    dismiss.hidden = Boolean(data.completed || data.dismissed || data.legacy_installation);
    message.textContent = data.legacy_installation
      ? "Existing installation detected. Your configuration was preserved; use this checklist whenever you want to review setup."
      : data.completed
        ? "Core setup is complete. Optional connections can be added at any time."
        : data.dismissed
          ? "Automatic setup is disabled. This guide remains available in Settings."
          : data.core_ready && data.required_verified
            ? "Required services are configured and verified. Finish setup now or continue with optional connections."
            : data.core_ready
              ? "Required services look configured. Run the required checks before finishing setup."
            : "Complete the required steps before finishing setup.";
  }

  async function runRequiredChecks() {
    checkRequired.disabled = true;
    checkRequired.textContent = "Checking…";
    try {
      for (const stepId of ["home_assistant", "model"]) {
        message.textContent = `Checking ${stepId === "home_assistant" ? "Home Assistant" : "AI model"}…`;
        const result = await requestCheck(stepId);
        if (!result.ready) throw new Error(result.detail || `${stepId} is not ready`);
      }
      await load();
      message.textContent = "Required checks passed. You can finish setup.";
    } catch (error) {
      await load().catch(() => {});
      message.textContent = `Required check failed: ${error.message || error}`;
    } finally {
      checkRequired.disabled = false;
      checkRequired.textContent = "Run required checks";
    }
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
  checkRequired.addEventListener("click", runRequiredChecks);
  recheck.addEventListener("click", () => load().catch(error => { message.textContent = `Recheck failed: ${error.message || error}`; }));
  complete.addEventListener("click", () => update("complete").catch(error => { message.textContent = error.message || String(error); }));
  dismiss.addEventListener("click", () => update("dismiss").catch(error => { message.textContent = error.message || String(error); }));
  load({openIfNeeded: true}).catch(() => {});
})();
