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

const entities = Array.from({length: 48}, (_, index) => entityFixture(index + 1));
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
  }],
  suggestions: [],
  timeline: [],
  entity_memory: [],
  area_context: {areas: [], entities: [], labels: [], zones: []},
  patterns: [],
  discoveries: [],
  engine: {status: "active"},
};

function apiFixture(url) {
  const pathname = new URL(url).pathname;
  if (pathname === "/api/health") {
    return {
      status: "ok",
      version: "0.13.67",
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
    return {entities, count: entities.length, domains: ["sensor"], source: "browser fixture"};
  }
  if (pathname === "/api/ha/approved") {
    return {policy: {}, read_entities: [], control_entities: []};
  }
  if (pathname === "/api/automations") return automationFixture;
  if (pathname === "/api/notifications") {
    return {settings: {}, channels: [], watches: [], deliveries: [], telegram_channels: 0};
  }
  if (pathname === "/api/plugins") return {plugins: []};
  if (pathname === "/api/files/shared") return {files: [], count: 0};
  if (pathname === "/api/release-memory-sync") {
    return {enabled: false, state: "disabled", version: "0.13.67", task_active: false};
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
        body: JSON.stringify(apiFixture(route.request().url())),
      });
    });
    await page.goto(`http://127.0.0.1:${address.port}/`, {waitUntil: "domcontentloaded"});
    await page.waitForFunction(() => typeof window.createNewChat === "function");
    await page.waitForFunction(() => !document.getElementById("chat-list")?.textContent.includes("Loading"));

    await page.locator("#message").fill("discard this draft");
    await page.locator("#new-chat-button").click();
    assert.equal(await page.locator("#message").inputValue(), "");
    await page.locator('#chat-list .chat-list-item[data-draft="true"]').waitFor();
    assert.match(await page.locator("#messages").innerText(), /intelligence core online/i);

    await page.locator("#entities-tab").click();
    await page.locator("#entities-panel:not(.hidden)").waitFor();
    await page.locator("#entity-rows tr").nth(47).waitFor();
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

    await page.locator("#automations-tab").click();
    await page.locator("#automations-panel:not(.hidden)").waitFor();
    await page.locator('[data-auto-view="library"]').click();
    await page.locator('[data-auto-panel="library"]:not(.hidden)').waitFor();
    await page.locator('[data-automation-library-view="saved"]').click();
    await page.locator('[data-automation-library-panel="saved"]:not(.hidden)').waitFor();
    assert.equal(await page.locator("#automation-library .automation-flow-node").count(), 4);
    await page.locator('[data-automation-library-view="create"]').click();
    await page.locator('[data-automation-library-panel="create"]:not(.hidden)').waitFor();
    await page.locator(".automation-advanced summary").click();
    await page.locator("#automation-entity-options option").nth(47).waitFor({state: "attached"});
    await page.locator('[data-auto-template="comfort"]').click();
    assert.equal(await page.locator("#automation-name").inputValue(), "Comfort advisor");
    const templateSignals = await page.locator("#automation-signals").inputValue();
    assert.match(templateSignals, /sensor\.browser_fixture_/);
    assert.doesNotMatch(templateSignals, /workshop_/);
    assert.equal(await page.locator("#automation-presence").inputValue(), "");
    assert.equal(await page.locator("#automation-action-entity").inputValue(), "");
    assert.equal(await page.locator("#automation-flow-preview .automation-flow-node").count(), 4);
    assert.match(await page.locator("#automation-flow-preview").innerText(), /Comfort advisor|Record the match|room is becoming uncomfortable/i);
    await page.locator('[data-studio-node="trigger"]').click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "Trigger");
    await page.locator("#studio-automation-trigger-value").fill("27");
    assert.equal(await page.locator("#automation-trigger-value").inputValue(), "27");
    await page.locator('[data-workflow-add="triggers"]').click();
    await page.locator('[data-workflow-field="entity_id"]').fill("sensor.browser_fixture_2");
    assert.match(await page.locator("#automation-flow-preview").innerText(), /2 OR triggers/i);
    await page.locator('#automation-flow-preview [data-flow-kind="context"]').click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "Context");
    await page.locator('[data-workflow-add="conditions"]').click();
    await page.locator('[data-workflow-field="entity_id"]').fill("sensor.browser_fixture_3");
    await page.locator("[data-workflow-mode]").selectOption("any");
    assert.match(await page.locator("#automation-flow-preview").innerText(), /1 ANY condition/i);
    await page.locator('#automation-flow-preview [data-flow-kind="action"]').click();
    await page.locator('[data-workflow-add="actions"]').click();
    assert.equal(await page.locator(".automation-workflow-step").count(), 1);
    await page.locator('#automation-flow-preview [data-flow-kind="decision"]').click();
    await page.locator("[data-branch-add]").click();
    await page.locator('[data-branch-add-item="conditions"]').click();
    await page.locator('[data-branch-collection="conditions"][data-branch-field="entity_id"]').fill("sensor.browser_fixture_4");
    await page.locator('[data-branch-add-item="actions"]').click();
    await page.locator('[data-branch-collection="actions"][data-branch-field="entity_id"]').fill("light.browser_fixture");
    await page.locator('[data-branch-collection="actions"][data-branch-field="service"]').fill("light.turn_on");
    assert.match(await page.locator("#automation-flow-preview").innerText(), /1 first-match branch/i);

    console.log("Browser smoke passed: New Chat, navigation, Entity scrolling, branching Automation Studio workflows, and installation-derived templates");
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
