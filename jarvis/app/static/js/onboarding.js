"use strict";

(() => {
  const setupTab = document.querySelector('[data-settings-target="setup"]');
  const list = document.getElementById("onboarding-step-list");
  const progress = document.querySelector(".onboarding-progress");
  const progressBar = document.getElementById("onboarding-progress-bar");
  const progressLabel = document.getElementById("onboarding-progress-label");
  const message = document.getElementById("onboarding-message");
  const previous = document.getElementById("onboarding-previous");
  const skip = document.getElementById("onboarding-skip");
  const next = document.getElementById("onboarding-next");
  const summary = document.getElementById("onboarding-summary");
  const configurationHelp = document.createElement("aside");
  configurationHelp.id = "onboarding-configuration-help";
  configurationHelp.className = "onboarding-configuration-help";
  configurationHelp.setAttribute("aria-labelledby", "onboarding-configuration-title");
  configurationHelp.hidden = true;
  configurationHelp.innerHTML = `
    <div class="onboarding-configuration-heading">
      <div><span class="onboarding-kicker">HOME ASSISTANT APP SETTINGS</span><h3 id="onboarding-configuration-title">Connect the AI model</h3></div>
      <button id="onboarding-configuration-close" type="button" aria-label="Close configuration guide">Close</button>
    </div>
    <p>Your credential stays in Home Assistant's protected app configuration. ZBRANO never displays it on this page.</p>
    <ol>
      <li>In Home Assistant, open <strong>Settings → Apps → ZBRANO → Configuration</strong>.</li>
      <li>Paste your own OpenAI API key into <code>openai_api_key</code>. The default <code>openai_model</code> can be kept.</li>
      <li>Select <strong>Save</strong>, then restart the ZBRANO app so the protected setting is loaded.</li>
      <li>Return here and select <strong>Verify key</strong>. ZBRANO checks the connection without revealing the key.</li>
    </ol>
    <p class="onboarding-configuration-optional"><strong>Optional fields can stay blank.</strong> ElevenLabs, Google, GitHub, and Workshop Memory settings are only needed when you choose those capabilities later.</p>
    <div class="onboarding-configuration-actions">
      <button id="onboarding-configuration-copy" type="button">Copy field name</button>
      <button id="onboarding-configuration-verify" type="button">Verify after restart</button>
    </div>`;
  summary.after(configurationHelp);
  const configurationClose = document.getElementById("onboarding-configuration-close");
  const configurationCopy = document.getElementById("onboarding-configuration-copy");
  const configurationVerify = document.getElementById("onboarding-configuration-verify");
  const guideActions = document.querySelector(".onboarding-guide-actions");
  const checkRequired = document.getElementById("onboarding-check-required");
  const recheck = document.getElementById("onboarding-recheck");
  const complete = document.getElementById("onboarding-complete");
  const dismiss = document.getElementById("onboarding-dismiss");
  if (!setupTab || !list || !progress || !progressBar || !progressLabel || !message || !previous || !skip || !next || !summary || !configurationHelp || !configurationClose || !configurationCopy || !configurationVerify || !guideActions || !checkRequired || !recheck || !complete || !dismiss) return;
  let latestData = null;
  let reviewingCompleted = false;

  function openTarget(target) {
    configurationHelp.hidden = true;
    if (target === "entities") {
      document.getElementById("entities-tab")?.click();
      window.setTimeout(() => window.zbranoOpenEntityPermissionGuide?.(), 0);
      return;
    }
    if (target === "plugins") return document.getElementById("plugins-tab")?.click();
    if (target === "notifications") {
      document.getElementById("automations-tab")?.click();
      window.setTimeout(() => document.querySelector('[data-auto-view="notifications"]')?.click(), 0);
      return;
    }
    if (target === "model") {
      configurationHelp.hidden = false;
      message.textContent = "Follow the four steps below. Keep the API key in Home Assistant's protected app configuration.";
      configurationHelp.scrollIntoView({behavior: "smooth", block: "nearest"});
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

  const stepMeta = {
    home_assistant: {symbol: "HA", eyebrow: "CORE CONNECTION", guidance: "This connection lets ZBRANO see Home Assistant and use only the entities you approve."},
    model: {symbol: "AI", eyebrow: "INTELLIGENCE", guidance: "The AI model powers chat and reasoning. Your key stays in the protected Home Assistant app configuration."},
    entities: {symbol: "ID", eyebrow: "PERMISSIONS", guidance: "You choose exactly which sensors ZBRANO may read and which devices it may control."},
    voice: {symbol: "VO", eyebrow: "VOICE", guidance: "Voice is optional. Configure speech, test playback, and enable the wake word only if you want hands-free use."},
    memory: {symbol: "ME", eyebrow: "MEMORY", guidance: "Fast Memory helps ZBRANO remember useful preferences and context locally between conversations."},
    plugins: {symbol: "PL", eyebrow: "CONNECTIONS", guidance: "Plugins connect optional services. You can skip this now and install only the services you trust later."},
    notifications: {symbol: "NT", eyebrow: "NOTIFICATIONS", guidance: "Choose where ZBRANO should send alerts and automation messages. This can be changed at any time."},
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
      await load();
      message.textContent = data.ready ? `${step.title} check passed.` : `${step.title}: ${data.detail || "needs attention"}`;
    } catch (error) {
      await load().catch(() => {});
      message.textContent = `${step.title || step.id} check failed: ${error.message || error}. Open its configuration action, correct the setting, then check again.`;
    } finally {
      button.disabled = false;
      button.textContent = checkLabels[step.id] || "Check";
    }
  }

  async function copyInstallationSummary(text, button, copiedLabel = "Copied", resetLabel = "Copy support summary") {
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
      else {
        const field = document.createElement("textarea");
        field.value = text;
        field.style.position = "fixed";
        field.style.opacity = "0";
        document.body.append(field);
        field.select();
        if (!document.execCommand("copy")) throw new Error("Copy is unavailable");
        field.remove();
      }
      button.textContent = copiedLabel;
      window.setTimeout(() => { button.textContent = resetLabel; }, 1600);
    } catch (error) {
      message.textContent = `Could not copy this text: ${error.message || error}`;
    }
  }

  configurationClose.addEventListener("click", () => {
    configurationHelp.hidden = true;
    message.textContent = "Configuration help closed. You can reopen it from the AI model setup step.";
  });
  configurationCopy.addEventListener("click", () => copyInstallationSummary("openai_api_key", configurationCopy, "Copied field name", "Copy field name"));
  configurationVerify.addEventListener("click", () => {
    const modelStep = [...list.querySelectorAll(".onboarding-step")].find(row => row.querySelector("strong")?.textContent.includes("AI model"));
    const check = modelStep?.querySelector(".onboarding-step-actions button:first-child");
    if (check) check.click();
  });

  function installationReportElement(data) {
    const report = data.installation_report || {};
    const details = document.createElement("details");
    details.className = "onboarding-installation-report";
    details.open = !report.ready;
    const heading = document.createElement("summary");
    heading.textContent = `Installation report · ${report.ready ? "Ready" : `${report.attention_count || 0} need attention`}`;
    const checks = document.createElement("div");
    checks.className = "onboarding-report-checks";
    for (const check of report.checks || []) {
      const row = document.createElement("div");
      row.className = "onboarding-report-check";
      row.dataset.state = check.state || "optional";
      const marker = document.createElement("span");
      marker.textContent = check.state === "ready" ? "OK" : check.state === "attention" ? "!" : "—";
      const copy = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = check.title || check.id;
      const detail = document.createElement("small");
      detail.textContent = check.detail || "";
      copy.append(title, detail);
      row.append(marker, copy);
      checks.append(row);
    }
    const privacy = document.createElement("p");
    privacy.textContent = "Safe to share: this report excludes keys, tokens, entity IDs, messages, and personal data.";
    const actions = document.createElement("div");
    actions.className = "onboarding-report-actions";
    const copy = document.createElement("button");
    copy.type = "button";
    copy.textContent = "Copy support summary";
    copy.addEventListener("click", () => copyInstallationSummary(String(report.support_summary || ""), copy));
    const download = document.createElement("button");
    download.type = "button";
    download.textContent = "Download report";
    download.addEventListener("click", () => {
      const payload = {version: report.version, generated_at: report.generated_at, ready: report.ready, checks: report.checks || [], support_summary: report.support_summary || ""};
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], {type: "application/json"}));
      const link = document.createElement("a");
      link.href = url;
      link.download = `zbrano-installation-report-${report.version || "current"}.json`;
      link.click();
      URL.revokeObjectURL(url);
    });
    const refresh = document.createElement("button");
    refresh.type = "button";
    refresh.textContent = "Refresh report";
    refresh.addEventListener("click", () => load().catch(error => { message.textContent = `Report refresh failed: ${error.message || error}`; }));
    actions.append(copy, download, refresh);
    details.append(heading, checks, privacy, actions);
    return details;
  }

  function renderCompletion(data, steps) {
    configurationHelp.hidden = true;
    const ready = steps.filter(step => step.ready);
    const later = steps.filter(step => !step.ready);
    const card = document.createElement("article");
    card.className = "onboarding-complete-card";
    const mark = document.createElement("span");
    mark.className = "onboarding-complete-mark";
    mark.textContent = "OK";
    mark.setAttribute("aria-hidden", "true");
    const title = document.createElement("h3");
    title.textContent = "ZBRANO is ready";
    const description = document.createElement("p");
    description.textContent = "Core setup is complete. You can start chatting now and add optional capabilities whenever you need them.";
    const capabilityList = document.createElement("div");
    capabilityList.className = "onboarding-capability-list";
    for (const step of ready) {
      const chip = document.createElement("span");
      chip.className = "is-ready";
      chip.textContent = `${step.title} ready`;
      capabilityList.append(chip);
    }
    for (const step of later) {
      const chip = document.createElement("span");
      chip.textContent = `${step.title} available later`;
      capabilityList.append(chip);
    }
    const actions = document.createElement("div");
    actions.className = "onboarding-complete-actions";
    const start = document.createElement("button");
    start.type = "button";
    start.className = "primary";
    start.textContent = "Start chatting";
    start.addEventListener("click", () => document.getElementById("chat-tab")?.click());
    const review = document.createElement("button");
    review.type = "button";
    review.textContent = "Review connections";
    review.addEventListener("click", () => {
      reviewingCompleted = true;
      render(data);
    });
    actions.append(start, review);
    card.append(mark, title, description, capabilityList, installationReportElement(data), actions);
    list.replaceChildren(card);
    guideActions.hidden = true;
    summary.hidden = true;
    checkRequired.hidden = true;
    recheck.hidden = true;
    complete.hidden = true;
    dismiss.hidden = true;
    message.textContent = "Setup complete. Optional connections remain available in Settings.";
  }

  function render(data) {
    latestData = data;
    const steps = Array.isArray(data.steps) ? data.steps : [];
    const storedIndex = Math.max(0, steps.findIndex(step => step.id === data.current_step));
    const blockedIndex = steps.findIndex(step => step.required && !(step.ready && step.last_check?.ready));
    const activeIndex = blockedIndex >= 0 && storedIndex > blockedIndex ? blockedIndex : storedIndex;
    const percentage = steps.length ? Math.round((Number(data.ready_count || 0) / steps.length) * 100) : 0;
    progressBar.style.width = `${percentage}%`;
    progress.setAttribute("aria-valuenow", String(percentage));
    progressLabel.textContent = `${data.ready_count || 0} of ${data.total_count || steps.length} ready`;
    if (data.completed && !reviewingCompleted) {
      renderCompletion(data, steps);
      return;
    }
    guideActions.hidden = false;
    summary.hidden = false;
    checkRequired.hidden = false;
    recheck.hidden = false;
    complete.hidden = false;
    list.replaceChildren();
    const rail = document.createElement("nav");
    rail.className = "onboarding-step-rail";
    rail.setAttribute("aria-label", "Setup steps");
    for (const [index, step] of steps.entries()) {
      const railStep = document.createElement("button");
      railStep.type = "button";
      railStep.className = `onboarding-rail-step${step.ready ? " is-ready" : ""}${index === activeIndex ? " is-active" : ""}${step.skipped ? " is-skipped" : ""}`;
      railStep.disabled = blockedIndex >= 0 && index > blockedIndex;
      if (index === activeIndex) railStep.setAttribute("aria-current", "step");
      const marker = document.createElement("span");
      marker.textContent = step.ready ? "OK" : String(index + 1);
      const label = document.createElement("small");
      label.textContent = step.title || step.id;
      railStep.append(marker, label);
      railStep.addEventListener("click", () => saveProgress(step.id).catch(error => {
        message.textContent = `Could not open this setup step: ${error.message || error}`;
      }));
      rail.append(railStep);
    }
    list.append(rail);
    for (const [index, step] of steps.entries()) {
      const row = document.createElement("article");
      row.className = `onboarding-step${step.ready ? " is-ready" : ""}${index === activeIndex ? " is-active" : ""}${step.skipped ? " is-skipped" : ""}`;
      if (index === activeIndex) row.setAttribute("aria-current", "step");
      const state = document.createElement("span");
      state.className = "onboarding-step-state";
      state.textContent = step.ready ? "✓" : "•";
      state.setAttribute("aria-label", step.ready ? "Ready" : "Needs attention");
      const meta = stepMeta[step.id] || {symbol: String(index + 1), eyebrow: "SETUP", guidance: "Configure this capability, then check it before continuing."};
      state.textContent = meta.symbol;
      const copy = document.createElement("div");
      copy.className = "onboarding-step-copy";
      const eyebrow = document.createElement("small");
      eyebrow.className = "onboarding-focus-eyebrow";
      eyebrow.textContent = meta.eyebrow;
      const title = document.createElement("strong");
      title.textContent = step.title || step.id;
      if (step.required) {
        const required = document.createElement("span");
        required.className = "onboarding-required";
        required.textContent = "REQUIRED";
        title.append(required);
      } else if (step.skipped) {
        const skipped = document.createElement("span");
        skipped.className = "onboarding-skipped";
        skipped.textContent = "SKIPPED";
        title.append(skipped);
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
        verification.textContent = step.skipped ? "Skipped for now; you can configure this later" : "Not verified yet";
      }
      const guidance = document.createElement("p");
      guidance.className = "onboarding-focus-guidance";
      guidance.textContent = meta.guidance;
      copy.append(eyebrow, title, description, guidance, verification);
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
    const activeStep = steps[activeIndex] || null;
    previous.disabled = activeIndex <= 0;
    next.disabled = !activeStep || (Boolean(activeStep.required) && !(Boolean(activeStep.ready) && Boolean(activeStep.last_check?.ready)));
    next.textContent = activeIndex >= steps.length - 1 ? "Review summary" : "Continue";
    skip.hidden = !activeStep || Boolean(activeStep.required) || Boolean(activeStep.ready);
    const requiredSteps = steps.filter(step => step.required);
    const optionalSteps = steps.filter(step => !step.required);
    const requiredVerified = requiredSteps.filter(step => step.last_check?.ready).length;
    const optionalReady = optionalSteps.filter(step => step.ready).length;
    const skippedCount = optionalSteps.filter(step => step.skipped).length;
    summary.textContent = `Setup summary: ${requiredVerified}/${requiredSteps.length} required checks passed; ${optionalReady}/${optionalSteps.length} optional capabilities ready${skippedCount ? `; ${skippedCount} skipped for now` : ""}.`;
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

  async function saveProgress(stepId, skippedStep = null) {
    configurationHelp.hidden = true;
    const response = await fetch("api/onboarding/progress", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({step_id: stepId, skipped_step: skippedStep}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    render(data);
    return data;
  }

  async function moveGuide(direction, skipCurrent = false) {
    const steps = Array.isArray(latestData?.steps) ? latestData.steps : [];
    const storedIndex = Math.max(0, steps.findIndex(step => step.id === latestData?.current_step));
    const blockedIndex = steps.findIndex(step => step.required && !(step.ready && step.last_check?.ready));
    const index = blockedIndex >= 0 && storedIndex > blockedIndex ? blockedIndex : storedIndex;
    const current = steps[index];
    const targetIndex = Math.max(0, Math.min(steps.length - 1, index + direction));
    if (!current || targetIndex === index) {
      summary.scrollIntoView({behavior: "smooth", block: "nearest"});
      return;
    }
    try {
      await saveProgress(steps[targetIndex].id, skipCurrent ? current.id : null);
    } catch (error) {
      message.textContent = `Setup navigation failed: ${error.message || error}`;
    }
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
    if (action === "complete") reviewingCompleted = false;
    render(data);
  }

  setupTab.addEventListener("click", () => load().catch(error => { message.textContent = `Setup unavailable: ${error.message || error}`; }));
  previous.addEventListener("click", () => moveGuide(-1));
  next.addEventListener("click", () => moveGuide(1));
  skip.addEventListener("click", () => moveGuide(1, true));
  checkRequired.addEventListener("click", runRequiredChecks);
  recheck.addEventListener("click", () => load().catch(error => { message.textContent = `Refresh failed: ${error.message || error}`; }));
  complete.addEventListener("click", () => update("complete").catch(error => { message.textContent = error.message || String(error); }));
  dismiss.addEventListener("click", () => update("dismiss").catch(error => { message.textContent = error.message || String(error); }));
  load({openIfNeeded: true}).catch(() => {});
})();
