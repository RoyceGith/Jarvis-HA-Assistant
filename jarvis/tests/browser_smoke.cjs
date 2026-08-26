"use strict";

const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

function loadPlaywright() {
  const npmRoot = childProcess.execFileSync("npm", ["root", "-g"], {encoding: "utf8"}).trim();
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
  automations: [],
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
      version: "0.13.50",
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
    return {enabled: false, state: "disabled", version: "0.13.50", task_active: false};
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
  const executablePath = ["/usr/bin/chromium-browser", "/usr/bin/chromium"].find(fs.existsSync);
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
    await page.locator('[data-automation-library-view="create"]').click();
    await page.locator('[data-automation-library-panel="create"]:not(.hidden)').waitFor();
    await page.locator('[data-auto-template="comfort"]').click();
    assert.equal(await page.locator("#automation-name").inputValue(), "Comfort advisor");
    const templateSignals = await page.locator("#automation-signals").inputValue();
    assert.match(templateSignals, /sensor\.browser_fixture_/);
    assert.doesNotMatch(templateSignals, /workshop_/);
    assert.equal(await page.locator("#automation-presence").inputValue(), "");
    assert.equal(await page.locator("#automation-action-entity").inputValue(), "");

    console.log("Browser smoke passed: New Chat, navigation, Entity scrolling, Automation Library tabs, and installation-derived templates");
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
