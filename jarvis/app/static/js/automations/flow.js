"use strict";

(() => {
  const operatorLabels = {
    any_change: "changes",
    changes_to: "changes to",
    equals: "equals",
    not_equals: "does not equal",
    above: "rises above",
    below: "falls below",
  };

  function text(value, fallback) {
    const cleaned = String(value ?? "").trim();
    return cleaned || fallback;
  }

  function node(kind, label, title, detail, steps = []) {
    const element = document.createElement("section");
    element.className = `automation-flow-node is-${kind}`;
    element.dataset.flowKind = kind;
    element.tabIndex = 0;
    element.setAttribute("role", "button");
    element.setAttribute("aria-label", `Configure ${label.toLowerCase()} block`);
    const kicker = document.createElement("span");
    kicker.className = "automation-flow-kicker";
    kicker.textContent = label;
    const heading = document.createElement("strong");
    heading.textContent = title;
    const description = document.createElement("small");
    description.textContent = detail;
    element.append(kicker, heading, description);
    appendSubsteps(element, steps);
    return element;
  }

  function connector() {
    const element = document.createElement("span");
    element.className = "automation-flow-connector";
    element.setAttribute("aria-hidden", "true");
    element.textContent = "→";
    return element;
  }

  function appendSubsteps(element, steps) {
    if (!steps.length) return;
    const list = document.createElement("div");
    list.className = "automation-flow-substeps";
    for (const step of steps) {
      const item = document.createElement("span");
      item.className = "automation-flow-substep";
      item.textContent = step;
      list.append(item);
    }
    element.append(list);
  }

  function create(automation = {}, entityName = value => value) {
    const flow = document.createElement("div");
    flow.className = "automation-flow";
    flow.setAttribute("role", "group");
    flow.setAttribute("aria-label", `${text(automation.name, "Automation")} visual flow`);

    const primaryTrigger = Array.isArray(automation.triggers) && automation.triggers.length ? automation.triggers[0] : {kind:"entity",entity_id:automation.trigger_entity,operator:automation.trigger_operator,value:automation.trigger_value,for_seconds:automation.trigger_for_seconds};
    const triggerKind = primaryTrigger.kind || "entity";
    const scheduleTitle = triggerKind === "time" ? `At ${primaryTrigger.at || "a local time"}` : triggerKind === "sun" ? `${primaryTrigger.sun_event || "sunrise"} ${Number(primaryTrigger.offset_minutes||0) >= 0 ? "+" : ""}${Number(primaryTrigger.offset_minutes||0)} min` : triggerKind === "interval" ? `Every ${Number(primaryTrigger.interval_minutes||5)} min` : triggerKind === "one_time" ? text(primaryTrigger.one_time_at,"Choose a date and time") : "";
    const triggerEntity = triggerKind === "entity" ? text(primaryTrigger.entity_id || automation.trigger_entity, "Choose a trigger entity") : scheduleTitle;
    const triggerValue = text(primaryTrigger.value || automation.trigger_value, "any value");
    const operator = operatorLabels[primaryTrigger.operator || automation.trigger_operator] || text(primaryTrigger.operator || automation.trigger_operator, "changes to");
    const duration = Number(primaryTrigger.for_seconds || automation.trigger_for_seconds || 0);
    const triggers = Array.isArray(automation.triggers) ? automation.triggers.filter(item => item && typeof item === "object") : [];
    const scheduleDays = Array.isArray(primaryTrigger.weekdays)&&primaryTrigger.weekdays.length ? ` · ${primaryTrigger.weekdays.length} selected day${primaryTrigger.weekdays.length===1?"":"s"}` : "";
    const triggerDetail = triggerKind === "entity" ? `${operator} ${triggerValue}${duration > 0 ? ` for ${duration} seconds` : ""}${triggers.length > 1 ? ` · ${triggers.length} OR triggers` : ""}` : `Local Home Assistant schedule${scheduleDays}${triggers.length > 1 ? ` · ${triggers.length} OR triggers` : ""}`;

    const presence = text(automation.presence_entity, "");
    const signals = Array.isArray(automation.signal_entities) ? automation.signal_entities.filter(Boolean) : [];
    const contextTitle = presence ? entityName(presence) : signals.length ? `${signals.length} context signal${signals.length === 1 ? "" : "s"}` : "No presence requirement";
    const conditions = Array.isArray(automation.conditions) ? automation.conditions.filter(item => item && typeof item === "object") : [];
    const conditionDetail = conditions.length ? `${conditions.length} ${String(automation.condition_mode || "all").toUpperCase()} condition${conditions.length === 1 ? "" : "s"}` : "";
    const contextDetail = presence
      ? `Presence confirmed${signals.length ? ` · ${signals.length} supporting signal${signals.length === 1 ? "" : "s"}` : ""}`
      : signals.length ? signals.slice(0, 2).map(entityName).join(" · ") : "Evaluate from the trigger alone";

    const confidence = Math.round(Number(automation.confidence_threshold ?? 0.75) * 100);
    const authority = text(automation.execution_policy, "suggest").replaceAll("_", " ");
    const branches = Array.isArray(automation.branches) ? automation.branches.filter(item => item && typeof item === "object") : [];
    const decisionTitle = branches.length ? `${branches.length} first-match branch${branches.length === 1 ? "" : "es"}` : text(automation.proposal_template, text(automation.objective, "Record the match"));
    const reoffer = Number(automation.reoffer_delta || 0);
    const reset = Number(automation.reset_delta || 0);
    const episodePolicy = `${reoffer > 0 ? `${reoffer} worsening` : "auto reconsider"} · ${reset > 0 ? `${reset} reset margin` : "threshold reset"}`;
    const decisionDetail = `${confidence}% confidence · ${authority} · ${Number(automation.cooldown_minutes || 30)} min cooldown · ${episodePolicy}${branches.length ? " · IF / ELSE" : ""}`;

    const actionEntity = text(automation.action_entity, "");
    const actionService = text(automation.action_service, "");
    const actions = Array.isArray(automation.actions) ? automation.actions.filter(item => item && typeof item === "object") : [];
    const actionLabel = item => item.kind === "delay" ? item.delay_seconds ? `Delay ${item.delay_seconds}s` : "Delay ?s" : item.kind === "wait_state" ? `Wait for ${item.entity_id ? entityName(item.entity_id) : "an entity"}` : text(item.service, "Configure service action");
    const actionTitle = actions.length > 1 ? `${actions.length} ordered actions` : actions.length === 1 ? actionLabel(actions[0]) : actionEntity ? entityName(actionEntity) : "Suggestion only";
    const actionDetail = actions.length > 1 ? actions.map(actionLabel).slice(0, 2).join(" → ") : actions.length === 1 ? actionLabel(actions[0]) : actionEntity && actionService ? actionService : "No Home Assistant service call";

    const nodes = [
      node("trigger", "WHEN", entityName(triggerEntity), triggerDetail),
      node("context", "IF", conditionDetail || contextTitle, conditionDetail ? `${contextDetail} · ${conditionDetail}` : contextDetail),
      node("decision", "DECIDE", decisionTitle, decisionDetail),
      node("action", "THEN", actionTitle, actionDetail),
    ];
    appendSubsteps(nodes[0], triggers.slice(1).map((item, index) => `OR ${index + 2} · ${item.kind && item.kind !== "entity" ? item.kind.replaceAll("_", " ") : text(item.entity_id, "Choose a trigger entity")}`));
    appendSubsteps(nodes[1], conditions.map((item, index) => `${String(automation.condition_mode || "all").toUpperCase()} ${index + 1} · ${item.kind && item.kind !== "entity" ? item.kind.replaceAll("_", " ") : text(item.entity_id, "Choose a condition entity")}`));
    appendSubsteps(nodes[2], branches.map((item, index) => `${text(item.name, `Branch ${index + 1}`)} · ${(item.conditions || []).length} condition${(item.conditions || []).length === 1 ? "" : "s"}`));
    appendSubsteps(nodes[3], automation.studio_visual_draft || actions.length > 1 ? actions.map((item, index) => `${index + 1} · ${actionLabel(item)}`) : []);
    nodes.forEach((item, index) => {
      if (index) flow.append(connector());
      flow.append(item);
    });
    return flow;
  }

  function render(root, automation, entityName) {
    if (!root) return;
    root.replaceChildren(create(automation, entityName));
  }

  window.zbranoAutomationFlow = {create, render};
})();
