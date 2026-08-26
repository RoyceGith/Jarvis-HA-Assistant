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

  function node(kind, label, title, detail) {
    const element = document.createElement("section");
    element.className = `automation-flow-node is-${kind}`;
    const kicker = document.createElement("span");
    kicker.className = "automation-flow-kicker";
    kicker.textContent = label;
    const heading = document.createElement("strong");
    heading.textContent = title;
    const description = document.createElement("small");
    description.textContent = detail;
    element.append(kicker, heading, description);
    return element;
  }

  function connector() {
    const element = document.createElement("span");
    element.className = "automation-flow-connector";
    element.setAttribute("aria-hidden", "true");
    element.textContent = "→";
    return element;
  }

  function create(automation = {}, entityName = value => value) {
    const flow = document.createElement("div");
    flow.className = "automation-flow";
    flow.setAttribute("role", "group");
    flow.setAttribute("aria-label", `${text(automation.name, "Automation")} visual flow`);

    const triggerEntity = text(automation.trigger_entity, "Choose a trigger entity");
    const triggerValue = text(automation.trigger_value, "any value");
    const operator = operatorLabels[automation.trigger_operator] || text(automation.trigger_operator, "changes to");
    const duration = Number(automation.trigger_for_seconds || 0);
    const triggerDetail = `${operator} ${triggerValue}${duration > 0 ? ` for ${duration} seconds` : ""}`;

    const presence = text(automation.presence_entity, "");
    const signals = Array.isArray(automation.signal_entities) ? automation.signal_entities.filter(Boolean) : [];
    const contextTitle = presence ? entityName(presence) : signals.length ? `${signals.length} context signal${signals.length === 1 ? "" : "s"}` : "No presence requirement";
    const contextDetail = presence
      ? `Presence confirmed${signals.length ? ` · ${signals.length} supporting signal${signals.length === 1 ? "" : "s"}` : ""}`
      : signals.length ? signals.slice(0, 2).map(entityName).join(" · ") : "Evaluate from the trigger alone";

    const confidence = Math.round(Number(automation.confidence_threshold ?? 0.75) * 100);
    const authority = text(automation.execution_policy, "suggest").replaceAll("_", " ");
    const decisionTitle = text(automation.proposal_template, text(automation.objective, "Record the match"));
    const decisionDetail = `${confidence}% confidence · ${authority} · ${Number(automation.cooldown_minutes || 30)} min cooldown`;

    const actionEntity = text(automation.action_entity, "");
    const actionService = text(automation.action_service, "");
    const actionTitle = actionEntity ? entityName(actionEntity) : "Suggestion only";
    const actionDetail = actionEntity && actionService ? actionService : "No Home Assistant service call";

    const nodes = [
      node("trigger", "WHEN", entityName(triggerEntity), triggerDetail),
      node("context", "IF", contextTitle, contextDetail),
      node("decision", "DECIDE", decisionTitle, decisionDetail),
      node("action", "THEN", actionTitle, actionDetail),
    ];
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
