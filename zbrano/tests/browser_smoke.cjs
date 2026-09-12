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
    control_capable: false,
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
  ...Array.from({length: 78}, (_, index) => entityFixture(index + 1)),
  {entity_id:"climate.browser_thermostat",friendly_name:"Browser Thermostat",domain:"climate",state:"cool",target_temperature:25,current_temperature:26.2,temperature_unit:"°C",hvac_action:"cooling",available:true,risk:"low_risk_control_proposed",control_capable:true,auto_approved:false},
  {entity_id:"light.browser_light",friendly_name:"Browser Light",domain:"light",state:"off",available:true,risk:"low_risk_control_proposed",control_capable:true,auto_approved:false},
  {entity_id:"light.browser_fixture",friendly_name:"Browser Fixture Light",domain:"light",state:"off",available:true,risk:"low_risk_control_proposed",control_capable:true,auto_approved:false},
];
// Real registry identity joins one thermostat and its temperature entity.
for (const entity of [entities[0], entities.find(entity => entity.domain === "climate")]) {
  Object.assign(entity, {device_id:"fixture-ac", device_name:"Living Room AC", area_id:"living-room", area_name:"Living room", site_name:"Home"});
}
entities[1].device_name = "A very long device name for the upstairs bedroom temperature and comfort sensor";
const browserNow = Math.floor(Date.now() / 1000);
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
    readiness: {ready:true,summary:"All referenced entities have the required live access",issues:[],requirements:[
      {entity_id:"sensor.browser_fixture_1",permission:"read",access:"read_only",allowed:true,sources:["trigger_read"]},
      {entity_id:"sensor.browser_fixture_2",permission:"read",access:"read_only",allowed:true,sources:["signal_read"]},
    ]},
    evaluation: {state:"tune",headline:"Tune its suggestions",recommendation:"You choose Not now more often than accepting this automation. Narrow its When or IF checks, or increase its cooldown.",evidence_count:4,suggestions:4,answered:4,accepted:1,approvals:1,manual_resolutions:0,dismissals:3,expired:0,automatic_successes:0,action_failures:0,acceptance_rate:.25,response_rate:1,recent_matches:0,recent_completed_actions:0},
    updated_at: 100,
    decision_history: [{id:"decision-safe",outcome:"suppressed_presence",detail:"Royce is away",evidence:"person.royce = not_home",policy:"suggest",branch:"IF",created_at:browserNow-120}],
    last_decision: {id:"decision-safe",outcome:"suppressed_presence",detail:"Royce is away",evidence:"person.royce = not_home",policy:"suggest",branch:"IF",created_at:browserNow-120},
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
    readiness: {ready:true,summary:"All referenced entities have the required live access",issues:[],requirements:[
      {entity_id:"sensor.browser_fixture_3",permission:"read",access:"read_only",allowed:true,sources:["trigger_read"]},
      {entity_id:"light.browser_fixture",permission:"control",access:"low_risk_control_proposed",allowed:true,sources:["action_control"],safety_label_blocked:false},
    ]},
    recovery_state: {circuit_open:false,recent_failures:1,failure_limit:3,window_minutes:60,remaining_before_pause:2,last_failure_at:browserNow-600,retry_available_at:0,failure_acknowledged_at:0,recovery_resets:0,last_error:"Home Assistant service timed out"},
    evaluation: {state:"healthy",headline:"Healthy signals",recommendation:"Recent feedback does not show a repeated dismissal, delivery, permission, or action-failure problem.",evidence_count:5,suggestions:0,answered:0,accepted:0,approvals:0,manual_resolutions:0,dismissals:0,expired:0,automatic_successes:4,action_failures:1,acceptance_rate:null,response_rate:null,recent_matches:1,recent_completed_actions:1},
    updated_at: 200,
    decision_history: [{id:"decision-executed",outcome:"executed",detail:"Completed 1 action step",evidence:"sensor.browser_fixture_3 changed from 19 to 21",policy:"autonomous",branch:"IF",created_at:browserNow-60}],
    last_decision: {id:"decision-executed",outcome:"executed",detail:"Completed 1 action step",evidence:"sensor.browser_fixture_3 changed from 19 to 21",policy:"autonomous",branch:"IF",created_at:browserNow-60},
  }],
  suggestions: [],
  timeline: [{id:"activity-executed",type:"action",title:"Automation action sequence executed: Active lighting",detail:"steps=1; source=selective_autonomy",created_at:browserNow-60}],
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

const onboardingFixture = {
  completed: false,
  dismissed: true,
  legacy_installation: false,
  show_on_startup: false,
  current_step: "home_assistant",
  core_ready: false,
  required_verified: false,
  ready_count: 1,
  total_count: 7,
  steps: [
    {id:"home_assistant",title:"Home Assistant",description:"Waiting for the Home Assistant connection",ready:false,required:true,target:"home_assistant",last_check:null,skipped:false},
    {id:"model",title:"AI model",description:"gpt-5-mini is configured",ready:true,required:true,target:"model",last_check:{ready:true,detail:"Key accepted",checked_at:1788300000},skipped:false},
    {id:"entities",title:"Device access",description:"No devices selected. ZBRANO can chat, but cannot read sensors or control devices yet.",ready:false,required:false,target:"entities",last_check:null,skipped:false},
    {id:"voice",title:"Voice and wake word",description:"Configure speech if wanted",ready:false,required:false,target:"voice",last_check:null,skipped:false},
    {id:"memory",title:"Memory",description:"Fast Memory is optional",ready:false,required:false,target:"memory",last_check:null,skipped:false},
    {id:"plugins",title:"Plugins",description:"Plugins are optional",ready:false,required:false,target:"plugins",last_check:null,skipped:false},
    {id:"notifications",title:"Notifications and autonomy",description:"Choose notification delivery",ready:false,required:false,target:"notifications",last_check:null,skipped:false},
  ],
  installation_report: {
    generated_at: 1788300000, version: "0.13.240", ready: true, attention_count: 0, ready_count: 5,
    checks: [
      {id:"home_assistant",title:"Home Assistant",state:"ready",required:true,detail:"Connected to Home Assistant",target:"home_assistant"},
      {id:"model",title:"AI model",state:"ready",required:true,detail:"gpt-5-mini is configured",target:"model"},
      {id:"storage",title:"Persistent storage",state:"ready",required:true,detail:"ZBRANO can read and write its persistent data folder",target:"storage"},
      {id:"backup",title:"Backup and restore",state:"ready",required:false,detail:"A portable ZBRANO backup can be exported from Settings",target:"memory"},
      {id:"automation_health",title:"Automation safety",state:"ready",required:false,detail:"2 saved; 0 need permission; 0 paused after failures",target:"automations"},
    ],
    support_summary: "ZBRANO installation report · v0.13.240\nOverall: Ready\nHome Assistant: Connected\nAI model: Configured\nDevice access: 3 sensor devices / 1 control devices\nPersistent storage: Ready\nAutomations: 2 saved / 0 permission issues / 0 failure pauses",
  },
};

const knowledgeMemoryFixture = {
  spaces: [{name:"Household", purpose:"Shared home reference", template:"home", category:"Home", note_count:3}],
  count: 1,
  storage: "local",
};
const knowledgeCategoriesFixture = {categories:[
  {name:"Personal", icon:"person", description:"Things that matter to you.", built_in:true},
  {name:"Home", icon:"home", description:"Household knowledge and routines.", built_in:true},
  {name:"Work", icon:"work", description:"Work and professional reference.", built_in:true},
  {name:"Learning", icon:"study", description:"Study, research, and ideas.", built_in:true},
], count:4};
const knowledgeTemplatesFixture = {templates:[
  {id:"blank", name:"Empty space", description:"Start without any ready-made notes.", icon:"blank", category:"All", notes:[], built_in:true},
  {id:"home", name:"Household organizer", description:"Household information and routines.", icon:"home", category:"Home", notes:[{name:"Overview.md"},{name:"Routines.md"}], built_in:true},
  {id:"work", name:"Work notebook", description:"Decisions and next actions.", icon:"work", category:"Work", notes:[{name:"Overview.md"}], built_in:true},
  {id:"custom:Client kit", name:"Client kit", description:"Reusable client records.", icon:"project", category:"Work", notes:[{name:"Brief.md",purpose:"Client brief",content:"# Brief"}], built_in:false},
], count:4};

let browserChatFixture = [];
const composerPluginFixture = Array.from({length: 6}, (_, index) => ({
  id: `plugin-${index + 1}`, name: `Plugin ${index + 1}`, enabled: index !== 1, healthy: true,
  available_to_chat: true, enabled_tool_count: index + 1, icon_url: index === 0 ? "plugin-icons/github.svg" : "",
}));

function apiFixture(url, method = "GET") {
  const parsedUrl = new URL(url);
  const pathname = parsedUrl.pathname;
  if (pathname === "/api/health") {
    return {
      status: "ok",
      version: "0.13.240",
      speech_provider: "openai",
      speech_providers: {openai: {configured: true}, elevenlabs: {configured: false}},
    };
  }
  if (pathname === "/api/models") return {models: ["gpt-5-mini"]};
  if (pathname === "/api/chats") return {chats: browserChatFixture};
  if (pathname.startsWith("/api/chat/history/")) {
    const sessionId = decodeURIComponent(pathname.split("/").pop() || "");
    if (method === "DELETE") {
      browserChatFixture = browserChatFixture.filter(chat => chat.session_id !== sessionId);
      return {cleared: true, session_id: sessionId};
    }
    const chat = browserChatFixture.find(item => item.session_id === sessionId);
    return {session_id: sessionId, title: chat?.title || "New chat", messages: chat?.messages || []};
  }
  if (pathname === "/api/settings") {
    return {
      preferences: {theme: "dark", model: "gpt-5-mini", reasoning_effort: "medium"},
      voice: {},
      speech_provider: "openai",
      auto_sync_releases_to_workshop_memory: false,
    };
  }
  if (pathname === "/api/knowledge-memory/spaces") return knowledgeMemoryFixture;
  if (pathname === "/api/knowledge-memory/categories") return knowledgeCategoriesFixture;
  if (pathname === "/api/knowledge-memory/templates") return knowledgeTemplatesFixture;
  if (pathname === "/api/knowledge-memory/remember" && method === "POST") return {saved:true,duplicate:false,created_space:false,area:"Home",area_key:"home",icon:"home",space:"Household",note:"Appliances.md",relative_path:"Spaces/Household/Appliances.md"};
  if (pathname === "/api/knowledge-memory/spaces/Household/notes") return {space:"Household", notes:["Overview.md","Routines.md","Important information.md"], count:3};
  if (pathname === "/api/knowledge-memory/spaces/Household/note") return {space:"Household", note:"Overview.md", content:"# Household\n\nShared home reference."};
  if (pathname === "/api/knowledge-memory/search") return {query:"home", results:[{relative_path:"Spaces/Household/Overview.md",excerpt:"Shared home reference."}], count:1};
  if (pathname === "/api/fast-memory") return {memories: [], status: {total: 0, pinned: 0, by_kind: {}, runtime: {running: false}}};
  if (pathname === "/api/onboarding") {
    if (method === "PUT") onboardingFixture.completed = true;
    return onboardingFixture;
  }
  if (pathname === "/api/ha/entities") {
    return {entities, count: entities.length, domains: ["sensor", "climate", "light"], source: "browser fixture"};
  }
  if (pathname === "/api/ha/approved") {
    const policy=Object.fromEntries(entities.filter(entity=>["light","switch","climate"].includes(entity.domain)).map(entity=>[entity.entity_id,{enabled:true,access:"low_risk_control_proposed",friendly_name:entity.friendly_name,domain:entity.domain,aliases:[],source:"default_control"}]));
    return {policy, read_entities: [], control_entities: Object.keys(policy)};
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
    return {settings: {}, channels: [
      {entity_id: "notify.browser_phone", friendly_name: "Browser Phone", platform: "home_assistant", available: true, state: "unknown", availability_label: "Ready · status not reported"},
      {entity_id: "notify.old_phone", friendly_name: "Old Phone", platform: "home_assistant", available: false, state: "unavailable", availability_label: "Unavailable"},
    ], watches: [], deliveries: [], telegram_channels: 0};
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
  }, ...Array.from({length:40}, (_, index) => ({
    id:`contact-fixture-${index}`,kind:"person",display_name:`Fixture Contact ${index + 1}`,given_name:"Fixture",family_name:`Contact ${index + 1}`,
    company_name:"",job_title:"",phone_numbers:[],emails:[`fixture${index + 1}@example.com`],birthday:"",birth_year:null,
    relationship:"Test contact",address:"",website:"",notes:"",has_bank_details:false,
  }))],count:41};
  if (pathname === "/api/contacts/google/status") return {connected:false,account:""};
  if (pathname === "/api/calendar/google/status") return {connected: false, enabled: false, pending_local_changes: 0};
  if (pathname === "/api/plugins") return {plugins: composerPluginFixture};
  if (pathname === "/api/files/shared/folders") return {folders: [{name:"Documents",path:"Documents"}]};
  if (pathname === "/api/files/shared") {
    if (parsedUrl.searchParams.get("folder") === "Documents") return {files:[{file_id:"abcdefabcdefabcdefabcdef",name:"Manual.pdf",created_at:1788300000,mime_type:"application/pdf",size:2048,folder:"Documents"}],folders:[],current_folder:"Documents"};
    return {files:[],folders:[{name:"Documents",path:"Documents",file_count:1}],current_folder:""};
  }
  if (pathname === "/api/release-memory-sync") {
    return {enabled: false, state: "disabled", version: "0.13.240", task_active: false};
  }
  if (pathname === "/api/tab-activity") return {revisions: {}};
  if (pathname === "/api/grinder-monitor/status") return {enabled: false, connected: false};
  if (pathname === "/api/voice/wake-calibration") {
    return {enabled: false, samples: [], verifier: {enabled: false}};
  }
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
    // Multi-architecture image builds may execute Chromium through QEMU. Keep
    // the assertions strict while allowing UI actions enough time on emulated ARM.
    page.setDefaultTimeout(60000);
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
    assert.equal(await page.locator("#developer-tab").count(), 0, "Developer navigation must not be exposed");
    assert.equal(await page.locator("#developer-panel").count(), 0, "Developer workspace must not be exposed");

    const chooseLanguage = value => page.locator("#preferred-language").evaluate((element, language) => {
      element.value = language;
      element.dispatchEvent(new Event("change", {bubbles: true}));
    }, value);
    await chooseLanguage("Greek");
    assert.equal(await page.locator("#chat-tab").innerText(), "Συνομιλία");
    assert.equal(await page.locator("#settings-tab span").innerText(), "Ρυθμίσεις");
    assert.equal(await page.evaluate(() => window.ZbranoI18n.t("Automation Studio")), "Στούντιο αυτοματισμών");
    await page.locator("#about-tab").click();
    await page.locator("#about-panel:not(.hidden)").waitFor();
    assert.match(await page.locator("#about-panel").innerText(), /Όλα λειτουργούν ως ένας βοηθός/);
    assert.match(await page.locator("#about-panel").innerText(), /Οπτικοί αυτοματισμοί/);
    assert.match(await page.locator("#about-panel").innerText(), /Αρχεία και καθημερινή οργάνωση/);
    const dynamicTitle = await page.evaluate(() => {
      const button = document.createElement("button");
      button.title = "Save automation";
      document.body.append(button);
      button.title = "Run diagnostics";
      return new Promise(resolve => requestAnimationFrame(() => resolve(button.title)));
    });
    assert.equal(dynamicTitle, "Εκτέλεση διαγνωστικών");
    assert.equal(await page.locator("html").getAttribute("lang"), "el");
    assert.match(await page.locator("#messages").innerText(), /intelligence core online/i, "User and assistant messages must not be translated as interface copy");
    await chooseLanguage("Italian");
    assert.equal(await page.locator("#settings-tab span").innerText(), "Impostazioni");
    assert.equal(await page.evaluate(() => window.ZbranoI18n.t("Automation Studio")), "Studio automazioni");
    assert.equal(await page.locator("html").getAttribute("lang"), "it");
    await chooseLanguage("French");
    assert.equal(await page.locator("#chat-tab").innerText(), "Discussion");
    assert.equal(await page.evaluate(() => window.ZbranoI18n.t("Automation Studio")), "Studio d’automatisation");
    assert.equal(await page.locator("html").getAttribute("lang"), "fr");
    await chooseLanguage("English");
    assert.equal(await page.locator("#chat-tab").innerText(), "Chat");
    assert.equal(await page.locator("#settings-tab span").innerText(), "Settings");
    assert.equal(await page.locator("html").getAttribute("lang"), "en");
    await page.locator("#chat-tab").click();
    await page.locator("#chat-panel:not(.hidden)").waitFor();

    // Wait for the chat-tab refresh to finish before measuring icon geometry.
    await page.waitForLoadState("networkidle");
    await page.waitForFunction(() => document.querySelectorAll("#composer-plugin-icons .composer-plugin-button").length === 6);
    assert.equal(await page.locator("#composer-plugins-open, #composer-plugin-count").count(), 0);
    assert.equal(await page.locator("#composer-plugin-icons .composer-plugin-button").count(), 6);
    await page.locator('[data-composer-plugin="plugin-1"] svg.composer-plugin-inline-icon').waitFor();
    const githubComposerIcon = await page.locator('[data-composer-plugin="plugin-1"] svg').evaluate(icon => icon.outerHTML);
    assert.match(githubComposerIcon, /<path\b/, githubComposerIcon);
    assert.equal(await page.locator('[data-composer-plugin="plugin-2"]').getAttribute("class"), "composer-plugin-button disabled");
    for (const width of [1100, 390]) {
      await page.setViewportSize({width, height:720});
      const last = page.locator('[data-composer-plugin="plugin-6"]');
      // Background plugin refresh can replace a button during Playwright's
      // stability wait. Re-resolve only that transient detachment; keep all
      // visibility and reachability assertions below.
      for (let attempt = 0; ; attempt++) {
        try { await last.scrollIntoViewIfNeeded(); break; }
        catch (error) {
          if (attempt >= 2 || !String(error).includes("not attached to the DOM")) throw error;
        }
      }
      assert.ok(await last.isVisible());
      const reachable = await last.evaluate(button => {
        const b=button.getBoundingClientRect(), r=button.parentElement.getBoundingClientRect();
        return b.left>=r.left-1 && b.right<=r.right+1;
      });
      assert.ok(reachable, `Last installed plugin is reachable at ${width}px`);
    }
    await page.setViewportSize({width:1100, height:720});
    await page.locator('[data-composer-plugin="plugin-1"]').scrollIntoViewIfNeeded();
    for (const theme of ["light", "dark", "gray"]) {
      await page.evaluate(theme => document.documentElement.dataset.theme = theme, theme);
      const geometry = await page.locator('[data-composer-plugin="plugin-1"]').evaluate(button => {
        const icon = button.querySelector("svg");
        const b = button.getBoundingClientRect(), i = icon.getBoundingClientRect();
        return {padding: getComputedStyle(button).padding, centered: Math.abs((b.left+b.right-i.left-i.right)/2)<1 && Math.abs((b.top+b.bottom-i.top-i.bottom)/2)<1,
          contained: i.left>=b.left && i.right<=b.right && i.top>=b.top && i.bottom<=b.bottom};
      });
      assert.ok(geometry.contained && geometry.centered, JSON.stringify({theme, geometry}));
    }
    await page.evaluate(() => document.documentElement.dataset.theme = "light");
    assert.equal(await page.locator("#composer-preferences-popover").isHidden(), true);
    await page.locator("#composer-preferences-toggle").click();
    assert.equal(await page.locator("#composer-preferences-popover").isVisible(), true);
    assert.equal(await page.locator("#composer-preferences-toggle").getAttribute("aria-expanded"), "true");
    await page.locator("#voice-select").selectOption("marin");
    assert.match(await page.locator("#composer-preferences-summary").innerText(), /Marin/);
    await page.keyboard.press("Escape");
    assert.equal(await page.locator("#composer-preferences-popover").isHidden(), true);

    let catalogRequests = 0;
    await page.route("**/api/plugin-catalog?*", async route => {
      catalogRequests++;
      const plugins = [{id:"featured", title:"Featured fixture", url:"https://example.com/mcp"}];
      if(catalogRequests>1)plugins.push({id:"updated", title:"Updated fixture", url:"https://example.org/mcp"});
      await route.fulfill({status:200, contentType:"application/json", body:JSON.stringify({plugins, refreshing:catalogRequests===1})});
    });
    await page.locator("#plugins-tab").click();
    await page.locator("#plugin-list .plugin-row").first().waitFor();
    assert.equal(catalogRequests, 0, "Installed view does not start a registry fetch");
    await page.locator("#plugins-browse-tab").click();
    await page.getByRole("heading", {name:"Featured fixture", exact:true}).waitFor();
    await page.getByRole("heading", {name:"Updated fixture", exact:true}).waitFor();
    assert.ok(catalogRequests>=2, "Background catalog refresh updates the visible cards");
    await page.unroute("**/api/plugin-catalog?*");

    await page.locator("#files-tab").click();
    await page.locator("#files-panel:not(.hidden)").waitFor();
    await page.locator('[data-shared-folder="Documents"]').click();
    await page.locator('#shared-file-rows tr').filter({hasText:"Manual.pdf"}).waitFor();
    assert.match(await page.locator("#shared-breadcrumbs").innerText(), /Shared Files.*Documents/s);
    assert.match(await page.locator("#shared-move-target").innerText(), /Shared Files \(main\)/);
    assert.equal(await page.locator("#shared-new-folder").isVisible(), true);
    assert.equal(await page.locator("#shared-upload-here").isVisible(), true);
    await page.locator("#chat-tab").click();
    await page.locator("#chat-panel:not(.hidden)").waitFor();

    const actionCard = await page.evaluate(() => {
      const item = document.createElement('div'); item.className = 'message zbrano'; renderMessageContent(item, 'Living room is now off.');
      renderDeviceActionResult(item, {route:'local',success:true,tool:'turn_off_home_assistant_entity',friendly_name:'Living room <AC>',verified_state:'off'});
      const card = {text:item.textContent, raw:item.dataset.rawText, styled:item.classList.contains('device-action-result'), injected:!!item.querySelector('ac')};
      const failed = document.createElement('div'); renderDeviceActionResult(failed, {route:'local',success:false,tool:'turn_off_home_assistant_entity',verified_state:'off'});
      return {...card, failedStyled:failed.classList.contains('device-action-result')};
    });
    assert.equal(actionCard.styled, true); assert.equal(actionCard.injected, false); assert.equal(actionCard.failedStyled, false);
    assert.equal(actionCard.raw, 'Living room is now off.'); assert.match(actionCard.text, /Living room <AC>Off/);
    await page.evaluate(() => {
      window.savedClipboard = Object.getOwnPropertyDescriptor(navigator, 'clipboard');
      Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copiedMessage=text;}}});
      addMessage('**Keep formatting**\nSecond line', 'zbrano').id='copy-fixture';
    });
    await page.locator('#copy-fixture .message-copy').click();
    assert.equal(await page.evaluate(()=>window.copiedMessage), '**Keep formatting**\nSecond line');
    assert.equal(await page.locator('#copy-fixture .message-copy-status').innerText(), 'Copied');
    if(process.env.ZBRANO_CHAT_SCREENSHOT)await page.locator('#copy-fixture').screenshot({animations:'disabled',path:process.env.ZBRANO_CHAT_SCREENSHOT.replace('.png','-message.png')});
    await page.evaluate(()=>{navigator.clipboard.writeText=async()=>{throw new Error('Clipboard denied');};});
    await page.locator('#copy-fixture .message-copy').click();
    assert.match(await page.locator('#copy-fixture .message-copy-status').innerText(), /Copy failed/);
    await page.evaluate(()=>{
      Object.defineProperty(navigator,'clipboard',{configurable:true,value:undefined});
      window.savedExecCommand=document.execCommand;
      document.execCommand=command=>{window.fallbackCopy={command,text:document.activeElement.value};return true;};
    });
    await page.locator('#copy-fixture .message-copy').click();
    assert.deepEqual(await page.evaluate(()=>window.fallbackCopy), {command:'copy',text:'**Keep formatting**\nSecond line'});
    assert.equal(await page.locator('.clipboard-fallback').count(),0);
    await page.evaluate(()=>{document.execCommand=window.savedExecCommand;});
    await page.evaluate(()=>{
      document.getElementById('copy-fixture').remove();
      if(window.savedClipboard)Object.defineProperty(navigator,'clipboard',window.savedClipboard);else delete navigator.clipboard;
    });
    const stoppedMarkdown = await page.evaluate(() => {
      const item = document.createElement("div");
      item.className = "message zbrano";
      const original = "### Beef soup\n\n1. Brown the beef.\n2. Add stock.\n\n**Tip:** Simmer gently.";
      renderMessageContent(item, original);
      finishInterruptedMessage(item, "[Response stopped]", "Response stopped.");
      return {raw: item.dataset.rawText, html: item.innerHTML};
    });
    assert.equal(stoppedMarkdown.raw, "### Beef soup\n\n1. Brown the beef.\n2. Add stock.\n\n**Tip:** Simmer gently.\n\n[Response stopped]");
    assert.match(stoppedMarkdown.html, /<h4>Beef soup<\/h4>/);
    assert.match(stoppedMarkdown.html, /<ol>/);
    assert.match(stoppedMarkdown.html, /<strong>Tip:<\/strong>/);

    const composerStartHeight = await page.locator("#message").evaluate(element => element.getBoundingClientRect().height);
    assert.equal(await page.locator("#message").evaluate(element => getComputedStyle(element).fieldSizing), "content");
    await page.locator("#message").fill("discard this draft\nwith a second visual line");
    assert.ok(await page.locator("#message").evaluate(element => element.getBoundingClientRect().height) > composerStartHeight);
    await page.locator("#new-chat-button").click();
    assert.equal(await page.locator("#message").inputValue(), "");
    await page.locator('#chat-list .chat-list-item[data-draft="true"]').waitFor();
    assert.match(await page.locator("#messages").innerText(), /intelligence core online/i);

    browserChatFixture = [{
      session_id: "only-saved-chat",
      title: "Only saved conversation",
      updated_at: 1,
      message_count: 2,
      messages: [
        {role: "user", content: "Hello"},
        {role: "assistant", content: "Hello from ZBRANO"},
      ],
    }];
    await page.evaluate(() => openChat("only-saved-chat"));
    await page.locator('#chat-search').fill('ONLY SAVED');
    assert.equal(await page.locator('#chat-list .chat-list-item:visible').count(), 1);
    await page.locator('#chat-search').fill('no matching title');
    assert.equal(await page.locator('#chat-search-empty').isVisible(), true);
    assert.equal(await page.locator('#chat-list .chat-list-item:visible').count(), 0);
    await page.evaluate(() => refreshChatList());
    assert.equal(await page.locator('#chat-list .chat-list-item:visible').count(), 0);
    await page.locator('#chat-search').press('Escape');
    assert.equal(await page.locator('#chat-search').inputValue(), '');
    assert.equal(await page.locator('#chat-list .chat-list-item:visible').count(), 1);
    await page.evaluate(() => {
      for(let i=0;i<40;i++)addMessage(`Earlier message ${i}`, 'zbrano');
      messages.scrollTop=0;
    });
    await page.locator('#chat-latest').waitFor({state:'visible'});
    await page.locator('#chat-latest').click();
    assert.equal(await page.locator('#chat-latest').isVisible(), false);
    assert.equal(await page.evaluate(() => isNearMessagesBottom()), true);

    if (process.env.ZBRANO_CHAT_SCREENSHOT) {
      for (const theme of ["light", "dark"]) {
        await page.evaluate(value => document.documentElement.dataset.theme = value, theme);
        await page.locator(".chat-sidebar").screenshot({animations:"disabled", path:process.env.ZBRANO_CHAT_SCREENSHOT.replace(".png", `-${theme}.png`)});
      }
      await page.evaluate(() => document.documentElement.dataset.theme = "light");
    }
    await page.locator('#chat-list .chat-list-item.active .chat-delete').click();
    await page.locator('#chat-list .chat-list-item[data-draft="true"]').waitFor();
    assert.equal(await page.locator("#chat-list .chat-list-item").count(), 1);
    assert.equal(await page.locator("#chat-list").innerText(), "New chat");
    assert.equal(browserChatFixture.length, 0);

    await page.waitForFunction(() => document.getElementById("brain-network")?.dataset.animationState === "running");
    await page.evaluate(() => setNeuronIntensity(false));
    await page.waitForFunction(() => document.getElementById("brain-network")?.dataset.animationState === "paused");
    await page.evaluate(() => setNeuronIntensity(true));
    await page.waitForFunction(() => document.getElementById("brain-network")?.dataset.animationState === "running");
    await page.locator("#messages .message").evaluate(element => {
      const selection = document.getSelection();
      const range = document.createRange();
      range.selectNodeContents(element);
      selection.removeAllRanges();
      selection.addRange(range);
    });
    await page.waitForFunction(() => document.getElementById("brain-network")?.dataset.animationState === "paused");
    await page.evaluate(() => document.getSelection()?.removeAllRanges());
    await page.waitForFunction(() => document.getElementById("brain-network")?.dataset.animationState === "running");

    await page.locator("#about-tab").click();
    await page.locator("#about-panel:not(.hidden)").waitFor();
    assert.equal(await page.locator("#chat-panel").isHidden(), true);
    assert.match(await page.locator("#about-title").innerText(), /One assistant for your home/i);
    assert.equal(await page.locator("#about-panel .about-feature").count(), 8);
    assert.match(await page.locator("#about-panel").innerText(), /Natural conversation/i);
    assert.match(await page.locator("#about-panel").innerText(), /Home awareness and control/i);
    assert.match(await page.locator("#about-panel").innerText(), /Visual automations/i);
    assert.match(await page.locator("#about-panel").innerText(), /Files and everyday organization/i);
    assert.match(await page.locator("#about-panel").innerText(), /Language and personalization/i);
    assert.match(await page.locator("#about-panel").innerText(), /Safety and ownership/i);
    assert.equal(await page.locator(".about-journey > ol li").count(), 4);
    const aboutScroll = await page.locator("#about-panel").evaluate(element => {
      element.scrollTop = element.scrollHeight;
      return {overflowY:getComputedStyle(element).overflowY, moved:element.scrollTop > 0};
    });
    assert.equal(aboutScroll.overflowY, "auto");
    assert.equal(aboutScroll.moved, true, "About showcase must scroll inside its panel");
    await page.locator("#about-open-files").click();
    await page.locator("#files-panel:not(.hidden)").waitFor();
    await page.locator("#about-tab").click();
    await page.locator("#about-open-memory").click();
    await page.locator("#memory-panel:not(.hidden)").waitFor();
    await page.locator("#about-tab").click();
    await page.locator("#about-open-devices").click();
    await page.locator("#entities-panel:not(.hidden)").waitFor();
    assert.equal(await page.locator("#about-panel").isHidden(), true);

    await page.locator("#entities-tab").click();
    await page.locator("#entities-panel:not(.hidden)").waitFor();
    await page.locator("#device-grid .device-card").first().waitFor();
    assert.equal(await page.locator("#entity-layout").inputValue(), "cards");
    assert.equal(await page.locator("#device-grid .device-card").count(), 60);
    await page.locator("#device-show-more").click();
    assert.equal(await page.locator("#device-grid .device-card").count(), entities.length-1);
    assert.equal(await page.locator("#entities-panel .table-wrap").isHidden(), true);
    assert.doesNotMatch(await page.locator("#device-grid").innerText(), /climate\.browser_thermostat/);
    await page.locator("#device-room-nav").getByRole("button", {name:/^Living room/}).click();
    assert.equal(await page.locator("#device-grid .device-card").count(), 1);
    const cardAllow = page.locator('[data-device-allow="device:fixture-ac"]');
    const cardMode = page.locator('[data-device-mode="device:fixture-ac"]');
    assert.equal(await cardAllow.evaluate(input => input.indeterminate), true);
    assert.equal(await cardMode.inputValue(), "control");
    const cardRead = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/climate.browser_thermostat") && request.postDataJSON().access==="state_only");
    await cardMode.selectOption("read");
    assert.equal((await cardRead).postDataJSON().enabled, true);
    assert.equal(await cardAllow.evaluate(input => input.indeterminate), true);
    const cardControl = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/climate.browser_thermostat") && request.postDataJSON().access==="low_risk_control_proposed");
    await cardMode.selectOption("control");
    await cardControl;
    assert.equal(await page.locator("#device-details").isHidden(), true, "Card controls do not open details");
    await page.locator('[data-device-open="device:fixture-ac"]').click();
    assert.equal(await page.locator("#device-details .device-entity").count(), 2);
    assert.match(await page.locator("#device-details").innerText(), /Mixed access/);
    for(const theme of ["dark", "light"]) {
      await page.evaluate(theme => document.documentElement.dataset.theme=theme, theme);
      assert.ok(await page.locator("#device-details").isVisible());
      if(process.env.ZBRANO_DEVICE_SCREENSHOT)await page.screenshot({animations:"disabled", path:process.env.ZBRANO_DEVICE_SCREENSHOT.replace(".png", `-${theme}.png`)});
    }
    const relatedSensor = page.locator('[data-device-entity="sensor.browser_fixture_1"]');
    await relatedSensor.locator("summary").first().click();
    assert.equal(await relatedSensor.locator(".device-history").isEnabled(), false);
    const sensorPermission = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/sensor.browser_fixture_1"));
    await relatedSensor.locator('input[type="checkbox"]').check();
    assert.equal((await sensorPermission).postDataJSON().enabled, true);
    assert.equal(await page.locator('[data-device-entity="climate.browser_thermostat"] input[type="checkbox"]').isChecked(), true);
    const aliasSave = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/sensor.browser_fixture_1") && request.postDataJSON().aliases?.includes("Room comfort"));
    await relatedSensor.locator('input:not([type="checkbox"])').fill("Room comfort");
    await relatedSensor.locator('input:not([type="checkbox"])').blur();
    assert.deepEqual((await aliasSave).postDataJSON().aliases, ["Room comfort"]);
    const historyRead = page.waitForRequest(request => request.url().includes("api/ha/timeline?"));
    await relatedSensor.locator(".device-history").click();
    assert.equal(new URL((await historyRead).url()).searchParams.get("entity_ids"), "sensor.browser_fixture_1");
    await page.locator('[data-entity-view="inventory"]').click();
    await page.getByRole("button", {name:"Close device details", exact:true}).click();
    const disableDevice = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/climate.browser_thermostat") && request.postDataJSON().enabled===false);
    const disableSensor = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/sensor.browser_fixture_1") && request.postDataJSON().enabled===false);
    await cardAllow.uncheck();
    await Promise.all([disableDevice,disableSensor]);
    const disabledMode = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/climate.browser_thermostat") && request.postDataJSON().access==="state_only");
    await cardMode.selectOption("read");
    assert.equal((await disabledMode).postDataJSON().enabled, false, "Changing mode does not enable a blocked device");
    const enableDevice = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/climate.browser_thermostat") && request.postDataJSON().enabled===true);
    const enableSensor = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/sensor.browser_fixture_1") && request.postDataJSON().enabled===true);
    await cardAllow.check();
    assert.equal((await enableDevice).postDataJSON().access, "state_only");
    const sensorEnabledPayload = (await enableSensor).postDataJSON();
    assert.equal(sensorEnabledPayload.access, "read_only");
    assert.deepEqual(sensorEnabledPayload.aliases, ["Room comfort"]);
    const restoreControl = page.waitForRequest(request => request.method()==="PUT" && request.url().includes("entity-policy/climate.browser_thermostat") && request.postDataJSON().access==="low_risk_control_proposed");
    await cardMode.selectOption("control");
    await restoreControl;
    await page.locator(".device-favorite").click();
    await page.locator('[data-device-location="favorites"]').click();
    assert.equal(await page.locator("#device-grid .device-card").count(), 1);
    assert.match(await page.evaluate(() => localStorage.getItem("zbrano_device_favorites_v1")), /fixture-ac/);
    await page.locator("#device-clear-filters").click();
    await page.locator('#device-sort').selectOption('name-desc');
    const descendingNames = await page.locator('#device-grid .device-name').allTextContents();
    assert.ok(descendingNames[0].localeCompare(descendingNames.at(-1), 'en', {numeric:true}) > 0);
    await page.locator('#device-sort').selectOption('room');
    assert.equal(await page.locator('#device-grid .device-room').first().innerText(), 'Office');
    await page.evaluate(() => { entityInventory.find(e=>e.entity_id==='sensor.browser_fixture_78').available=false; renderEntities(); });
    await page.locator('#device-sort').selectOption('unavailable');
    assert.equal(await page.locator('#device-grid [data-device-open]').first().getAttribute('data-device-open'), 'entity:sensor.browser_fixture_78');
    await page.locator('#entity-more > summary').click();
    await page.locator('#device-favorites-first').check();
    assert.equal(await page.locator('#device-grid [data-device-open]').first().getAttribute('data-device-open'), 'device:fixture-ac');
    assert.deepEqual(await page.evaluate(()=>JSON.parse(localStorage.getItem('zbrano_device_order_v1'))), {sort:'unavailable',favoritesFirst:true});
    await page.locator('#device-favorites-first').uncheck();
    await page.locator('#entity-more > summary').click();
    await page.evaluate(() => { entityInventory.find(e=>e.entity_id==='sensor.browser_fixture_78').available=true; renderEntities(); });
    await page.locator('#device-sort').selectOption('name');
    const longName = page.locator('[data-device-open="entity:sensor.browser_fixture_2"] .device-name');
    assert.equal(await longName.getAttribute("title"), entities[1].device_name);
    assert.ok(await longName.evaluate(name => name.getBoundingClientRect().height <= parseFloat(getComputedStyle(name).lineHeight)+1));
    assert.ok(await longName.locator("xpath=ancestor::article").evaluate(card => card.getBoundingClientRect().width > card.getBoundingClientRect().height*1.5));
    assert.equal(await page.locator('[data-device-mode="entity:sensor.browser_fixture_2"] option[value="control"]').count(), 0);
    await page.locator("#entity-search").fill("Room comfort");
    assert.equal(await page.locator("#device-grid .device-card").count(), 1);
    await page.locator("#device-clear-filters").click();
    await page.locator('[data-device-filter="unavailable"]').click();
    assert.equal(await page.locator("#device-grid .device-card").count(), 0);
    await page.locator("#device-clear-filters").click();
    await page.setViewportSize({width:390,height:720});
    await page.locator('[data-mobile-tab="chat-tab"]').click();
    assert.equal(await page.locator('#chat-panel').isVisible(), true);
    assert.equal(await page.locator('#mobile-navigation > button svg').count(), 4);
    await page.evaluate(() => window.zbranoMarkTabChanged('settings-tab'));
    await page.locator('#mobile-navigation > button.has-activity').waitFor();
    assert.equal(await page.locator('#mobile-more [data-mobile-tab="settings-tab"]').getAttribute('class'), 'has-activity');
    await page.locator('#mobile-navigation > button').last().click();
    if(process.env.ZBRANO_DEVICE_SCREENSHOT)await page.screenshot({animations:'disabled',path:process.env.ZBRANO_DEVICE_SCREENSHOT.replace('.png','-more.png')});
    await page.locator('#mobile-more [data-mobile-tab="settings-tab"]').click();
    assert.equal(await page.locator('#settings-panel').isVisible(), true);
    assert.equal(await page.locator('#mobile-more').isVisible(), false);
    await page.waitForFunction(() => !document.querySelector('#mobile-more [data-mobile-tab="settings-tab"]').classList.contains('has-activity'));

    await page.locator('[data-mobile-tab="entities-tab"]').click();
    assert.equal(await page.locator('#entities-panel').isVisible(), true);

    await page.locator("#entity-search").fill("Living Room AC");
    if(process.env.ZBRANO_DEVICE_SCREENSHOT){
      await page.screenshot({animations:"disabled",path:process.env.ZBRANO_DEVICE_SCREENSHOT.replace('.png','-mobile.png')});
    }
    await page.locator('[data-device-open="device:fixture-ac"]').click();
    assert.ok(await page.locator("#device-details").evaluate(element => {const r=element.getBoundingClientRect(); return r.left>=0 && r.right<=innerWidth && r.bottom<=innerHeight;}));
    await page.keyboard.press("Escape");
    await page.setViewportSize({width:1100,height:720});
    await page.locator("#device-clear-filters").click();
    await page.locator("#entity-layout").selectOption("table");
    await page.locator("#entity-rows tr").nth(47).waitFor();
    const entityHeaders = await page.locator('#entities-panel thead th').allTextContents();
    assert.deepEqual(entityHeaders.slice(0, 5), [
      'Allow',
      'Device or sensor',
      'Current value',
      'How ZBRANO may use it',
      'Room / area',
    ]);
    const thermostatRow = page.locator("#entity-rows tr").filter({hasText:"Browser Thermostat"});
    assert.equal(await thermostatRow.locator('[data-entity-column="state"]').innerText(), "cool · set to 25 °C");
    assert.match(await thermostatRow.locator('[data-entity-column="state"]').getAttribute("title"), /Current 26.2 °C · Action cooling/);

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
    await page.locator('#entity-permission-guide summary').click();
    assert.match(await page.locator('#entity-permission-guide').innerText(), /allowed as Control devices by default/i);
    assert.match(await page.locator('[data-entity-permission-filter="sensor"]').innerText(), /read information only/i);
    assert.match(await page.locator('[data-entity-permission-filter="control"]').innerText(), /can perform actions/i);
    await page.locator('[data-entity-permission-filter="control"]').click();
    assert.equal(await page.locator('#entity-permission-guide').getAttribute('open'), null);
    assert.deepEqual(await page.locator('#entities-panel .table-wrap').evaluate(element => ({top:element.scrollTop,left:element.scrollLeft})), {top:0,left:0});
    assert.equal(await page.locator('#entity-rows tr').count(), 3);
    assert.match(await page.locator('#entity-rows').innerText(), /Browser Thermostat/i);
    assert.match(await page.locator('#entity-rows').innerText(), /Browser Fixture Light/i);
    const explicitControlRow = page.locator('#entity-rows tr').filter({hasText:'Browser Fixture Light'});
    assert.equal(await explicitControlRow.locator('input[type="checkbox"]').isChecked(), true);
    assert.equal(await explicitControlRow.locator('input[type="checkbox"]').isEnabled(), true);
    assert.deepEqual(await explicitControlRow.locator('select option').allTextContents(), [
      'Sensor device · read status only',
      'Control device · allow actions',
      'Do not allow',
    ]);
    assert.equal(await explicitControlRow.locator('select option:checked').innerText(), 'Control device · allow actions');
    await explicitControlRow.locator('input[type="checkbox"]').check();
    await explicitControlRow.locator('select').selectOption('restricted');
    assert.equal(await explicitControlRow.locator('input[type="checkbox"]').isChecked(), false);
    await explicitControlRow.locator('input[type="checkbox"]').check();
    assert.equal(await explicitControlRow.locator('select').inputValue(), 'state_only');
    await page.locator('#entity-permission-guide summary').click();
    await page.locator('[data-entity-permission-filter="sensor"]').click();
    const explicitSensorRow = page.locator('#entity-rows tr').first();
    assert.deepEqual(await explicitSensorRow.locator('select option').allTextContents(), [
      'Sensor device · read information',
      'Do not allow',
    ]);
    await page.locator('#entity-permission-guide summary').click();
    await page.locator('[data-entity-permission-filter="all"]').click();

    await page.locator("#contacts-tab").click();
    await page.locator("#contacts-panel:not(.hidden)").waitFor();
    await page.getByText("Alex Morgan", {exact:true}).waitFor();
    assert.match(await page.locator("#contacts-list").innerText(), /Alex Morgan/);
    assert.match(await page.locator("#contacts-list").innerText(), /alex@example.com/);
    const contactsScroll = await page.locator(".contacts-content").evaluate(element => {element.scrollTop=element.scrollHeight;return {overflowY:getComputedStyle(element).overflowY,vertical:element.scrollTop>0};});
    assert.equal(contactsScroll.overflowY, "auto");
    assert.equal(contactsScroll.vertical, true, "Contacts must scroll inside its full-height workspace");
    await page.locator("#contacts-layout").selectOption("list");
    assert.equal(await page.locator("#contacts-list").getAttribute("data-layout"), "list");
    await page.locator("#contacts-layout").selectOption("compact");
    assert.equal(await page.locator("#contacts-list").getAttribute("data-layout"), "compact");
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
    const guideStripBox=await page.locator(".automation-studio-guide-strip").boundingBox(),blockBarBox=await page.locator(".automation-studio-toolbox").boundingBox(),flowCanvasBox=await page.locator("#automation-studio-canvas").boundingBox();
    assert.ok(guideStripBox.y < blockBarBox.y && blockBarBox.y < flowCanvasBox.y);
    assert.equal(await page.locator(".automation-block-category").count(), 4);
    assert.equal(await page.locator('.automation-studio-toolbox [data-studio-node="details"]').count(), 0);
    assert.equal(await page.locator('.automation-studio-guide-strip [data-studio-node="details"]').count(), 1);
    assert.equal(await page.locator("[data-tool-trigger]").count(), 7);
    assert.equal(await page.locator("[data-tool-condition]").count(), 5);
    assert.equal(await page.locator("[data-tool-action]").count(), 5);
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "1. Setup & safety");
    assert.equal(await page.locator("#automation-studio-current-step").innerText(), "Step 1 of 5");
    assert.equal(await page.locator("#automation-studio-step-back").isDisabled(), true);
    assert.equal(await page.locator("#studio-automation-execution-policy").count(), 0);
    assert.equal(await page.locator("#studio-automation-require-presence").isChecked(), false);
    assert.equal(await page.locator("#studio-automation-presence").isDisabled(), true);
    await page.locator("#studio-automation-require-presence").check();
    assert.equal(await page.locator("#studio-automation-presence").isEnabled(), true);
    await page.locator("#studio-automation-presence").fill("person.browser_fixture");
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="context"]').innerText(), /browser_fixture/i);
    await page.locator("#studio-automation-require-presence").uncheck();
    assert.equal(await page.locator("#studio-automation-presence").isDisabled(), true);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="context"]').count(), 0);
    assert.match(await page.locator("#automation-studio-inspector-fields").innerText(), /Enable automation on saving/i);
    await page.locator("#automation-studio-step-next").click();
    assert.match(await page.locator("#automation-studio-state").innerText(), /Complete this step first/i);
    await page.locator("#studio-automation-name").fill("A");
    await page.locator("#studio-automation-objective").fill("B");
    await page.locator("#automation-studio-step-next").click();
    assert.match(await page.locator("#automation-studio-state").innerText(), /at least 2 characters/i);
    await page.locator("#studio-automation-name").fill("Guided browser flow");
    await page.locator("#studio-automation-objective").fill("Verify the guided setup path");
    await page.locator("#automation-studio-step-next").click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "2. When");
    assert.equal(await page.locator("#automation-studio-current-step").innerText(), "Step 2 of 5");
    assert.equal(await page.locator('.automation-trigger-palette [data-trigger-preset]').count(), 7);
    assert.equal(await page.locator('.automation-trigger-palette [data-trigger-preset="sensor"]').getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator("#studio-automation-trigger-entity").count(), 1);
    assert.equal(await page.locator("#studio-automation-trigger-sun-event").count(), 0);
    await page.locator('[data-trigger-preset="power_on"]').click();
    assert.equal(await page.locator('[data-trigger-preset="power_on"]').getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator("#studio-automation-trigger-operator").count(), 0);
    assert.equal(await page.locator("#studio-automation-trigger-value").count(), 0);
    assert.doesNotMatch(await page.locator("#automation-studio-inspector-fields").innerText(), /What should it do\?|Compared with what value\?/i);
    await page.locator("#studio-automation-trigger-entity").fill("climate.browser_thermostat");
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').first().click();
    assert.equal(await page.locator('[data-trigger-preset="power_on"]').getAttribute("aria-pressed"), "true");
    await page.locator('[data-trigger-preset="power_off"]').click();
    assert.equal(await page.locator('[data-trigger-preset="power_off"]').getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator("#studio-automation-trigger-operator").count(), 0);
    assert.equal(await page.locator("#studio-automation-trigger-value").count(), 0);
    await page.locator('[data-trigger-preset="sun"]').click();
    assert.equal(await page.locator("#studio-automation-trigger-sun-event").count(), 1);
    assert.equal(await page.locator("#studio-automation-trigger-entity").count(), 0);
    assert.equal(await page.locator("#studio-automation-trigger-at").count(), 0);
    await page.locator('[data-trigger-preset="sensor"]').click();
    await page.locator("#studio-automation-trigger-operator").selectOption("any_change");
    assert.equal(await page.locator("#studio-automation-trigger-value").count(), 0);
    await page.locator("#studio-automation-trigger-operator").selectOption("above");
    assert.equal(await page.locator("#studio-automation-trigger-value").count(), 1);
    await page.locator("#studio-automation-trigger-operator").selectOption("changes_to");
    await page.locator('[data-tool-condition="entity"]').click();
    const sharedConditionEntity=page.locator('[data-workflow-index="0"][data-condition-field="entity_id"]');
    await sharedConditionEntity.focus();
    await page.locator('[data-workflow-index="0"] + .automation-entity-results .automation-entity-result').first().waitFor();
    await sharedConditionEntity.press("Escape");
    await page.locator('[data-tool-action="turn_on"]').click();
    const friendlyActionEntity=page.locator('[data-workflow-index="0"][data-action-field="entity_id"]');
    await friendlyActionEntity.focus();
    await page.locator('[data-workflow-index="0"] + .automation-entity-results .automation-entity-result').first().waitFor();
    await friendlyActionEntity.press("Escape");
    const pickerResetDialogPromise=page.waitForEvent("dialog"),pickerResetClick=page.locator("#automation-studio-new").click();
    const pickerResetDialog=await pickerResetDialogPromise;await pickerResetDialog.accept();await pickerResetClick;
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
    assert.equal(await page.locator("#automation-library .automation-flow-stage").count(), 6);
    assert.equal(await page.locator("#automation-library").evaluate(element => element.classList.contains("is-compact")), true);
    assert.equal(await page.locator("#automation-library .automation-library-flow").first().getAttribute("open"), null);
    await page.locator("#automation-library .automation-library-flow summary").first().click();
    assert.equal(await page.locator("#automation-library .automation-library-flow").first().getAttribute("open"), "");
    assert.equal(await page.locator("#automation-library .automation-flow").first().isVisible(), true);
    assert.ok(await page.locator("#automation-library .automation-flow-entity-icon").count() > 0);
    assert.doesNotMatch(await page.locator("#automation-library .automation-flow").first().innerText(), /WATCH 1/i);
    assert.match(await page.locator("#automation-library .automation-flow").first().innerText(), /> 20/);
    assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("zbrano.automation-studio.library.v1"))), {filter: "all", sort: "active"});
    await page.locator('[data-auto-view="activity"]').click();
    await page.locator('[data-auto-panel="activity"]:not(.hidden)').waitFor();
    assert.equal(await page.locator("#automation-activity-watching").innerText(), "1");
    assert.equal(await page.locator("#automation-activity-attention").innerText(), "0");
    assert.equal(await page.locator("#automation-activity-matched").innerText(), "1");
    assert.equal(await page.locator("#automation-activity-actions").innerText(), "1");
    assert.match(await page.locator("#automation-decision-feed").innerText(), /Action completed/i);
    assert.match(await page.locator("#automation-decision-feed").innerText(), /Active lighting/i);
    await page.locator("#automation-activity-result-filter").selectOption("no_action");
    assert.match(await page.locator("#automation-decision-feed").innerText(), /Required person is not present/i);
    await page.locator("#automation-activity-automation-filter").selectOption("active-flow");
    assert.match(await page.locator("#automation-decision-feed").innerText(), /No evaluations match these filters yet/i);
    await page.locator("#automation-activity-result-filter").selectOption("all");
    assert.match(await page.locator("#automation-health-list").innerText(), /Active lighting/i);
    assert.match(await page.locator("#autonomy-timeline").innerText(), /Automation action sequence executed/i);
    assert.equal(await page.locator("#automation-recovery-paused").innerText(), "0 Paused");
    assert.match(await page.locator("#automation-recovery-list").innerText(), /1 of 3 failures/i);
    assert.match(await page.locator("#automation-recovery-list").innerText(), /2 more failures would pause/i);
    await page.locator("#automation-recovery-list details summary").click();
    assert.match(await page.locator("#automation-recovery-list").innerText(), /Home Assistant service timed out/i);
    assert.equal(await page.locator("#automation-results-evaluated").innerText(), "2");
    assert.equal(await page.locator("#automation-results-attention").innerText(), "1");
    assert.equal(await page.locator("#automation-results-learning").innerText(), "0");
    assert.equal(await page.locator("#automation-results-healthy").innerText(), "1");
    assert.match(await page.locator("#automation-results-list").innerText(), /25% accepted when answered/i);
    await page.locator("#automation-results-filter").selectOption("attention");
    assert.equal(await page.locator("#automation-results-list .automation-result-row").count(), 1);
    assert.match(await page.locator("#automation-results-list").innerText(), /Narrow its When or IF checks/i);
    await page.locator('[data-auto-view="permissions"]').click();
    await page.locator('[data-auto-panel="permissions"]:not(.hidden)').waitFor();
    assert.equal(await page.locator("#automation-permission-ready").innerText(), "2");
    assert.equal(await page.locator("#automation-permission-attention").innerText(), "0");
    assert.equal(await page.locator("#automation-permission-reads").innerText(), "3");
    assert.equal(await page.locator("#automation-permission-controls").innerText(), "1");
    assert.match(await page.locator("#automation-permission-list").innerText(), /Browser Fixture Light/i);
    assert.match(await page.locator("#automation-permission-list").innerText(), /Control allowed/i);
    await page.locator("#automation-permission-filter").selectOption("attention");
    assert.match(await page.locator("#automation-permission-list").innerText(), /No automations match this filter/i);
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
    assert.match(await page.locator("#automation-studio-state").innerText(), /When block added/i);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 2);
    assert.equal(await page.locator('#automation-flow-preview [data-trigger-logic]').count(), 1);
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').last().innerText(), /Choose a device or sensor/i);
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').last().click();
    const secondTriggerEntity=page.locator('[data-workflow-index="0"][data-trigger-field="entity_id"]');
    await page.waitForFunction(()=>document.activeElement?.matches('[data-workflow-index="0"][data-trigger-field="entity_id"]'));
    await secondTriggerEntity.locator('xpath=..').locator('.automation-entity-results .automation-entity-result').first().waitFor();
    await secondTriggerEntity.press("Escape");
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
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').first().click();
    const studioTriggerEntity = page.locator("#studio-automation-trigger-entity");
    await studioTriggerEntity.fill("Browser Fixture 1");
    const studioTriggerResult = page.locator("#automation-studio-inspector-fields .automation-entity-result").filter({hasText:"sensor.browser_fixture_1"}).first();
    await studioTriggerResult.waitFor();
    assert.match(await studioTriggerResult.locator(".automation-entity-reading").innerText(), /20\.1\s*°C/i);
    await studioTriggerResult.click();
    assert.equal(await page.locator("#automation-trigger-entity").inputValue(), "sensor.browser_fixture_1");
    await studioTriggerEntity.fill("sensor.primary_trigger");
    await studioTriggerEntity.press("Escape");
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(1).focus();
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(1).press("Enter");
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(1).evaluate(node=>node.classList.contains("is-selected")), true);
    await page.locator('[data-workflow-index="0"][data-trigger-field="entity_id"]').fill("sensor.middle_trigger");
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(2).focus();
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(2).press("Enter");
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(2).evaluate(node=>node.classList.contains("is-selected")), true);
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
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(1).innerText(), /Choose a device or sensor/i);
    await dropStudioBlock("context");
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="context"]').count(), 1);
    await dropStudioBlock("decision");
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="decision"]').count(), 0);
    assert.equal(await page.locator('#automation-flow-preview .automation-flow-node.is-decision').count(), 0);
    assert.deepEqual(await page.locator('#automation-flow-preview .automation-flow-branch-lane').evaluateAll(lanes=>lanes.map(lane=>lane.querySelector('[data-flow-kind="branch-condition"] .automation-flow-kicker')?.textContent)), ["IF", "ELSE IF"]);
    const timingDetails=page.locator(".automation-inspector-more").filter({hasText:"Fine-tune timing and confidence"});
    assert.match(await timingDetails.locator(":scope > summary").innerText(), /Fine-tune timing and confidence/i);
    assert.equal(await timingDetails.getAttribute("open"), null);
    await dropStudioBlock("action");
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="action"]').innerText(), /Choose what it should do/i);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="action"]').count(), 1);
    assert.match(await page.locator("#automation-studio-state").innerText(), /Then block added/i);
    assert.equal(await page.locator(".automation-task-palette [data-action-template]").count(), 9);
    assert.equal(await page.locator('[data-action-template="notification"]').isEnabled(), true);
    await page.locator('[data-action-template="turn_on"]').click();
    await page.locator('[data-workflow-index="1"][data-action-field="entity_id"]').fill("light.browser_fixture");
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="action"]').nth(1).innerText(), /Turn on/i);
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
    assert.match(await page.locator("#automation-studio-validation").innerText(), /When: choose a device or sensor/i);
    assert.equal(await page.locator('[data-studio-node="trigger"]').getAttribute("aria-label"), "WHEN · Events: Needs attention");
    assert.match(await page.locator('[data-studio-step-status="details"]').innerText(), /Ready/i);
    await page.locator("#automation-studio-test").click();
    assert.match(await page.locator("#automation-studio-state").innerText(), /before testing/i);
    await page.locator("#automation-studio-save").click();
    assert.match(await page.locator("#automation-studio-state").innerText(), /before saving/i);
    await page.locator('[data-validation-kind="trigger"]').first().click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "2. When");
    await page.locator("#studio-automation-trigger-entity").fill("sensor.browser_fixture_1");
    await page.locator("#studio-automation-trigger-value").fill("27");
    assert.equal(await page.locator("#automation-trigger-value").inputValue(), "27");
    assert.equal(await page.locator("#automation-studio-validation").isHidden(), true);
    assert.equal(await page.locator('[data-studio-node="trigger"]').getAttribute("aria-label"), "WHEN · Events: Ready");
    await page.locator("#automation-studio-step-next").click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "3. IF conditions");
    assert.equal(await page.locator("#automation-studio-current-step").innerText(), "Step 3 of 5");
    await page.locator("#automation-studio-step-back").click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "2. When");
    await page.waitForFunction(() => {
      try {
        const saved=JSON.parse(localStorage.getItem("zbrano.automation-studio.unsaved.v1")||"null");
        return saved?.state?.controls?.["automation-trigger-value"]==="27";
      } catch (_error) {
        return false;
      }
    });
    assert.equal(await page.locator("#automation-studio-undo").isEnabled(), true);
    await page.locator("#studio-automation-trigger-value").fill("28");
    await page.waitForFunction(() => {
      try {
        const saved=JSON.parse(localStorage.getItem("zbrano.automation-studio.unsaved.v1")||"null");
        return saved?.state?.controls?.["automation-trigger-value"]==="28";
      } catch (_error) {
        return false;
      }
    });
    await page.locator("#automation-studio-undo").click();
    assert.equal(await page.locator("#automation-trigger-value").inputValue(), "27");
    assert.equal(await page.locator("#automation-studio-redo").isEnabled(), true);
    await page.locator("#automation-studio-redo").click();
    assert.equal(await page.locator("#automation-trigger-value").inputValue(), "28");
    await page.locator("#studio-automation-trigger-value").fill("27");
    await page.waitForFunction(() => {
      try {
        const saved=JSON.parse(localStorage.getItem("zbrano.automation-studio.unsaved.v1")||"null");
        return saved?.state?.controls?.["automation-trigger-value"]==="27";
      } catch (_error) {
        return false;
      }
    });
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
    assert.equal(await page.locator('.automation-workflow-step').count(), 1);
    assert.equal(await page.locator('#studio-automation-trigger-entity').count(), 0);
    await page.locator('[data-trigger-preset="time"]').click();
    await page.locator('[data-workflow-index="0"][data-trigger-field="at"]').fill("18:30");
    await page.locator('[data-workflow-index="0"][data-trigger-field="weekdays"]').fill("Mon, Wed, Fri");
    assert.equal(await page.locator('[data-workflow-index="0"][data-trigger-field="at"]').inputValue(), "18:30");
    await page.locator('[data-trigger-preset="power_off"]').click();
    await page.locator('[data-workflow-index="0"][data-trigger-field="entity_id"]').fill("climate.browser_fixture");
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(1).click();
    assert.equal(await page.locator('[data-trigger-preset="power_off"]').getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator('[data-workflow-index="0"][data-trigger-field="operator"]').count(), 0);
    assert.equal(await page.locator('[data-workflow-index="0"][data-trigger-field="value"]').count(), 0);
    assert.match(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(1).innerText(), /POWER OFF|Turns off/i);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').count(), 2);
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').first().click();
    assert.equal(await page.locator('.automation-workflow-step').count(), 0);
    assert.equal(await page.locator('#studio-automation-trigger-entity').count(), 1);
    await page.locator('#automation-flow-preview [data-flow-kind="trigger"]').nth(1).click();
    assert.equal(await page.locator('.automation-workflow-step').count(), 1);
    assert.equal(await page.locator('#studio-automation-trigger-entity').count(), 0);
    assert.equal(await page.locator("#automation-flow-preview [data-trigger-logic]").inputValue(), "any");
    await page.locator("#automation-flow-preview [data-trigger-logic]").selectOption("all");
    assert.equal(await page.locator("[data-trigger-mode]").inputValue(), "all");
    await page.locator("#automation-flow-preview [data-trigger-logic]").selectOption("any");
    await page.locator('#automation-flow-preview [data-flow-kind="context"]').first().click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "3. IF conditions");
    await page.waitForTimeout(250);
    await page.evaluate(()=>{document.activeElement?.blur();window.zbranoEntitySearch.close()});
    await page.locator('[data-workflow-add="conditions"]').click();
    await page.locator('[data-workflow-index="0"][data-condition-field="entity_id"]').fill("sensor.browser_fixture_3");
    await page.locator("[data-workflow-mode]").selectOption("any");
    assert.match(await page.locator("#automation-flow-preview").innerText(), /Browser Fixture 3/i);
    await page.locator('#automation-flow-preview [data-flow-kind="action"]').click();
    await page.waitForTimeout(250);
    await page.evaluate(()=>{document.activeElement?.blur();window.zbranoEntitySearch.close()});
    await page.locator('[data-action-template="delay"]').click();
    assert.equal(await page.locator(".automation-workflow-step").count(), 1);
    await page.locator('[data-workflow-index="0"][data-action-field="delay_seconds"]').fill("2");
    assert.match(await page.locator("#automation-flow-preview").innerText(), /Wait 2 sec/i);
    await page.locator('[data-studio-node="details"]').click();
    assert.equal(await page.locator("#automation-studio-inspector-title").innerText(), "1. Setup & safety");
    assert.equal(await page.locator('.automation-rule-safety-guide').count(), 0);
    assert.equal(await page.locator('[data-auto-view="safety"]').isHidden(), true);
    assert.equal(await page.locator("#studio-automation-execution-policy").count(), 0);
    assert.equal(await page.locator("#studio-automation-sleep-hours-start").count(), 0);
    await page.locator("#studio-automation-sleep-hours-enabled").check();
    assert.equal(await page.locator("#studio-automation-sleep-hours-start").inputValue(), "22:00");
    assert.equal(await page.locator("#studio-automation-sleep-hours-end").inputValue(), "07:00");
    await page.locator("#studio-automation-run-during-sleep-hours").check();
    assert.equal(await page.locator("#automation-run-during-sleep-hours").isChecked(), true);
    await page.locator("#studio-automation-risk").selectOption("controlled");
    assert.equal(await page.locator("#automation-risk").inputValue(), "controlled");
    await page.locator("#studio-automation-max-actions").fill("3");
    assert.equal(await page.locator("#automation-max-actions").inputValue(), "3");
    await page.locator('.automation-studio-toolbox [data-studio-node="decision"]').click();
    assert.equal(await page.locator("#studio-automation-proposal").count(), 1);
    await page.locator("#automation-studio-test").click();
    await page.locator("#automation-studio-test-results:not([hidden])").waitFor();
    assert.equal(await page.locator("#automation-studio-test-results .automation-studio-test-step").count(), 4);
    assert.match(await page.locator("#automation-studio-state").innerText(), /0 actions executed/i);
    await page.locator('[data-studio-node="details"]').click();
    await page.locator("#studio-automation-risk").selectOption("informational");
    assert.equal(await page.locator("#studio-automation-execution-policy").count(), 0);
    assert.equal(await page.locator("#studio-automation-max-actions").count(), 0);
    assert.equal(await page.locator("#studio-automation-reversible-only").count(), 0);
    assert.equal(await page.locator("#studio-automation-notify-action").count(), 0);
    await page.locator('.automation-studio-toolbox [data-studio-node="decision"]').click();
    await page.locator("[data-branch-add]").click();
    assert.equal(await page.locator("#automation-flow-preview .automation-flow-branch-lane").count(), 2);
    assert.equal(await page.locator('#automation-flow-preview .automation-flow-node.is-decision').count(), 0);
    assert.deepEqual(await page.locator('#automation-flow-preview .automation-flow-branch-lane').evaluateAll(lanes=>lanes.map(lane=>lane.querySelector('[data-flow-kind="branch-condition"] .automation-flow-kicker')?.textContent)), ["IF", "ELSE IF"]);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="action"]').count(), 0);
    assert.match(await page.locator('[data-flow-branch-drop="0"]').innerText(), /Browser Fixture 3/i);
    assert.match(await page.locator('[data-flow-branch-drop="0"]').innerText(), /Wait 2 sec/i);
    assert.match(await page.locator('[data-flow-branch-drop="0"] [data-flow-kind="branch-message"]').innerText(), /room is becoming uncomfortable/i);
    assert.equal(await page.locator('[data-flow-branch-drop="1"] [data-flow-kind="branch-message"]').count(), 0);
    assert.equal(await page.locator('[data-flow-branch-drop="1"] [data-flow-branch-task-template="message"]').count(), 1);
    assert.equal(await page.locator("[data-branch-suggestion]").count(), 0);
    const messageMenu=page.locator('[data-flow-branch-drop="1"] .automation-flow-branch-task-menu');
    await messageMenu.locator('summary').click();
    await messageMenu.locator('[data-flow-branch-task-template="message"]').click();
    assert.equal(await page.locator('[data-flow-branch-drop="1"] [data-flow-kind="branch-message"]').count(), 1);
    assert.equal(await page.locator('[data-branch-delivery]').count(), 3);
    assert.doesNotMatch(await page.locator('#automation-studio-inspector-fields').innerText(), /This path runs when/i);
    await page.locator('[data-branch-delivery="delivery_voice"]').uncheck();
    await page.locator('[data-flow-branch-drop="0"] [data-flow-kind="branch-message"]').click();
    assert.equal(await page.locator('[data-branch-delivery="delivery_voice"]').isChecked(), true);
    await page.locator('[data-flow-branch-drop="1"] [data-flow-kind="branch-condition"]').click();
    const elseIfEntity=page.locator('[data-branch-collection="conditions"][data-branch-index="1"][data-item-index="0"][data-condition-field="entity_id"]'),elseIfAttribute=page.locator('[data-branch-collection="conditions"][data-branch-index="1"][data-item-index="0"][data-condition-field="attribute"]');
    await elseIfEntity.fill("Browser Thermostat");
    const thermostatResult=page.locator("#automation-studio-inspector-fields .automation-entity-result").filter({hasText:"climate.browser_thermostat"}).first();
    await thermostatResult.waitFor();
    assert.match(await thermostatResult.locator(".automation-entity-reading").innerText(), /26\.2\s*°C/i);
    await thermostatResult.click();
    const elseIfAdvanced=elseIfAttribute.locator("xpath=ancestor::details[1]");
    assert.doesNotMatch(await elseIfAdvanced.innerText(), /Which value\?/i);
    assert.equal(await elseIfAdvanced.getAttribute("open"), null);
    assert.equal(await elseIfAttribute.isVisible(), false);
    await page.locator('[data-branch-collection="conditions"][data-branch-index="1"][data-item-index="0"][data-condition-field="value"]').fill("on");
    await page.locator('[data-branch-collection="conditions"][data-branch-index="1"][data-item-index="0"][data-condition-field="for_seconds"]').fill("1200");
    await page.locator('[data-flow-branch-drop="1"] [data-flow-kind="branch-message"]').click();
    await page.locator('[data-branch-suggestion="1"]').fill("Check whether a window is open.");
    const taskMenu=page.locator('[data-flow-branch-drop="1"] .automation-flow-branch-task-menu');
    await taskMenu.locator('summary').click();
    const taskSummaryBox=await taskMenu.locator('summary').boundingBox(),taskChoicesBox=await taskMenu.locator('.automation-flow-branch-task-choices').boundingBox();
    assert.ok(taskSummaryBox&&taskChoicesBox&&taskChoicesBox.y<taskSummaryBox.y);
    assert.ok(taskChoicesBox.y+taskChoicesBox.height<=page.viewportSize().height);
    await taskMenu.locator('[data-flow-branch-task-template="turn_off"]').click();
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"].has-validation-error').count(), 1);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"].has-validation-error').count(), 0);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-message"].has-validation-error').count(), 0);
    const branchActionEntity=page.locator('[data-branch-collection="actions"][data-branch-index="1"][data-item-index="0"][data-action-field="entity_id"]');
    await branchActionEntity.fill("Browser Fixture Li");
    assert.match(await page.locator('[data-flow-branch-drop="1"] [data-flow-kind="branch-action"]').innerText(), /Choose a device/i);
    await page.locator('#automation-studio-inspector-fields .automation-entity-result').filter({hasText:"Browser Fixture Light"}).click();
    assert.equal(await branchActionEntity.inputValue(), "light.browser_fixture");
    assert.match(await page.locator('[data-flow-branch-drop="1"] [data-flow-kind="branch-action"]').innerText(), /Browser Fixture Light/i);
    assert.equal(await page.locator('#automation-flow-preview [data-flow-kind="branch-action"].has-validation-error').count(), 0);
    assert.match(await page.locator('[data-flow-branch-drop="1"]').innerText(), /ELSE IF/i);
    assert.match(await page.locator('[data-flow-branch-drop="1"]').innerText(), /20 min|1200 sec/i);
    assert.match(await page.locator('[data-flow-branch-drop="1"]').innerText(), /Check whether a window is open/i);
    assert.match(await page.locator('[data-flow-branch-drop="1"]').innerText(), /Turn off/i);
    await page.locator('#automation-flow-preview [data-flow-kind="branch-condition"][data-flow-branch-index="1"]').click();
    assert.equal(await page.locator('[data-branch-collection="conditions"][data-branch-index="1"]').count(), 6);
    assert.equal(await page.locator('[data-branch-suggestion]').count(), 0);
    assert.equal(await page.locator('[data-branch-collection="actions"]').count(), 0);
    await page.locator('#automation-flow-preview [data-flow-kind="branch-action"][data-flow-branch-index="1"]').click();
    assert.equal(await page.locator('[data-branch-collection="actions"][data-branch-index="1"]').count(), 2);
    assert.equal(await page.locator('[data-branch-collection="conditions"]').count(), 0);
    assert.equal(await page.locator('[data-branch-policy][data-branch-index="1"]').inputValue(), "approval_required");
    await page.locator('[data-branch-policy][data-branch-index="1"]').selectOption("autonomous");
    assert.match(await page.locator('[data-flow-branch-drop="1"] .automation-flow-branch-section-label').last().innerText(), /RUN AUTOMATICALLY/i);
    await page.locator('#automation-flow-preview [data-flow-kind="branch-action"][data-flow-branch-index="0"]').click();
    assert.equal(await page.locator('[data-branch-policy][data-branch-index="0"]').inputValue(), "approval_required");
    assert.match(await page.locator("#automation-studio-state").innerText(), /Power off task added/i);
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
    await page.locator('#settings-panel:not(.hidden) [data-notification-workspace]').waitFor();
    assert.equal(await page.locator('#automations-panel [data-notification-workspace]').count(), 0);
    await page.locator('[data-notification-view="center"]').click();
    await page.locator('.notification-channel[data-availability="ready"]').waitFor();
    assert.match(await page.locator('.notification-channel[data-availability="ready"]').innerText(), /Ready · status not reported/);
    assert.match(await page.locator('.notification-channel[data-availability="unavailable"]').innerText(), /Unavailable/);
    await page.locator('#telegram-setup-status[data-status="attention"]').waitFor();
    assert.equal(await page.locator('#telegram-setup-status').innerText(), 'Not connected');
    assert.equal(await page.locator('#telegram-setup-guide a[href="https://t.me/BotFather"]').count(), 1);
    assert.equal(await page.locator('#telegram-setup-guide a[href*="domain=telegram_bot"]').count(), 1);
    await page.setViewportSize({width:1440,height:900});
    const notificationDesktopLayout = await page.locator('[data-notification-workspace]').evaluate(element => {
      const cards = [...element.querySelectorAll('.notification-center-grid > .autonomy-card')];
      const channels = element.querySelector('.notification-channel-card').getBoundingClientRect();
      const policy = element.querySelector('.notification-policy-card').getBoundingClientRect();
      return {
        stylesheet: [...document.styleSheets].some(sheet => String(sheet.href || '').endsWith('/css/notification-center.css')),
        pairedFirstRow: Math.abs(channels.top - policy.top) <= 1,
        contained: cards.every(card => card.scrollWidth <= card.clientWidth + 1),
        noHorizontalOverflow: element.scrollWidth <= element.clientWidth + 1,
      };
    });
    assert.equal(notificationDesktopLayout.stylesheet, true);
    assert.equal(notificationDesktopLayout.pairedFirstRow, true);
    assert.equal(notificationDesktopLayout.contained, true);
    assert.equal(notificationDesktopLayout.noHorizontalOverflow, true);
    await page.setViewportSize({width:700,height:720});
    const notificationMobileLayout = await page.locator('[data-notification-workspace]').evaluate(element => ({
      compactHeader: getComputedStyle(element.querySelector('.notification-workspace-head')).display === 'grid',
      noHorizontalOverflow: element.scrollWidth <= element.clientWidth + 1,
    }));
    assert.equal(notificationMobileLayout.compactHeader, true);
    assert.equal(notificationMobileLayout.noHorizontalOverflow, true);
    await page.setViewportSize({width:1100,height:720});

    await page.locator("#calendar-tab").click();
    await page.locator("#calendar-panel:not(.hidden)").waitFor();
    await page.locator('[data-calendar-view="upcoming"]').click();
    const calendarTitle = page.locator("#calendar-title");
    await calendarTitle.focus();
    assert.equal(await calendarTitle.getAttribute("placeholder"), "");
    await calendarTitle.blur();
    assert.equal(await calendarTitle.getAttribute("placeholder"), "Dentist");
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
    const textSizeBefore = await page.locator('#text-size').inputValue();
    await page.locator('#settings-find').fill('TEXT SIZE');
    assert.equal(await page.locator('#settings-find-results button').count(), 1);
    assert.match(await page.locator('#settings-find-results').innerText(), /Appearance/);
    if(process.env.ZBRANO_DEVICE_SCREENSHOT)await page.screenshot({animations:'disabled',path:process.env.ZBRANO_DEVICE_SCREENSHOT.replace('.png','-settings-search.png')});
    await page.locator('#settings-find').press('ArrowDown');
    await page.keyboard.press('Enter');
    await page.waitForFunction(()=>document.activeElement?.id==='text-size');
    assert.equal(await page.locator('[data-settings-category="appearance"]').isVisible(), true);
    assert.equal(await page.locator('#text-size').inputValue(), textSizeBefore);
    await page.locator('#settings-find').fill('no-setting-matches-this');
    assert.equal(await page.locator('#settings-find-empty').isVisible(), true);
    await page.locator('#settings-find').press('Escape');
    assert.equal(await page.locator('#settings-find-empty').isVisible(), false);
    const settingsLayout = await page.locator("#settings-panel .settings-stack").evaluate(element => ({
      display: getComputedStyle(element).display,
      columns: getComputedStyle(element).gridTemplateColumns,
      cursor: getComputedStyle(document.querySelector("#settings-tab")).cursor,
    }));
    assert.equal(settingsLayout.display, "grid");
    assert.match(settingsLayout.columns, /px .*px/);
    assert.equal(settingsLayout.cursor, "pointer");
    await page.locator('[data-settings-target="setup"]').click();
    await page.locator('.onboarding-step.is-active').waitFor();
    assert.equal(await page.locator('.onboarding-rail-step').count(), 7);
    assert.match(await page.locator('.onboarding-step-rail').innerText(), /Device access/i);
    assert.equal(await page.locator('.onboarding-step:visible').count(), 1);
    assert.match(await page.locator('.onboarding-step.is-active').innerText(), /CORE CONNECTION/);
    assert.match(await page.locator('.onboarding-step.is-active .onboarding-focus-guidance').innerText(), /only the entities you approve/i);
    assert.equal(await page.locator('.onboarding-rail-step').nth(1).isDisabled(), true);
    assert.equal(await page.locator('#onboarding-next').isDisabled(), true);
    assert.equal(await page.locator('#onboarding-recheck').innerText(), "Refresh status");
    await page.locator('.onboarding-step').first().locator('.onboarding-step-actions button').nth(1).click();
    await page.locator('#onboarding-configuration-help:not([hidden])').waitFor();
    assert.match(await page.locator('#onboarding-configuration-help').innerText(), /connects to Home Assistant automatically/i);
    assert.match(await page.locator('#onboarding-configuration-help').innerText(), /do not need to enter an address or access token/i);
    assert.match(await page.locator('#onboarding-configuration-help').innerText(), /ZBRANO Log tab/i);
    assert.equal(await page.locator('#onboarding-configuration-copy').isHidden(), true);
    assert.equal(await page.locator('#onboarding-configuration-verify').innerText(), "Check connection again");
    await page.locator('#onboarding-configuration-close').click();
    await page.locator('.onboarding-step').nth(1).locator('.onboarding-step-actions button').nth(1).evaluate(element => element.click());
    await page.locator('#onboarding-configuration-help:not([hidden])').waitFor();
    assert.match(await page.locator('#onboarding-configuration-help').innerText(), /Settings → Apps → ZBRANO → Configuration/i);
    assert.match(await page.locator('#onboarding-configuration-help').innerText(), /chat_provider/i);
    assert.match(await page.locator('#onboarding-configuration-help').innerText(), /openrouter_api_key/i);
    assert.match(await page.locator('#onboarding-configuration-help').innerText(), /restart the ZBRANO app/i);
    assert.match(await page.locator('#onboarding-configuration-help').innerText(), /Optional fields can stay blank/i);
    await page.locator('#onboarding-configuration-close').click();
    assert.equal(await page.locator('#onboarding-configuration-help').isHidden(), true);
    await page.locator('#onboarding-complete').evaluate(element => {
      element.disabled = false;
      element.click();
    });
    await page.locator('.onboarding-complete-card').waitFor();
    assert.match(await page.locator('.onboarding-complete-card').innerText(), /ZBRANO is ready/);
    assert.match(await page.locator('.onboarding-capability-list').innerText(), /AI model ready/);
    assert.match(await page.locator('.onboarding-capability-list').innerText(), /Voice and wake word available later/);
    assert.match(await page.locator('.onboarding-installation-report summary').innerText(), /Installation report · Ready/i);
    await page.locator('.onboarding-installation-report summary').click();
    assert.match(await page.locator('.onboarding-report-checks').innerText(), /Persistent storage/i);
    assert.match(await page.locator('.onboarding-installation-report').innerText(), /excludes keys, tokens, entity IDs, messages, and personal data/i);
    assert.equal(await page.getByRole('button', {name:'Download report'}).count(), 1);
    await page.getByRole('button', {name:'Review connections'}).click();
    await page.locator('.onboarding-step.is-active').waitFor();
    await page.locator('#memory-tab').click();
    await page.locator('#memory-database-view:visible').waitFor();
    await page.getByText('Household', {exact:true}).waitFor();
    assert.match(await page.locator('#memory-panel').innerText(), /stays on this ZBRANO installation/i);
    assert.equal(await page.locator('#memory-space-count').innerText(), '1');
    assert.equal(await page.locator('#memory-note-count').innerText(), '3');
    assert.equal(await page.locator('[data-memory-view="templates"]').count(), 1);
    assert.equal(await page.locator('#memory-new-space').count(), 1);
    assert.equal(await page.locator('#memory-new-template').count(), 1);
    assert.match(await page.locator('#memory-panel').innerText(), /What should ZBRANO remember\?/i);
    await page.locator('#memory-quick-content').fill('The living-room air conditioner filter is 40 x 60 cm.');
    await page.locator('#memory-quick-save').click();
    await page.locator('#memory-quick-result:not([hidden])').waitFor();
    assert.match(await page.locator('#memory-quick-result').innerText(), /Saved and organized/i);
    assert.match(await page.locator('#memory-quick-result').innerText(), /Household.*Appliances/is);
    await page.setViewportSize({width: 1100, height: 480});
    await page.locator('#memory-new-space').click();
    const databaseScroll = await page.locator('.memory-studio-main').evaluate(element => {
      element.scrollTop = element.scrollHeight;
      const panel = document.getElementById('memory-panel');
      return {
        overflowY: getComputedStyle(element).overflowY,
        fitsPanel: Math.abs(element.clientHeight - panel.clientHeight) <= 2,
        scrollable: element.scrollHeight > element.clientHeight,
        moved: element.scrollTop > 0,
      };
    });
    assert.equal(databaseScroll.overflowY, 'auto');
    assert.equal(databaseScroll.fitsPanel, true, 'Memory content must fit its panel instead of inheriting the page-sized main layout');
    assert.equal(databaseScroll.scrollable, true, 'Memory Database must overflow at compact viewport heights');
    assert.equal(databaseScroll.moved, true, 'Memory Database must accept vertical scrolling');
    await page.locator('.memory-studio-main').evaluate(element => { element.scrollTop = 0; });
    await page.locator('[data-memory-view="templates"]').click();
    await page.locator('#memory-new-template').click();
    await page.locator('#memory-add-blueprint').click();
    await page.locator('#memory-add-blueprint').click();
    const templateScroll = await page.locator('.memory-studio-main').evaluate(element => {
      element.scrollTop = element.scrollHeight;
      return {
        scrollable: element.scrollHeight > element.clientHeight,
        moved: element.scrollTop > 0,
      };
    });
    assert.equal(templateScroll.scrollable, true, 'Template Studio must overflow at compact viewport heights');
    assert.equal(templateScroll.moved, true, 'Template Studio must accept vertical scrolling');
    await page.setViewportSize({width: 700, height: 480});
    const compactMemoryScroll = await page.locator('#memory-panel').evaluate(element => {
      element.scrollTop = element.scrollHeight;
      return {
        overflowY: getComputedStyle(element).overflowY,
        scrollable: element.scrollHeight > element.clientHeight,
        moved: element.scrollTop > 0,
      };
    });
    assert.equal(compactMemoryScroll.overflowY, 'auto');
    assert.equal(compactMemoryScroll.scrollable, true, 'Compact Memory Studio must overflow within the panel');
    assert.equal(compactMemoryScroll.moved, true, 'Compact Memory Studio must accept vertical scrolling');
    await page.setViewportSize({width: 1100, height: 720});
    await page.locator('#settings-tab').click();
    await page.locator('[data-settings-target="memory"]').click();
    await page.locator('[data-settings-category="memory"]:visible').waitFor();
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

    console.log("Browser smoke passed: New Chat, About showcase, navigation, Entity scrolling, notification inbox, Calendar birthdays, guided onboarding, built-in Knowledge Memory, modern Settings, Automation Library filtering, Studio safety, validation, recovery, and branching workflows");
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
