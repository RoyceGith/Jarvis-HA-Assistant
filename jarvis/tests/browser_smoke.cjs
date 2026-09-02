"use strict";

const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

function loadPlaywright() {
  const npmRoot = process.platform === "win32"
    ? childProcess.execFileSync("cmd.exe", ["/d", "/s", "/c", "npm root -g"], {encoding: "utf8"}).trim()
    : childProcess.execFileSync("npm", ["root", "-g"], {encoding: "utf8"}).trim();
  const candidates = [
    path.join(npmRoot, "playwright"),
    path.join(npmRoot, "playwright-core"),
    path.join(npmRoot, "@playwright", "mcp", "node_modules", "playwright"),
    path.join(npmRoot, "@playwright", "mcp", "node_modules", "playwright-core"),
  ];
  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch (error) {
      if (error && error.code !== "MODULE_NOT_FOUND") throw error;
    }
  }
  throw new Error("Playwright library was not found beside the pinned @playwright/mcp package");
}

function entityFixture(index) {
  return {
    entity_id: `sensor.browser_fixture_${index}`,
    friendly_name: `Browser Fixture ${index}`,
    domain: "sensor",
    state: String(20 + index / 10),
    available: true,
    risk: "read_only",
    auto_approved: false,
    area_name: index % 2 ? "Workshop" : "Office",
    area_source: "device",
    site_name: "Factory workshop",
    site_label: "site-factory-workshop",
    zone_entity_id: "zone.factory_workshop",
    labels: ["browser-test"],
    device_class: "temperature",
    unit: "°C",
  };
}

const entities = [
  ...Array.from({length: 48}, (_, index) => entityFixture(index + 1)),
  {entity_id:"climate.browser_thermostat",friendly_name:"Browser Thermostat",domain:"climate",state:"cool",target_temperature:25,current_temperature:26.2,temperature_unit:"°C",hvac_action:"cooling",available:true,risk:"low_risk_control_proposed",auto_approved:true},
  {entity_id:"light.browser_light",friendly_name:"Browser Light",domain:"light",state:"off",available:true,risk:"low_risk_control_proposed",auto_approved:true},
];
const automationFixture = {
  settings: {
    operating_mode: "suggest_only",
    presence_entity: "",
    require_presence: false,
    respect_quiet_hours: true,
    minimum_confidence: 0.75,
    default_cooldown_minutes: 30,
    autonomous_risk_ceiling: "low",
    notify_after_autonomous_action: true,
    passive_learning_enabled: true,
  },
  automations: [{
    id: "browser-flow",
    name: "Browser flow",
    objective: "Verify graphical automation rendering",
    trigger_entity: "sensor.browser_fixture_1",
    trigger_operator: "above",
    trigger_value: "26",
    trigger_for_seconds: 60,
    presence_entity: "",
    signal_entities: ["sensor.browser_fixture_2"],
    proposal_template: "Suggest cooling",
    action_entity: "",
    action_service: "",
    cooldown_minutes: 30,
    confidence_threshold: 0.8,
    execution_policy: "suggest",
    risk_level: "controlled",
    enabled: false,
    review_required: false,
    updated_at: 100,
  }, {
    id: "active-flow",
    name: "Active lighting",
    objective: "Verify active library ordering",
    trigger_entity: "sensor.browser_fixture_3",
    trigger_operator: "above",
    trigger_value: "20",
    trigger_for_seconds: 0,
    presence_entity: "",
    signal_entities: [],
    proposal_template: "Suggest lighting",
    action_entity: "light.browser_fixture",
    action_service: "light.turn_on",
    cooldown_minutes: 10,
    confidence_threshold: 0.9,
    execution_policy: "autonomous",
    risk_level: "low",
    enabled: true,
    review_required: false,
    updated_at: 200,
  }],
  suggestions: [],
  timeline: [],
  entity_memory: [],
  area_context: {areas: [], entities: [], labels: [], zones: []},
  patterns: [],
  discoveries: [],
  engine: {status: "active"},
};

const notificationInboxFixture = {
  notifications: [{
    id: "notice-browser-1", title: "Workshop temperature", message: "The office is above 26°C.",
    target: "notify.browser_phone", severity: "suggestion", status: "delivered", created_at: 1788300000, read_at: 0,
    suggestion_id: "1234567890abcdef1234",
    automation_suggestion: {id:"1234567890abcdef1234", status:"approval_required", source:"automation", action_entity:"climate.browser_thermostat", action_service:"climate.turn_on", discovery_id:""},
  }],
  unread_count: 1,
  total: 1,
};

function apiFixture(url, method = "GET") {
  const pathname = new URL(url).pathname;
  if (pathname === "/api/health") {
    return {
      status: "ok",
      version: "0.13.121",
      speech_provider: "openai",
      speech_providers: {openai: {configured: true}, elevenlabs: {configured: false}},
    };
  }
  if (pathname === "/api/models") return {models: ["gpt-5-mini"]};
  if (pathname === "/api/chats") return {chats: []};
  if (pathname === "/api/settings") {
    return {
      preferences: {theme: "dark", model: "gpt-5-mini", reasoning_effort: "medium"},
      voice: {},
      speech_provider: "openai",
      auto_sync_releases_to_workshop_memory: false,
    };
  }
  if (pathname === "/api/ha/entities") {
    return {entities, count: entities.length, domains: ["sensor", "climate", "light"], source: "browser fixture"};
  }
  if (pathname === "/api/ha/approved") {
    return {policy: {}, read_entities: [], control_entities: []};
  }
  if (pathname === "/api/automations") return automationFixture;
  if (method === "POST" && pathname === "/api/automations/active-flow/pause") {
    Object.assign(automationFixture.automations.find(item => item.id === "active-flow"), {enabled: false, status: "paused", updated_at: 300});
    return {paused: true};
  }
  if (method === "POST" && pathname === "/api/automations/active-flow/activate") {
    Object.assign(automationFixture.automations.find(item => item.id === "active-flow"), {enabled: true, status: "armed", updated_at: 400});
    return {activated: true};
  }
  if (pathname === "/api/automations/test-flow") return {
    safe_dry_run: true,
    actions_executed: 0,
    status: "waiting_for_event",
    trace: [
      {kind: "trigger", status: "waiting", title: "Trigger", detail: "Waiting for the next matching state change"},
      {kind: "context", status: "pass", title: "Context", detail: "Current context passes"},
      {kind: "decision", status: "pass", title: "Decision", detail: "Linear path; suggest only"},
      {kind: "action", status: "info", title: "Planned actions", detail: "No action executed"},
    ],
  };
  if (pathname === "/api/notifications") {
    return {settings: {}, channels: [{entity_id: "notify.browser_phone", friendly_name: "Browser Phone", platform: "home_assistant", available: true}], watches: [], deliveries: [], telegram_channels: 0};
  }
  if (pathname === "/api/notifications/inbox") {
    if (method === "PUT") {
      notificationInboxFixture.unread_count = 0;
      notificationInboxFixture.notifications[0].read_at = 1788300001;
      return {marked_read: 1, unread_count: 0};
    }
    return notificationInboxFixture;
  }
  if (method === "DELETE" && pathname === "/api/notifications/deliveries") {
    notificationInboxFixture.notifications = [];
    notificationInboxFixture.unread_count = 0;
    notificationInboxFixture.total = 0;
    return {deleted: 1, remaining: 0};
  }
  if (method === "POST" && pathname === "/api/automations/suggestions/1234567890abcdef1234/dismiss") {
    notificationInboxFixture.notifications[0].automation_suggestion.status = "dismissed";
    return {dismissed: true};
  }
  if (pathname === "/api/calendar") return {appointments: [], default_destination: "notify.browser_phone"};
  if (pathname === "/api/birthdays") return {birthdays: [{
    id: "birthday-fixture", name: "Alex", birthday: "09-12", birth_year: 1990,
    relationship: "Friend", reminder_days_before: [7, 1, 0], destination: "notify.browser_phone",
    notes: "Likes books", gift_ideas: "A new novel", next_occurrence: "2026-09-12", days_until: 11, turning_age: 36,
  }]};
  if (pathname === "/api/contacts") return {contacts: [{
    id:"contact-fixture",kind:"person",display_name:"Alex Morgan",given_name:"Alex",family_name:"Morgan",
    company_name:"Example Works",job_title:"Designer",phone_numbers:["+357 99123456"],emails:["alex@example.com"],
    birthday:"09-12",birth_year:1990,relationship:"Friend",address:"Nicosia",website:"https://example.com",
    notes:"Likes books",has_bank_details:false,
  }],count:1};
  if (pathname === "/api/contacts/google/status") return {connected:false,account:""};
  if (pathname === "/api/calendar/google/status") return {connected: false, enabled: false, pending_local_changes: 0};
  if (pathname === "/api/plugins") return {plugins: []};
  if (pathname === "/api/files/shared") return {files: [], count: 0};
  if (pathname === "/api/release-memory-sync") {
    return {enabled: false, state: "disabled", version: "0.13.121", task_active: false};
  }
  if (pathname === "/api/tab-activity") return {revisions: {}};
  if (pathname === "/api/grinder-monitor/status") return {enabled: false, connected: false};
  if (pathname === "/api/voice/wake-calibration") {
    return {enabled: false, samples: [], verifier: {enabled: false}};
  }
  if (pathname === "/api/developer/features") return {features: []};
  if (pathname === "/api/developer/status") return {enabled: false};
  return {};
}

function contentType(filePath) {
  return ({
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
  })[path.extname(filePath)] || "application/octet-stream";
}

async function startStaticServer(staticRoot) {
  const server = http.createServer((request, response) => {
    const requestPath = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
    const relative = requestPath === "/" ? "index.html" : requestPath.replace(/^\/+/, "");
    const resolved = path.resolve(staticRoot, relative);
    if (!resolved.startsWith(`${path.resolve(staticRoot)}${path.sep}`) || !fs.existsSync(resolved)) {
      response.writeHead(404).end("Not found");
      return;
    }
    response.writeHead(200, {"Content-Type": contentType(resolved), "Cache-Control": "no-store"});
    fs.createReadStream(resolved).pipe(response);
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return server;
}

async function main() {
  const staticRoot = path.resolve(__dirname, "..", "app", "static");
  const server = await startStaticServer(staticRoot);
  const address = server.address();
  const executablePath = [
    process.env.CHROMIUM_PATH,
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean).find(fs.existsSync);
  assert.ok(executablePath, "The image must provide Chromium for browser smoke tests");

  const {chromium} = loadPlaywright();
  const browser = await chromium.launch({
    executablePath,
    headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  try {
    const page = await browser.newPage({viewport: {width: 1100, height: 720}});
    await page.route("**/api/**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(apiFixture(route.request().url(), route.request().method())),
      });
    });
    await page.goto(`http://127.0.0.1:${address.port}/`, {waitUntil: "domcontentloaded"});
    await page.waitForFunction(() => typeof window.createNewChat === "function");
    await page.waitForFunction(() => !document.getElementById("chat-list")?.textContent.includes("Loading"));

    const composerStartHeight = await page.locator("#message").evaluate(element => element.getBoundingClientRect().height);
    assert.equal(await page.locator("#message").evaluate(element => getComputedStyle(element).fieldSizing), "content");
    await page.locator("#message").fill("discard this draft\nwith a second visual line");
    assert.ok(await page.locator("#message").evaluate(element => element.getBoundingClientRect().height) > composerStartHeight);
    await page.locator("#new-chat-button").click();
    assert.equal(await page.locator("#message").inputValue(), "");
    await page.locator('#chat-list .chat-list-item[data-draft="true"]').waitFor();
    assert.match(await page.locator("#messages").innerText(), /intelligence core online/i);

    await page.locator("#entities-tab").click();
    await page.locator("#entities-panel:not(.hidden)").waitFor();
    await page.locator("#entity-rows tr").nth(47).waitFor();
    const thermostatRow = page.locator("#entity-rows tr").filter({hasText:"Browser Thermostat"});
    assert.equal(await thermostatRow.locator("td").nth(7).innerText(), "cool · set to 25 °C");
    assert.match(await thermostatRow.locator("td").nth(7).getAttribute("title"), /Current 26.2 °C · Action cooling/);

    const scrollState = await page.locator("#entities-panel .table-wrap").evaluate(element => {
      element.scrollTop = element.scrollHeight;
      element.scrollLeft = element.scrollWidth;
      const style = getComputedStyle(element);
      return {
        overflowX: style.overflowX,
        overflowY: style.overflowY,
        horizontal: element.scrollLeft > 0,
        vertical: element.scrollTop > 0,
      };
    });
    assert.ok(["auto", "scroll"].includes(scrollState.overflowX));
    assert.ok(["auto", "scroll"].includes(scrollState.overflowY));
    assert.equal(scrollState.horizontal, true, "Entity Inventory must scroll horizontally");
    assert.equal(scrollState.vertical, true, "Entity Inventory must scroll vertically");

    await page.locator("#contacts-tab").click();
    await page.locator("#contacts-panel:not(.hidden)").waitFor();
    await page.getByText("Alex Morgan", {exact:true}).waitFor();
    assert.match(await page.locator("#contacts-list").innerText(), /Alex Morgan/);
    assert.match(await page.locator("#contacts-list").innerText(), /alex@example.com/);
    await page.locator('[data-contact-view="import"]').click();
    assert.equal(await page.locator("#contacts-import-upload").isVisible(), true);

    await page.locator("#automations-tab").click();
    await page.locator("#automations-panel:not(.hidden)").waitFor();
    assert.equal(await page.locator('[data-automation-overview-target="drafts"]').evaluate(element => getComputedStyle(element).cursor), "pointer");
    await page.locator('[data-automation-overview-target="drafts"][aria-label="View 1 automation draft"]').waitFor();
    assert.equal(await page.locator('[data-automation-overview-target="drafts"]').getAttribute("aria-label"), "View 1 automation draft");
    await page.locator('[data-automation-overview-target="drafts"]').click();
    await page.locator('[data-auto-panel="library"]:not(.hidden)').waitFor();
    assert.equal(await page.locator("#automation-library-filter").inputValue(), "disabled");
    assert.equal(await page.locator("#automation-library .autonomy-draft").count(), 1);
    await page.locator("#automation-library-filter").selectOption("all");
    await page.locator('[data-auto-view="overview"]').click();
    await page.locator('[data-automation-overview-target="suggestions"]').click();
    await page.waitForFunction(() => document.activeElement?.id === "autonomy-suggestion-inbox");
    assert.equal(await page.locator('[data-auto-panel="overview"]').evaluate(element => element.classList.contains("hidden")), false);
    await page.locator('[data-auto-view="studio"]').click();
    await page.locator('[data-auto-panel="studio"]:not(.hidden)').waitFor();
    assert.equal(await page.locator("#automations-panel").evaluate(element => element.classList.contains("studio-active")), true);
    const automationLayout = await page.locator("#automations-panel .autonomy-shell").evaluate(element => ({
      display: getComputedStyle(element).display,
      columns: getComputedStyle(element).gridTemplateColumns,
      navCursor: getComputedStyle(document.querySelector('[data-auto-view="studio"]')).cursor,
    }));
    assert.equal(automationLayout.display, "grid");
    assert.match(automationLayout.columns, /px .*px/);
    assert.equal(automationLayout.navCursor, "pointer");
    assert.equal(await page.locator("#studio-automation-trigger-entity").count(), 1);
    assert.equal(await page.locator("#studio-automation-trigger-sun-event").count(), 0);
    await page.locator("#studio-automation-trigger-kind").selectOption("sun");
    assert.equal(await page.locator("#studio-automation-trigger-sun-event").count(), 1);
    assert.equal(await page.locator("#studio-automation-trigger-entity").count(), 0);
    assert.equal(await page.locator("#studio-automation-trigger-at").count(), 0);
    await page.locator("#studio-automation-trigger-kind").selectOption("entity");
    await page.locator("#studio-automation-trigger-operator").selectOption("any_change");
    assert.equal(await page.locator("#studio-automation-trigger-value").count(), 0);
    await page.locator("#studio-automation-trigger-operator").selectOption("above");
    assert.equal(await page.locator("#studio-automation-trigger-value").count(), 1);
    await page.locator("#studio-automation-trigger-operator").selectOption("changes_to");
    assert.match(await page.locator('[data-auto-view="library"]').innerText(), /My Automations/);
    assert.match(await page.locator('[data-auto-view="memory"]').innerText(), /Automation Memory/);
    await page.locator('[data-auto-view="library"]').click();
    await page.locator('[data-auto-panel="library"]:not(.hidden)').waitFor();
    assert.equal((await page.locator("#automation-library-count").innerText()).toLowerCase(), "2 automations");
    assert.match(await page.locator("#automation-library .autonomy-draft").first().innerText(), /Active lighting/i);
    await page.locator("#automation-library-search").fill("browser flow");
    assert.equal(await page.locator("#automation-library .autonomy-draft").count(), 1);
    await page.locator("#automation-library-search").fill("missing automation");
    assert.equal(await page.locator("#automation-library .autonomy-draft").count(), 0);
    assert.match(await page.locator("#automation-library-count").innerText(), /0 of 2/i);
    await page.locator("#automation-library-search").fill("");
    assert.equal(await page.locator("#automation-library-all-count").innerText(), "2");
    assert.equal(await page.locator("#automation-library-active-count").innerText(), "1");
    assert.equal(await page.locator("#automation-library-attention-count").innerText(), "0");
    assert.equal(await page.locator("#automation-library-disabled-count").innerText(), "1");
    assert.equal(await page.locator("#automation-library-autonomous-count").innerText(), "1");
    await page.locator('[data-library-quick-filter="disabled"]').click();
    assert.equal(await page.locator("#automation-library-filter").inputValue(), "disabled");
    assert.equal(await page.locator('[data-library-quick-filter="disabled"]').getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator("#automation-library .autonomy-draft").count(), 1);
    await page.locator("#automation-library-filter").selectOption("active");
    assert.equal(await page.locator("#automation-library .autonomy-draft").count(), 1);
    await page.locator("#automation-library-filter").selectOption("disabled");
    assert.equal(await page.locator("#automation-library .autonomy-draft").count(), 1);
    await page.locator("#automation-library-filter").selectOption("all");
    await page.locator("#automation-library-sort").selectOption("name_desc");
    assert.match(await page.locator("#automation-library .autonomy-draft").first().innerText(), /Browser flow/i);
    await page.locator("#automation-library-sort").selectOption("active");
    assert.match(await page.locator("#automation-library .autonomy-draft").first().innerText(), /Active lighting/i);
    assert.equal(await page.locator("#automation-library .automation-flow-stage").count(), 8);
    assert.equal(await page.locator("#automation-library").evaluate(element => element.classList.contains("is-compact")), true);
    assert.equal(await page.locator("#automation-library .automation-library-flow").first().getAttribute("open"), null);
    await page.locator("#automation-library .automation-library-flow summary").first().click();
    assert.equal(await page.locator("#automation-library .automation-library-flow").first().getAttribute("open"), "");
    assert.equal(await page.locator("#automation-library .automation-flow").first().isVisible(), true);
    assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("zbrano.automation-studio.library.v1"))), {filter: "all", sort: "active"});
    await page.locator('[data-auto-view="memory"]').click();
    await page.locator('[data-auto-panel="memory"]:not(.hidden)').waitFor();
    assert.equal(await page.locator("#automation-memory-list").isVisible(), true);
    await page.locator('[data-auto-view="library"]').click();
    const pauseDialogPromise=page.waitForEvent("dialog"),pauseClick=page.locator('[data-auto-pause="active-flow"]').click();
    const pauseDialog=await pauseDialogPromise;assert.match(pauseDialog.message(),/Live evaluation and new actions will stop immediately/i);await pauseDialog.accept();await pauseClick;
    await page.locator('[data-auto-activate="active-flow"][data-auto-activation-label="Resume"]').waitFor();
    const resumeDialogPromise=page.waitForEvent("dialog"),resumeClick=page.locator('[data-auto-activate="active-flow"]').click();
    const resumeDialog=await resumeDialogPromise;assert.match(resumeDialog.message(),/^Resume Active lighting/i);await resumeDialog.accept();await resumeClick;
    await page.locator('[data-auto-pause="active-flow"]').waitFor();
    await page.locator('[data-auto-duplicate="active-flow"]').click();
    assert.equal(await page.locator("#automation-edit-id").inputValue(), "");
    assert.equal(await page.locator("#automation-name").inputValue(), "Active lighting copy");
    assert.equal(await page.locator("#automation-enabled").isChecked(), false);
    assert.equal(await page.locator("#automation-studio-dirty").isVisible(), true);
    assert.match(await page.locator("#automation-studio-state").innerText(), /Independent disabled copy ready/i);
    const duplicateDiscardDialog=page.waitForEvent("dialog"),duplicateDiscardClick=page.locator("#automation-studio-new").click();
    const duplicateDialog=await duplicateDiscardDialog;assert.match(duplicateDialog.message(),/Discard unsaved automation changes/i);await duplicateDialog.accept();await duplicateDiscardClick;
    await page.locator('[data-auto-view="studio"]').click();
    await page.locator('[data-auto-panel="studio"]:not(.hidden)').waitFor();
    const studioOrder = await page.evaluate(() => ({
      studio: document.querySelector(".automation-studio-preview").getBoundingClientRect().top,
      chat: document.querySelector(".automation-chat-builder").getBoundingClientRect().top,
    }));
    assert.ok(studioOrder.studio < studioOrder.chat, "Automation Studio must appear before Create with ZBRANO");
    const dropStudioBlock=kind=>page.evaluate(blockKind=>{const source=document.querySelector(`.automation-studio-toolbox [data-studio-node="${blockKind}"]`),canvas=document.querySelector("#automation-studio-canvas"),dataTransfer=new DataTransfer();source.dispatchEvent(new DragEvent("dragstart",{bubbles:true,dataTransfer}));canvas.dispatchEvent(new DragEvent("dragover",{bubbles:true,cancelable:true,dataTransfer}));canvas.dispatchEvent(new DragEvent("drop",{bubbles:true,cancelable:true,dataTransfer}));source.dispatchEvent(new DragEvent("dragend",{bubbles:true,dataTransfer}))},kind);
    await dropStudioBlock("trigger");
    assert.match(await page.locator("#automation-studio-state").innerText(), /Trigger block added/i);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 2);
    assert.equal(await page.locator('#automation-flow-preview [data-trigger-logic]').count(), 1);
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').last().innerText(), /Choose a trigger entity/i);
    await dropStudioBlock("trigger");
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 3);
    assert.equal(await page.locator('#automation-flow-preview .automation-flow-stage.is-trigger.is-dense').count(), 1);
    assert.deepEqual(await page.locator('#automation-flow-preview [data-trigger-logic]').first().locator("option").allTextContents(), ["OR", "AND"]);
    const lastTriggerCard=page.locator('#automation-flow-preview [data-flow-kind="trigger"]').last();await lastTriggerCard.hover();
    assert.equal(await lastTriggerCard.locator(".automation-flow-card-delete").isVisible(), true);
    await lastTriggerCard.locator(".automation-flow-card-delete").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 2);
    assert.match(await page.locator("#automation-studio-state").innerText(), /Use Undo to restore/i);
    await page.locator("#automation-studio-undo").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 3);
    const studioTriggerEntity = page.locator("#studio-automation-trigger-entity");
    await studioTriggerEntity.fill("Browser Fixture 1");
    const studioTriggerResult = page.locator("#automation-studio-inspector-fields .automation-entity-result").filter({hasText:"sensor.browser_fixture_1"}).first();
    await studioTriggerResult.waitFor();
    await studioTriggerResult.click();
    assert.equal(await page.locator("#automation-trigger-entity").inputValue(), "sensor.browser_fixture_1");
    await studioTriggerEntity.fill("sensor.primary_trigger");
    await studioTriggerEntity.press("Escape");
    await page.locator('[data-workflow-index="0"][data-trigger-field="entity_id"]').fill("sensor.middle_trigger");
    await page.locator('[data-workflow-index="1"][data-trigger-field="entity_id"]').fill("sensor.last_trigger");
    await page.waitForTimeout(260);
    const middleTriggerCard=page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(1);await middleTriggerCard.hover();
    assert.equal(await middleTriggerCard.locator(".automation-flow-card-duplicate").isVisible(), true);
    await middleTriggerCard.locator(".automation-flow-card-duplicate").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 4);
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(2).innerText(), /middle_trigger/i);
    assert.match(await page.locator("#automation-studio-state").innerText(), /Flow card duplicated/i);
    await page.locator("#automation-studio-undo").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 3);
    await page.evaluate(()=>{const cards=document.querySelectorAll('#automation-flow-preview [data-flow-kind="trigger"]'),source=cards[cards.length-1],target=cards[0],dataTransfer=new DataTransfer(),rect=target.getBoundingClientRect();source.dispatchEvent(new DragEvent("dragstart",{bubbles:true,dataTransfer}));target.dispatchEvent(new DragEvent("dragover",{bubbles:true,cancelable:true,dataTransfer,clientX:rect.left+1}));target.dispatchEvent(new DragEvent("drop",{bubbles:true,cancelable:true,dataTransfer,clientX:rect.left+1}))});
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').first().innerText(), /last_trigger/i);
    assert.match(await page.locator("#automation-studio-state").innerText(), /Flow card moved/i);
    await page.evaluate(()=>{const source=document.querySelector('.automation-studio-toolbox [data-studio-node="trigger"]'),target=document.querySelectorAll('#automation-flow-preview [data-flow-kind="trigger"]')[1],dataTransfer=new DataTransfer(),rect=target.getBoundingClientRect();source.dispatchEvent(new DragEvent("dragstart",{bubbles:true,dataTransfer}));target.dispatchEvent(new DragEvent("dragover",{bubbles:true,cancelable:true,dataTransfer,clientX:rect.left+1}));target.dispatchEvent(new DragEvent("drop",{bubbles:true,cancelable:true,dataTransfer,clientX:rect.left+1}));source.dispatchEvent(new DragEvent("dragend",{bubbles:true,dataTransfer}))});
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 4);
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(1).innerText(), /Choose a trigger entity/i);
    await dropStudioBlock("context");
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="context"]').count(), 1);
    await dropStudioBlock("decision");
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="decision"]').count(), 1);
    await dropStudioBlock("action");
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="action"]').innerText(), /Configure a service action/i);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="action"]').count(), 1);
    assert.match(await page.locator("#automation-studio-state").innerText(), /Action block added/i);
    assert.equal(await page.locator(".automation-task-palette [data-action-template]").count(), 9);
    assert.equal(await page.locator('[data-action-template="notification"]').isEnabled(), true);
    await page.locator('[data-action-template="turn_on"]').click();
    await page.locator('[data-workflow-index="1"][data-action-field="entity_id"]').fill("light.browser_fixture");
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="action"]').nth(1).innerText(), /Power on/i);
    await page.locator('[data-action-template="notification"]').click();
    assert.equal(await page.locator('[data-workflow-index="2"][data-action-field="entity_id"]').inputValue(), "notify.browser_phone");
    await page.locator('[data-workflow-index="2"][data-action-field="notification_message"]').fill("Automation finished");
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="action"]').nth(2).innerText(), /Automation finished/i);
    await page.locator('[data-workflow-remove="2"]').click();
    await page.locator('[data-workflow-remove="1"]').click();
    await page.locator('[data-action-template="set_temperature"]').click();
    await page.locator('[data-workflow-index="1"][data-action-field="entity_id"]').fill("climate.browser_thermostat");
    await page.locator('[data-workflow-index="1"][data-action-data-field="temperature"]').fill("23.5");
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="action"]').nth(1).innerText(), /Set to 23.5°/i);
    const temperatureCard=page.locator('#automation-flow-preview [data-flow-kind="action"]').nth(1);await temperatureCard.hover();await temperatureCard.locator(".automation-flow-card-delete").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="action"]').count(), 1);
    assert.equal(await page.locator(".automation-workflow-step").count(), 1);
    assert.equal(await page.locator("#automation-studio-dirty").isVisible(), true);
    const droppedBlocksReset=page.waitForEvent("dialog"),droppedBlocksNewFlow=page.locator("#automation-studio-new").click();
    const droppedBlocksDialog=await droppedBlocksReset;assert.match(droppedBlocksDialog.message(),/Discard unsaved automation changes/i);await droppedBlocksDialog.accept();await droppedBlocksNewFlow;
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 1);
    await page.locator(".automation-advanced summary").click();
    await page.locator("#automation-entity-options option").nth(47).waitFor({state: "attached"});
    await page.locator('[data-auto-template="comfort"]').click();
    assert.equal(await page.locator("#automation-name").inputValue(), "Comfort advisor");
    assert.equal(await page.locator("#automation-studio-dirty").isVisible(), true);
    const templateSignals = await page.locator("#automation-signals").inputValue();
    assert.match(templateSignals, /sensor\.browser_fixture_/);
    assert.doesNotMatch(templateSignals, /workshop_/);
    assert.equal(await page.locator("#automation-presence").inputValue(), "");
    assert.equal(await page.locator("#automation-action-entity").inputValue(), "");
    assert.equal(await page.locator("#automation-flow-preview .automation-flow-stage").count(), 4);
    assert.match(await page.locator("#automation-flow-preview").innerText(), /Comfort advisor|Record the match|room is becoming uncomfortable/i);
    await page.locator("#automation-studio-validation:not([hidden])").waitFor();
    assert.match(await page.locator("#automation-studio-validation").innerText(), /trigger: choose an entity/i);
    await page.locator("#automation-studio-test").click();
    assert.match(await page.locator("#automation-studio-state").innerText(), /before testing/i);
    await page.locator("#automation-studio-save").click();
    assert.match(await page.locator("#automation-studio-state").innerText(), /before saving/i);
    await page.locator('[data-validation-kind="trigger"]').first().click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "Trigger");
    await page.locator("#studio-automation-trigger-entity").fill("sensor.browser_fixture_1");
    await page.locator("#studio-automation-trigger-value").fill("27");
    assert.equal(await page.locator("#automation-trigger-value").inputValue(), "27");
    assert.equal(await page.locator("#automation-studio-validation").isHidden(), true);
    await page.waitForTimeout(260);
    assert.equal(await page.locator("#automation-studio-undo").isEnabled(), true);
    await page.locator("#automation-studio-undo").click();
    assert.equal(await page.locator("#automation-trigger-value").inputValue(), "");
    assert.equal(await page.locator("#automation-studio-redo").isEnabled(), true);
    await page.locator("#automation-studio-redo").click();
    assert.equal(await page.locator("#automation-trigger-value").inputValue(), "27");
    await page.waitForTimeout(260);
    await page.reload({waitUntil: "domcontentloaded"});
    await page.waitForFunction(() => window.zbranoAutomationWorkspace?.ready === true);
    await page.locator("#automations-tab").click();
    await page.locator('[data-auto-view="studio"]').click();
    assert.equal(await page.locator("#automation-trigger-value").inputValue(), "27");
    assert.match(await page.locator("#automation-studio-state").innerText(), /Recovered unsaved flow/i);
    assert.equal(await page.locator("#automation-studio-dirty").isVisible(), true);
    const replacementDialog=page.waitForEvent("dialog"),newFlowClick=page.locator("#automation-studio-new").click();
    const dialog=await replacementDialog;assert.match(dialog.message(),/Discard unsaved automation changes/i);await dialog.dismiss();await newFlowClick;
    assert.equal(await page.locator("#automation-trigger-value").inputValue(), "27");
    await page.locator('[data-studio-node="trigger"]').click();
    await page.locator('[data-workflow-add="triggers"]').click();
    await page.locator('[data-workflow-index="0"][data-trigger-field="kind"]').selectOption("time");
    await page.locator('[data-workflow-index="0"][data-trigger-field="at"]').fill("18:30");
    await page.locator('[data-workflow-index="0"][data-trigger-field="weekdays"]').fill("Mon, Wed, Fri");
    assert.equal(await page.locator('[data-workflow-index="0"][data-trigger-field="at"]').inputValue(), "18:30");
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 2);
    assert.equal(await page.locator("#automation-flow-preview [data-trigger-logic]").inputValue(), "any");
    await page.locator("#automation-flow-preview [data-trigger-logic]").selectOption("all");
    assert.equal(await page.locator("[data-trigger-mode]").inputValue(), "all");
    await page.locator("#automation-flow-preview [data-trigger-logic]").selectOption("any");
    await page.locator('#automation-flow-preview [data-flow-kind="context"]').first().click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "Context");
    await page.locator('[data-workflow-add="conditions"]').click();
    await page.locator('[data-workflow-index="0"][data-condition-field="entity_id"]').fill("sensor.browser_fixture_3");
    await page.locator("[data-workflow-mode]").selectOption("any");
    assert.match(await page.locator("#automation-flow-preview").innerText(), /Browser Fixture 3/i);
    await page.locator('#automation-flow-preview [data-flow-kind="action"]').click();
    await page.locator('[data-workflow-add="actions"]').click();
    assert.equal(await page.locator(".automation-workflow-step").count(), 1);
    await page.locator('[data-workflow-index="0"][data-action-field="kind"]').selectOption("delay");
    await page.locator('[data-workflow-index="0"][data-action-field="delay_seconds"]').fill("2");
    assert.match(await page.locator("#automation-flow-preview").innerText(), /Delay 2s/i);
    await page.locator('#automation-flow-preview [data-flow-kind="decision"]').click();
    await page.locator("#studio-automation-execution-policy").selectOption("inherit");
    assert.equal(await page.locator("#automation-execution-policy").inputValue(), "inherit");
    await page.locator("#studio-automation-delivery-voice").uncheck();
    assert.equal(await page.locator("#automation-delivery-voice").isChecked(), false);
    await page.locator("#automation-studio-test").click();
    await page.locator("#automation-studio-test-results:not([hidden])").waitFor();
    assert.equal(await page.locator("#automation-studio-test-results .automation-studio-test-step").count(), 4);
    assert.match(await page.locator("#automation-studio-state").innerText(), /0 actions executed/i);
    await page.locator("[data-branch-add]").click();
    await page.locator('[data-branch-suggestion="0"]').fill("Check the cooling conditions for this path.");
    assert.match(await page.locator('#automation-flow-preview .automation-flow-branch-suggestion').first().innerText(), /Check the cooling conditions/i);
    await page.locator('[data-branch-add-item="conditions"]').click();
    await page.locator('[data-branch-collection="conditions"][data-condition-field="entity_id"]').fill("sensor.browser_fixture_4");
    await page.locator('[data-branch-add-item="actions"]').click();
    await page.locator('[data-branch-collection="actions"][data-action-field="entity_id"]').fill("light.browser_fixture");
    await page.locator('[data-branch-collection="actions"][data-action-field="service"]').fill("light.turn_on");
    await page.locator('[data-branch-add-item="actions"]').click();
    await page.locator('[data-branch-collection="actions"][data-item-index="1"][data-action-field="kind"]').selectOption("wait_state");
    await page.locator('[data-branch-collection="actions"][data-item-index="1"][data-action-field="entity_id"]').fill("sensor.browser_fixture_5");
    await page.locator('[data-branch-collection="actions"][data-item-index="1"][data-action-field="wait_value"]').fill("25");
    assert.match(await page.locator("#automation-flow-preview").innerText(), /PATH 1|Branch 1/i);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-branch-drop="0"]').count(), 1);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"]').count(), 1);
    await page.locator('[data-flow-branch-drop="0"] .automation-flow-branch-condition-menu > summary').click();
    await page.locator('[data-flow-branch-condition-template="entity_compare"][data-flow-branch-index="0"]').click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"]').count(), 2);
    await page.locator('[data-branch-collection="conditions"][data-item-index="1"][data-condition-field="entity_id"]').fill("sensor.browser_fixture_5");
    await page.locator('[data-branch-collection="conditions"][data-item-index="1"][data-condition-field="compare_entity_id"]').fill("climate.browser_thermostat");
    await page.locator('[data-branch-collection="conditions"][data-item-index="1"][data-condition-field="compare_attribute"]').fill("temperature");
    await page.locator('#automation-flow-preview [data-branch-condition-logic]').selectOption("any");
    assert.equal(await page.locator('[data-branch-mode="0"]').inputValue(), "any");
    await page.evaluate(()=>{const cards=document.querySelectorAll('#automation-flow-preview [data-flow-kind="branch-condition"]'),source=cards[1],target=cards[0],dataTransfer=new DataTransfer(),rect=target.getBoundingClientRect();source.dispatchEvent(new DragEvent("dragstart",{bubbles:true,dataTransfer}));target.dispatchEvent(new DragEvent("dragover",{bubbles:true,cancelable:true,dataTransfer,clientY:rect.top+1}));target.dispatchEvent(new DragEvent("drop",{bubbles:true,cancelable:true,dataTransfer,clientY:rect.top+1}))});
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"]').first().innerText(), /Browser Fixture 5/i);
    const firstBranchCondition=page.locator('#automation-flow-preview [data-flow-kind="branch-condition"]').first();await firstBranchCondition.hover();await firstBranchCondition.locator(".automation-flow-card-duplicate").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"]').count(), 3);
    await page.locator("#automation-studio-undo").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"]').count(), 2);
    await page.locator("[data-flow-add-branch]").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-branch-drop="1"]').count(), 1);
    assert.equal(await page.locator("#automation-flow-preview .automation-flow-branch-toolbar").count(), 2);
    await page.locator('[data-flow-branch-action="duplicate"][data-flow-branch-index="0"]').click();
    assert.equal(await page.locator("#automation-flow-preview .automation-flow-branch-lane").count(), 3);
    await page.locator('[data-flow-branch-action="delete"][data-flow-branch-index="1"]').click();
    assert.equal(await page.locator("#automation-flow-preview .automation-flow-branch-lane").count(), 2);
    await page.locator('[data-flow-branch-action="next"][data-flow-branch-index="0"]').click();
    await page.locator('[data-flow-branch-action="previous"][data-flow-branch-index="1"]').click();
    assert.match(await page.locator('[data-flow-branch-drop="0"] [data-flow-kind="decision"]').innerText(), /Branch 1/i);
    const starterPathCondition=page.locator('#automation-flow-preview [data-flow-kind="branch-condition"][data-flow-branch-index="1"]');await starterPathCondition.hover();await starterPathCondition.locator(".automation-flow-card-delete").click({force:true});
    await page.evaluate(()=>{const source=document.querySelector('#automation-flow-preview [data-flow-kind="branch-condition"]'),lane=document.querySelector('#automation-flow-preview [data-flow-branch-condition-drop="1"]'),dataTransfer=new DataTransfer();source.dispatchEvent(new DragEvent("dragstart",{bubbles:true,dataTransfer}));lane.dispatchEvent(new DragEvent("dragover",{bubbles:true,cancelable:true,dataTransfer}));lane.dispatchEvent(new DragEvent("drop",{bubbles:true,cancelable:true,dataTransfer}))});
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"][data-flow-branch-index="1"]').count(), 1);
    await page.evaluate(()=>{const source=document.querySelector('#automation-flow-preview [data-flow-kind="branch-condition"][data-flow-branch-index="1"]'),lane=document.querySelector('#automation-flow-preview [data-flow-branch-condition-drop="0"]'),dataTransfer=new DataTransfer();source.dispatchEvent(new DragEvent("dragstart",{bubbles:true,dataTransfer}));lane.dispatchEvent(new DragEvent("dragover",{bubbles:true,cancelable:true,dataTransfer}));lane.dispatchEvent(new DragEvent("drop",{bubbles:true,cancelable:true,dataTransfer}))});
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"][data-flow-branch-index="0"]').count(), 2);
    const removableBranchCondition=page.locator('#automation-flow-preview [data-flow-kind="branch-condition"]').last();await removableBranchCondition.hover();await removableBranchCondition.locator(".automation-flow-card-delete").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"]').count(), 1);
    await page.locator("#automation-studio-undo").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"]').count(), 2);
    await page.locator('[data-flow-branch-drop="0"] .automation-flow-branch-task-menu > summary').click();
    await page.locator('[data-flow-branch-task-template="delay"][data-flow-branch-index="0"]').click();
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').last().innerText(), /Delay 5s/i);
    await page.waitForTimeout(260);
    const quickBranchTask=page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').last();await quickBranchTask.hover();await quickBranchTask.locator(".automation-flow-card-delete").click({force:true});
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').count(), 2);
    assert.match(await page.locator('#automation-flow-preview .automation-flow-stage.is-action').innerText(), /UNASSIGNED TASKS|Delay 2s/i);
    await page.evaluate(()=>{const source=document.querySelector('#automation-flow-preview [data-flow-kind="action"]'),cards=document.querySelectorAll('#automation-flow-preview [data-flow-kind="branch-action"]'),target=cards[cards.length-1],dataTransfer=new DataTransfer(),rect=target.getBoundingClientRect();source.dispatchEvent(new DragEvent("dragstart",{bubbles:true,dataTransfer}));target.dispatchEvent(new DragEvent("dragover",{bubbles:true,cancelable:true,dataTransfer,clientY:rect.bottom-1}));target.dispatchEvent(new DragEvent("drop",{bubbles:true,cancelable:true,dataTransfer,clientY:rect.bottom-1}))});
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="action"]').count(), 0);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').count(), 3);
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').last().innerText(), /Delay 2s/i);
    assert.match(await page.locator("#automation-studio-state").innerText(), /moved into the selected branch/i);
    await page.evaluate(()=>{const cards=document.querySelectorAll('#automation-flow-preview [data-flow-kind="branch-action"]'),source=cards[cards.length-1],target=cards[0],dataTransfer=new DataTransfer(),rect=target.getBoundingClientRect();source.dispatchEvent(new DragEvent("dragstart",{bubbles:true,dataTransfer}));target.dispatchEvent(new DragEvent("dragover",{bubbles:true,cancelable:true,dataTransfer,clientY:rect.top+1}));target.dispatchEvent(new DragEvent("drop",{bubbles:true,cancelable:true,dataTransfer,clientY:rect.top+1}))});
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').first().innerText(), /Delay 2s/i);
    await page.evaluate(()=>{const source=document.querySelector('.automation-studio-toolbox [data-studio-node="action"]'),lane=document.querySelector('#automation-flow-preview [data-flow-branch-drop="0"]'),dataTransfer=new DataTransfer();source.dispatchEvent(new DragEvent("dragstart",{bubbles:true,dataTransfer}));lane.dispatchEvent(new DragEvent("dragover",{bubbles:true,cancelable:true,dataTransfer}));lane.dispatchEvent(new DragEvent("drop",{bubbles:true,cancelable:true,dataTransfer}));source.dispatchEvent(new DragEvent("dragend",{bubbles:true,dataTransfer}))});
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').count(), 4);
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').last().innerText(), /Configure a service action/i);
    const newBranchTask=page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').last();await newBranchTask.hover();await newBranchTask.locator(".automation-flow-card-delete").click({force:true});
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').count(), 3);
    const firstBranchTask=page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').first();await firstBranchTask.hover();await firstBranchTask.locator(".automation-flow-card-duplicate").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').count(), 4);
    await page.locator("#automation-studio-undo").click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"]').count(), 3);

    await page.locator("#notification-inbox-count:not([hidden])").waitFor();
    assert.equal(await page.locator("#notification-inbox-count").innerText(), "1");
    await page.locator("#notification-inbox-toggle").click();
    await page.locator("#notification-inbox-popover:not([hidden])").waitFor();
    assert.match(await page.locator("#notification-inbox-list").innerText(), /Workshop temperature/);
    assert.match(await page.locator("#notification-inbox-list").innerText(), /above 26°C/);
    assert.equal(await page.getByRole("button", {name:"Approve action"}).count(), 1);
    await page.getByRole("button", {name:"Not now"}).click();
    await page.getByRole("button", {name:"Not now"}).waitFor({state:"detached"});
    assert.equal(await page.locator("#notification-inbox-popover").isVisible(), true);
    const markAllNotifications = page.locator("#notification-inbox-mark-all");
    if (await markAllNotifications.isEnabled()) await markAllNotifications.click();
    await page.locator("#notification-inbox-count").waitFor({state:"hidden", timeout:3000});
    const notificationRow = page.locator(".notification-inbox-item");
    await notificationRow.hover();
    await notificationRow.locator(".notification-inbox-delete").click();
    await page.locator("#notification-inbox-list .notification-inbox-empty").waitFor();
    assert.match(await page.locator("#notification-inbox-list").innerText(), /No notifications yet/i);
    assert.equal(await page.locator("#notification-inbox-popover").isVisible(), true);
    await page.locator("#notification-inbox-open-center").click();
    await page.locator('[data-auto-panel="notifications"]:not(.hidden)').waitFor();

    await page.locator("#calendar-tab").click();
    await page.locator("#calendar-panel:not(.hidden)").waitFor();
    await page.locator('[data-calendar-view="birthdays"]').click();
    assert.match(await page.locator("#birthday-upcoming-list").innerText(), /Alex/);
    assert.match(await page.locator("#birthday-upcoming-list").innerText(), /in 11 days/i);
    await page.locator('[data-birthday-view="people"]').click();
    assert.match(await page.locator("#birthday-people-list").innerText(), /A new novel/);
    await page.locator('#birthday-people-list [data-birthday-edit="birthday-fixture"]').click({force:true});
    assert.equal(await page.locator("#birthday-name").inputValue(), "Alex");
    assert.equal(await page.locator("#birthday-year").inputValue(), "1990");

    await page.locator("#settings-tab").click();
    await page.locator("#settings-panel:not(.hidden)").waitFor();
    const settingsLayout = await page.locator("#settings-panel .settings-stack").evaluate(element => ({
      display: getComputedStyle(element).display,
      columns: getComputedStyle(element).gridTemplateColumns,
      cursor: getComputedStyle(document.querySelector("#settings-tab")).cursor,
    }));
    assert.equal(settingsLayout.display, "grid");
    assert.match(settingsLayout.columns, /px .*px/);
    assert.equal(settingsLayout.cursor, "pointer");
    await page.locator('[data-settings-target="voice"]').click();
    await page.locator('[data-settings-category="voice"]:visible').waitFor();
    assert.equal(await page.locator('[data-settings-target="voice"]').evaluate(element => element.closest("details").open), true);
    const voiceScroll = await page.locator("#settings-panel").evaluate(element => {
      element.scrollTop = element.scrollHeight;
      return {overflowY: getComputedStyle(element).overflowY, scrollable: element.scrollHeight > element.clientHeight, moved: element.scrollTop > 0};
    });
    assert.ok(["auto", "scroll"].includes(voiceScroll.overflowY));
    assert.equal(voiceScroll.scrollable, true, "Voice settings must exceed and scroll within the panel at compact viewport heights");
    assert.equal(voiceScroll.moved, true, "Voice settings panel must accept vertical scrolling");

    console.log("Browser smoke passed: New Chat, navigation, Entity scrolling, notification inbox, Calendar birthdays, modern Settings, Automation Library filtering, Studio safety, validation, recovery, and branching workflows");
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
