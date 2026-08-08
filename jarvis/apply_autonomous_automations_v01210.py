from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.10 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    model_marker = "class SettingsRestoreRequest(BaseModel):\n"
    require(text, model_marker, "automation request models")
    models = r'''class AutonomySettingsRequest(BaseModel):
    operating_mode: str = Field(default="suggest_only", pattern="^(observe_only|suggest_only|approval_gated|selective_autonomy)$")
    presence_entity: str = Field(default="", max_length=255)
    require_presence: bool = True
    respect_quiet_hours: bool = True
    minimum_confidence: float = Field(default=0.75, ge=0.5, le=0.99)
    default_cooldown_minutes: int = Field(default=30, ge=1, le=1440)
    autonomous_risk_ceiling: str = Field(default="low", pattern="^(informational|low|controlled)$")
    notify_after_autonomous_action: bool = True


class AutonomousAutomationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    objective: str = Field(min_length=3, max_length=1000)
    presence_entity: str = Field(default="", max_length=255)
    signal_entities: list[str] = Field(default_factory=list, max_length=20)
    context_notes: str = Field(default="", max_length=3000)
    proposal_template: str = Field(default="", max_length=1000)
    action_entity: str = Field(default="", max_length=255)
    action_service: str = Field(default="", max_length=120)
    cooldown_minutes: int = Field(default=30, ge=1, le=1440)
    confidence_threshold: float = Field(default=0.75, ge=0.5, le=0.99)
    risk_level: str = Field(default="controlled", pattern="^(informational|low|controlled|high)$")
    execution_policy: str = Field(default="suggest", pattern="^(observe|suggest|approval_required|autonomous)$")
    notify_on_action: bool = True
    reversible_only: bool = True
    max_actions_per_hour: int = Field(default=2, ge=1, le=60)


'''
    text = text.replace(model_marker, models + model_marker, 1)

    api_marker = '@app.get("/api/settings")\n'
    require(text, api_marker, "automation API insertion point")
    backend = r'''AUTOMATION_STORAGE_PATH = Path("/data/autonomous_automations.json")
AUTOMATION_DEFAULT_SETTINGS = {
    "operating_mode": "suggest_only",
    "presence_entity": "",
    "require_presence": True,
    "respect_quiet_hours": True,
    "minimum_confidence": 0.75,
    "default_cooldown_minutes": 30,
    "autonomous_risk_ceiling": "low",
    "notify_after_autonomous_action": True,
}


def _automation_empty_store():
    return {
        "settings": dict(AUTOMATION_DEFAULT_SETTINGS),
        "automations": [],
        "suggestions": [],
        "timeline": [],
    }


def automation_store():
    data = _plugin_load(AUTOMATION_STORAGE_PATH)
    if not data:
        return _automation_empty_store()
    settings = dict(AUTOMATION_DEFAULT_SETTINGS)
    if isinstance(data.get("settings"), dict):
        settings.update(data["settings"])
    return {
        "settings": settings,
        "automations": data.get("automations") if isinstance(data.get("automations"), list) else [],
        "suggestions": data.get("suggestions") if isinstance(data.get("suggestions"), list) else [],
        "timeline": data.get("timeline") if isinstance(data.get("timeline"), list) else [],
    }


def _automation_save(data):
    data["automations"] = list(data.get("automations") or [])[:100]
    data["suggestions"] = list(data.get("suggestions") or [])[:100]
    data["timeline"] = list(data.get("timeline") or [])[:200]
    _plugin_save(AUTOMATION_STORAGE_PATH, data)


def _automation_event(data, event_type, title, detail=""):
    import secrets

    data.setdefault("timeline", []).insert(0, {
        "id": secrets.token_hex(8), "type": str(event_type)[:40],
        "title": str(title)[:160], "detail": str(detail)[:500],
        "created_at": time.time(),
    })


def _automation_payload(request):
    payload = request.model_dump()
    payload["name"] = " ".join(payload["name"].split())
    payload["objective"] = payload["objective"].strip()
    payload["presence_entity"] = payload["presence_entity"].strip()
    payload["signal_entities"] = list(dict.fromkeys(
        str(value).strip()[:255] for value in payload["signal_entities"] if str(value).strip()
    ))[:20]
    payload["context_notes"] = payload["context_notes"].strip()
    payload["proposal_template"] = payload["proposal_template"].strip()
    payload["action_entity"] = payload["action_entity"].strip()
    payload["action_service"] = payload["action_service"].strip()
    return payload


@app.get("/api/automations")
async def read_autonomous_automations():
    data = automation_store()
    return {
        **data,
        "engine": {
            "status": "foundation_ready",
            "continuous_monitoring": False,
            "context_reasoning": False,
            "automatic_execution": False,
            "message": "Automation workspace ready; continuous evaluator is not implemented yet.",
        },
    }


@app.put("/api/automations/settings")
async def update_autonomy_settings(request: AutonomySettingsRequest):
    data = automation_store()
    settings = request.model_dump()
    settings["presence_entity"] = settings["presence_entity"].strip()
    data["settings"] = settings
    _automation_event(
        data, "policy", "Autonomy policy updated",
        f"Mode: {settings['operating_mode']}; execution engine remains inactive in this version.",
    )
    _automation_save(data)
    return {"saved": True, "settings": settings}


@app.post("/api/automations")
async def create_autonomous_automation(request: AutonomousAutomationRequest):
    import secrets

    data = automation_store()
    if len(data["automations"]) >= 100:
        raise HTTPException(status_code=400, detail="Automation draft limit reached (100)")
    now = time.time()
    automation = {
        "id": secrets.token_hex(12), "status": "draft",
        "created_at": now, "updated_at": now,
        **_automation_payload(request),
    }
    data["automations"].insert(0, automation)
    _automation_event(data, "draft", f"Draft created: {automation['name']}", automation["objective"])
    _automation_save(data)
    return {"created": True, "automation": automation}


@app.put("/api/automations/{automation_id}")
async def update_autonomous_automation(automation_id: str, request: AutonomousAutomationRequest):
    data = automation_store()
    automation = next((item for item in data["automations"] if item.get("id") == automation_id), None)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation draft not found")
    automation.update(_automation_payload(request))
    automation["updated_at"] = time.time()
    automation["status"] = "draft"
    _automation_event(data, "draft", f"Draft updated: {automation['name']}")
    _automation_save(data)
    return {"saved": True, "automation": automation}


@app.delete("/api/automations/{automation_id}")
async def delete_autonomous_automation(automation_id: str):
    data = automation_store()
    automation = next((item for item in data["automations"] if item.get("id") == automation_id), None)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation draft not found")
    data["automations"] = [item for item in data["automations"] if item.get("id") != automation_id]
    _automation_event(data, "draft", f"Draft deleted: {automation.get('name') or automation_id}")
    _automation_save(data)
    return {"removed": True}


'''
    text = text.replace(api_marker, backend + api_marker, 1)

    general_diagnostics = "        catalog_attempts = []\n"
    require(text, general_diagnostics, "automation general diagnostics")
    text = text.replace(
        general_diagnostics,
        '''        await probe(
            "Autonomous Automations API operational",
            "/api/automations",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("automations"), list) else "failed",
                f"{len(payload.get('automations', [])) if isinstance(payload, dict) else 0} automation drafts; evaluator intentionally inactive",
            ),
            "automations",
        )

''' + general_diagnostics,
        1,
    )

    surface_marker = '''            "Entities frontend wired": ('id="entities-tab"', 'id="entities-panel"', "loadEntities"),'''
    require(text, surface_marker, "automation frontend diagnostics")
    text = text.replace(
        surface_marker,
        '''            "Automations frontend wired": ('id="automations-tab"', 'id="automations-panel"', 'zbrano-v01210-autonomous-automations'),
''' + surface_marker,
        1,
    )

    spec_marker = '''    "entities": {
        "title": "Home Assistant entities",'''
    require(text, spec_marker, "automation feature specification")
    automation_spec = '''    "automations": {
        "title": "Autonomous Automations",
        "aliases": ("automation", "automations", "autonomy", "suggestion", "proactive", "sensor monitoring"),
        "terms": ("automation", "home assistant", "frontend source", "persistent storage", "application health"),
        "layers": ("frontend", "api", "persistence", "entity context", "safety policy"),
        "files": (
            "jarvis/apply_autonomous_automations_v01210.py",
            "jarvis/app/main.py",
            "jarvis/app/static/index.html",
        ),
    },
'''
    text = text.replace(spec_marker, automation_spec + spec_marker, 1)

    route_marker = '''        "plugins": ("/api/plugins",),
        "entities": ("/api/ha/entities",),'''
    require(text, route_marker, "automation targeted routes")
    text = text.replace(
        route_marker,
        '''        "plugins": ("/api/plugins",),
        "automations": ("/api/automations",),
        "entities": ("/api/ha/entities",),''',
        1,
    )

    targeted_marker = '''    elif feature_key == "entities":
        await probe("Entity inventory operational", list_ha_entities, lambda p: (isinstance(p.get("entities"), list), f"{len(p.get('entities', []))} entities returned"), "home_assistant")'''
    require(text, targeted_marker, "automation targeted diagnostics")
    text = text.replace(
        targeted_marker,
        '''    elif feature_key == "automations":
        await probe("Autonomous Automations API operational", read_autonomous_automations, lambda p: (isinstance(p.get("automations"), list) and p.get("engine", {}).get("status") == "foundation_ready", f"{len(p.get('automations', []))} drafts; evaluator inactive by design"), "automations")
''' + targeted_marker,
        1,
    )

    backup_policy = '''        "entity_policy": json.loads(ENTITY_POLICY_PATH.read_text(encoding="utf-8"))
        if ENTITY_POLICY_PATH.exists() else {"version": 1, "entities": {}},
    }'''
    require(text, backup_policy, "automation backup export")
    text = text.replace(
        backup_policy,
        '''        "entity_policy": json.loads(ENTITY_POLICY_PATH.read_text(encoding="utf-8"))
        if ENTITY_POLICY_PATH.exists() else {"version": 1, "entities": {}},
        "automations": automation_store(),
    }''',
        1,
    )

    restore_policy = '''    policy = backup.get("entity_policy")
    if not isinstance(settings, dict) or not isinstance(chats, dict) or not isinstance(policy, dict):'''
    require(text, restore_policy, "automation backup restore input")
    text = text.replace(
        restore_policy,
        '''    policy = backup.get("entity_policy")
    automations = backup.get("automations")
    if not isinstance(settings, dict) or not isinstance(chats, dict) or not isinstance(policy, dict):''',
        1,
    )
    restore_validation = '''    if not isinstance(chats.get("sessions", {}), dict) or not isinstance(policy.get("entities", {}), dict):
        raise HTTPException(status_code=400, detail="Backup data is malformed")'''
    require(text, restore_validation, "automation backup validation")
    text = text.replace(
        restore_validation,
        restore_validation + '''
    if automations is not None and (
        not isinstance(automations, dict)
        or not isinstance(automations.get("settings"), dict)
        or not isinstance(automations.get("automations"), list)
        or not isinstance(automations.get("suggestions", []), list)
        or not isinstance(automations.get("timeline", []), list)
    ):
        raise HTTPException(status_code=400, detail="Automation backup data is malformed")''',
        1,
    )
    restore_save = '''    save_entity_policy(policy.get("entities", {}))
    load_chat_sessions()
    return {"restored": True, "chat_count": len(CHAT_SESSIONS)}'''
    require(text, restore_save, "automation backup persistence")
    text = text.replace(
        restore_save,
        '''    save_entity_policy(policy.get("entities", {}))
    if automations is not None:
        _automation_save(automations)
    load_chat_sessions()
    return {"restored": True, "chat_count": len(CHAT_SESSIONS), "automation_count": len(automation_store()["automations"])}''',
        1,
    )

    text = text.replace('version="0.12.9"', 'version="0.12.10"')
    text = text.replace('"version": "0.12.9"', '"version": "0.12.10"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    nav_marker = '    <button id="chat-tab" class="active">Chat</button>\n'
    require(text, nav_marker, "Automations navigation tab")
    text = text.replace(
        nav_marker,
        nav_marker + '    <button id="automations-tab">Automations</button>\n',
        1,
    )

    old_oauth_note = "OAuth-only connectors are listed with setup guidance and cannot be installed until ZBRANO supports their authorization flow."
    require(text, old_oauth_note, "current plugin OAuth catalog guidance")
    text = text.replace(
        old_oauth_note,
        "Compatible providers offer Connect and browser authorization; providers requiring owner-created OAuth credentials show setup guidance.",
        1,
    )

    main_close = "\n</main>"
    require(text, main_close, "Automations panel insertion point")
    panel = r'''
  <section id="automations-panel" class="panel hidden">
    <div class="autonomy-shell">
      <div class="autonomy-header">
        <div><h2>AUTONOMOUS AUTOMATIONS</h2><p>Design how ZBRANO should observe workshop context, reason about conditions, and propose useful actions.</p></div>
        <span class="autonomy-engine-badge">FOUNDATION READY · EVALUATOR INACTIVE</span>
      </div>
      <div class="autonomy-boundary"><strong>Current capability:</strong> Continuous monitoring and action execution are not active in this version. Drafts may define observe-only, suggest-only, approval-required, or fully autonomous future behavior.</div>
      <div class="autonomy-tabs" role="tablist" aria-label="Automation workspace views">
        <button class="active" type="button" data-auto-view="overview" role="tab" aria-selected="true">Overview</button>
        <button type="button" data-auto-view="library" role="tab" aria-selected="false">Automation Library</button>
        <button type="button" data-auto-view="safety" role="tab" aria-selected="false">Safety &amp; Authority</button>
        <button type="button" data-auto-view="activity" role="tab" aria-selected="false">Activity</button>
      </div>

      <section class="autonomy-view" data-auto-panel="overview">
        <div class="autonomy-metrics">
          <article><span>Engine</span><strong id="autonomy-engine-status">Foundation ready</strong><small>Continuous evaluator not active</small></article>
          <article><span>Operating policy</span><strong id="autonomy-mode-summary">Suggest only</strong><small id="autonomy-mode-detail">Per-automation authority supported</small></article>
          <article><span>Automation drafts</span><strong id="autonomy-draft-count">0</strong><small>Prepared observation plans</small></article>
          <article><span>Pending suggestions</span><strong id="autonomy-suggestion-count">0</strong><small>No synthetic suggestions</small></article>
        </div>
        <div class="autonomy-overview-grid">
          <article class="autonomy-card">
            <div class="autonomy-card-head"><div><h3>Suggestion Inbox</h3><p>Future proactive recommendations will include evidence, confidence, proposed action, and safety impact.</p></div></div>
            <div id="autonomy-suggestions" class="autonomy-list"><div class="autonomy-empty">No suggestions yet. ZBRANO will never invent activity before the evaluator is implemented.</div></div>
          </article>
          <article class="autonomy-card">
            <div class="autonomy-card-head"><div><h3>Workshop Context Snapshot</h3><p>Current Home Assistant states referenced by your drafts. This is a manual snapshot, not continuous monitoring.</p></div><button id="autonomy-refresh-context" type="button">Refresh</button></div>
            <div id="autonomy-context" class="autonomy-list"><div class="autonomy-empty">Open this tab to load Home Assistant entity context.</div></div>
          </article>
        </div>
      </section>

      <section class="autonomy-view hidden" data-auto-panel="library">
        <div class="autonomy-library-grid">
          <article class="autonomy-card">
            <h3>Quick-start designs</h3><p>Templates prefill a draft; they do not activate monitoring or control devices.</p>
            <div class="autonomy-template-grid">
              <button type="button" data-auto-template="comfort"><strong>Workshop comfort</strong><small>Presence + temperature + seasonal context → suggest HVAC</small></button>
              <button type="button" data-auto-template="air"><strong>Air quality &amp; ventilation</strong><small>Presence + CO₂/VOC/PM → suggest extraction or ventilation</small></button>
              <button type="button" data-auto-template="security"><strong>Workshop left open</strong><small>Absence + doors/windows/equipment → suggest a safety check</small></button>
              <button type="button" data-auto-template="lighting"><strong>Presence lighting</strong><small>Presence + low light → autonomous reversible lighting</small></button>
            </div>
          </article>
          <article class="autonomy-card autonomy-editor">
            <div class="autonomy-card-head"><div><h3 id="automation-editor-title">New automation draft</h3><p>Describe the intent and evidence. The future evaluator will implement the reasoning code separately.</p></div><button id="automation-cancel-edit" type="button" hidden>Cancel edit</button></div>
            <form id="automation-draft-form">
              <input id="automation-edit-id" type="hidden">
              <div class="autonomy-form-grid">
                <label>Name<input id="automation-name" maxlength="100" required placeholder="Workshop comfort advisor"></label>
                <label>Objective<input id="automation-objective" maxlength="1000" required placeholder="Notice uncomfortable workshop conditions while I am present"></label>
                <label>Presence entity<input id="automation-presence" list="automation-entity-options" maxlength="255" placeholder="binary_sensor.workshop_presence"></label>
                <label>Signal entities<input id="automation-signals" maxlength="1500" placeholder="sensor.workshop_temperature, sensor.outdoor_temperature"></label>
                <label class="wide">Context and baseline strategy<textarea id="automation-context-notes" rows="3" maxlength="3000" placeholder="Compare indoor temperature with seasonal outdoor norms, recent trend, time of day, and whether HVAC is already running."></textarea></label>
                <label class="wide">Suggestion wording<textarea id="automation-proposal" rows="2" maxlength="1000" placeholder="It is getting a little hot in the workshop. Would you like me to turn on the air conditioner?"></textarea></label>
                <label>Proposed action entity<input id="automation-action-entity" list="automation-entity-options" maxlength="255" placeholder="climate.workshop"></label>
                <label>Proposed HA service<input id="automation-action-service" maxlength="120" placeholder="climate.set_hvac_mode"></label>
                <label>Cooldown (minutes)<input id="automation-cooldown" type="number" min="1" max="1440" value="30"></label>
                <label>Minimum confidence<input id="automation-confidence" type="number" min="0.5" max="0.99" step="0.01" value="0.75"></label>
                <label>Risk class<select id="automation-risk"><option value="informational">Informational only</option><option value="low">Low risk</option><option value="controlled" selected>Controlled device</option><option value="high">High risk</option></select></label>
                <label>Execution authority<select id="automation-execution-policy"><option value="observe">Observe only</option><option value="suggest" selected>Suggest only</option><option value="approval_required">Require approval</option><option value="autonomous">Fully autonomous</option></select></label>
                <label>Maximum actions per hour<input id="automation-max-actions" type="number" min="1" max="60" value="2"></label>
                <label class="check"><input id="automation-notify-action" type="checkbox" checked> Notify after an action</label>
                <label class="check"><input id="automation-reversible-only" type="checkbox" checked> Autonomous actions must be reversible</label>
              </div>
              <div class="autonomy-form-actions"><button type="submit">Save draft</button><span id="automation-draft-state" role="status"></span></div>
            </form>
            <datalist id="automation-entity-options"></datalist>
          </article>
        </div>
        <article class="autonomy-card"><div class="autonomy-card-head"><div><h3>Automation Library</h3><p>Drafts are persistent design specifications. None are evaluated in v0.12.10.</p></div></div><div id="automation-library" class="autonomy-list"></div></article>
      </section>

      <section class="autonomy-view hidden" data-auto-panel="safety">
        <div class="autonomy-safety-grid">
          <article class="autonomy-card">
            <h3>Operating mode</h3><p>Set the global autonomy ceiling. Each automation keeps its own execution authority beneath this ceiling.</p>
            <form id="autonomy-settings-form">
              <label class="autonomy-mode"><input type="radio" name="autonomy-mode" value="observe_only"><span><strong>Observe only</strong><small>Build context and activity history without proposing actions.</small></span></label>
              <label class="autonomy-mode"><input type="radio" name="autonomy-mode" value="suggest_only" checked><span><strong>Suggest only</strong><small>Propose actions conversationally; you decide whether anything happens.</small></span></label>
              <label class="autonomy-mode"><input type="radio" name="autonomy-mode" value="approval_gated"><span><strong>Approval-gated</strong><small>Automations may act only after explicit approval.</small></span></label>
              <label class="autonomy-mode"><input type="radio" name="autonomy-mode" value="selective_autonomy"><span><strong>Selective autonomy</strong><small>Eligible low-risk automations may act without approval under their configured limits.</small></span></label>
              <div class="autonomy-form-grid">
                <label>Default presence entity<input id="autonomy-presence-entity" list="automation-entity-options" maxlength="255" placeholder="binary_sensor.workshop_presence"></label>
                <label>Minimum confidence<input id="autonomy-min-confidence" type="number" min="0.5" max="0.99" step="0.01" value="0.75"></label>
                <label>Default cooldown (minutes)<input id="autonomy-default-cooldown" type="number" min="1" max="1440" value="30"></label>
                <label>Autonomous risk ceiling<select id="autonomy-risk-ceiling"><option value="informational">Informational</option><option value="low" selected>Low risk</option><option value="controlled">Controlled device</option></select></label>
                <label class="check"><input id="autonomy-require-presence" type="checkbox" checked> Require confirmed workshop presence</label>
                <label class="check"><input id="autonomy-respect-quiet" type="checkbox" checked> Respect configured quiet hours</label>
                <label class="check"><input id="autonomy-notify-autonomous" type="checkbox" checked> Notify after autonomous actions</label>
              </div>
              <div class="autonomy-form-actions"><button type="submit">Save authority policy</button><span id="autonomy-settings-state" role="status"></span></div>
            </form>
          </article>
          <article class="autonomy-card">
            <h3>Hard safety boundaries</h3>
            <ul class="autonomy-boundary-list">
              <li><strong>Per-automation authority</strong><span>Each rule explicitly chooses observe, suggest, approval-required, or autonomous behavior.</span></li>
              <li><strong>Autonomous risk ceiling</strong><span>The global policy limits which risk classes may ever run without approval.</span></li>
              <li><strong>Evidence before suggestion</strong><span>Future suggestions must name the signals and context that caused them.</span></li>
              <li><strong>Confidence and cooldown</strong><span>Suppress weak, repetitive, or stale recommendations.</span></li>
              <li><strong>Presence-aware</strong><span>Comfort automations should require verified presence unless deliberately overridden.</span></li>
              <li><strong>High-risk controls separated</strong><span>Locks, machinery, heat sources, and security actions need stricter policies.</span></li>
              <li><strong>Auditable actions</strong><span>Autonomous decisions, evidence, actions, and outcomes must be recorded.</span></li>
            </ul>
          </article>
        </div>
      </section>

      <section class="autonomy-view hidden" data-auto-panel="activity">
        <article class="autonomy-card"><h3>Decision &amp; Activity Timeline</h3><p>Configuration changes appear now. Future observations, suppressed suggestions, approvals, actions, and outcomes will be auditable here.</p><div id="autonomy-timeline" class="autonomy-list"></div></article>
      </section>
    </div>
  </section>
'''
    text = text.replace(main_close, panel + main_close, 1)

    style_close = text.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.10 patch missing: style close")
    css = r'''
    .autonomy-shell{display:grid;gap:.9rem}.autonomy-header,.autonomy-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem}.autonomy-header h2,.autonomy-card h3{margin:.1rem 0}.autonomy-header p,.autonomy-card p{margin:.35rem 0;color:var(--text-muted)}
    .autonomy-engine-badge{border:1px solid var(--cyan);color:var(--cyan);padding:.45rem .65rem;border-radius:999px;font-size:.7rem;letter-spacing:.08em;white-space:nowrap}.autonomy-boundary{border:1px solid color-mix(in srgb,#f0b35b 65%,var(--line));background:rgba(240,179,91,.08);padding:.7rem .8rem;border-radius:6px}
    .autonomy-tabs{display:flex;gap:.4rem;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:.55rem}.autonomy-tabs button.active{border-color:var(--cyan);color:var(--cyan)}.autonomy-view.hidden{display:none}
    .autonomy-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem}.autonomy-metrics article,.autonomy-card{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:.85rem}.autonomy-metrics span,.autonomy-metrics small{display:block;color:var(--text-muted)}.autonomy-metrics strong{display:block;margin:.25rem 0;color:var(--cyan);font-size:1.05rem}
    .autonomy-overview-grid,.autonomy-safety-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem;margin-top:.75rem}.autonomy-library-grid{display:grid;grid-template-columns:minmax(240px,.7fr) minmax(420px,1.3fr);gap:.75rem;margin-bottom:.75rem}
    .autonomy-template-grid,.autonomy-list{display:grid;gap:.55rem}.autonomy-template-grid button{text-align:left;display:grid;gap:.2rem}.autonomy-template-grid small,.autonomy-empty{color:var(--text-muted)}.autonomy-empty{border:1px dashed var(--line);padding:.8rem;border-radius:6px}
    .autonomy-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.6rem;margin-top:.65rem}.autonomy-form-grid label{display:grid;gap:.3rem}.autonomy-form-grid .wide{grid-column:1/-1}.autonomy-form-grid .check{display:flex;align-items:center;gap:.45rem}.autonomy-form-actions{display:flex;align-items:center;gap:.7rem;margin-top:.7rem}
    .autonomy-mode{display:flex;gap:.6rem;border:1px solid var(--line);padding:.65rem;border-radius:6px;margin:.5rem 0}.autonomy-mode span,.autonomy-mode small{display:block}.autonomy-mode small{color:var(--text-muted);margin-top:.2rem}.autonomy-mode.locked{opacity:.65}
    .autonomy-boundary-list{display:grid;gap:.6rem;padding:0;list-style:none}.autonomy-boundary-list li{display:grid;gap:.15rem;border-left:2px solid var(--cyan);padding-left:.65rem}.autonomy-boundary-list span{color:var(--text-muted)}
    .autonomy-draft,.autonomy-context-row,.autonomy-event{border:1px solid var(--line);border-radius:6px;padding:.7rem;display:grid;gap:.35rem}.autonomy-draft-head{display:flex;justify-content:space-between;gap:.7rem}.autonomy-tags{display:flex;flex-wrap:wrap;gap:.35rem}.autonomy-tags span{border:1px solid var(--line);border-radius:999px;padding:.2rem .45rem;font-size:.7rem;color:var(--text-muted)}.autonomy-draft-actions{display:flex;gap:.4rem}.autonomy-event time{color:var(--text-muted);font-size:.72rem}
    @media(max-width:900px){.autonomy-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.autonomy-overview-grid,.autonomy-safety-grid,.autonomy-library-grid{grid-template-columns:1fr}.autonomy-header{display:grid}.autonomy-engine-badge{white-space:normal}.autonomy-form-grid{grid-template-columns:1fr}.autonomy-form-grid .wide{grid-column:auto}}
'''
    text = text[:style_close] + css + text[style_close:]

    control_map = '''      entities: ["entities-tab", "entities-panel"],'''
    require(text, control_map, "developer browser evidence")
    text = text.replace(
        control_map,
        '''      automations: ["automations-tab", "automations-panel", "automation-library"],
''' + control_map,
        1,
    )

    show_files = '  const showFiles = panel === "files";\n'
    require(text, show_files, "base panel routing")
    text = text.replace(show_files, show_files + '  const showAutomations = panel === "automations";\n', 1)
    files_panel_toggle = '  document.getElementById("files-panel")?.classList.toggle("hidden", !showFiles);\n'
    require(text, files_panel_toggle, "base automation panel visibility")
    text = text.replace(
        files_panel_toggle,
        files_panel_toggle + '  document.getElementById("automations-panel")?.classList.toggle("hidden", !showAutomations);\n',
        1,
    )
    files_tab_toggle = '  document.getElementById("files-tab")?.classList.toggle("active", showFiles);\n'
    require(text, files_tab_toggle, "base automation tab state")
    text = text.replace(
        files_tab_toggle,
        files_tab_toggle + '  document.getElementById("automations-tab")?.classList.toggle("active", showAutomations);\n',
        1,
    )

    runtime = r'''
<script id="zbrano-v01210-autonomous-automations">
(() => {
  const tab=document.getElementById("automations-tab");
  const panel=document.getElementById("automations-panel");
  if(!tab||!panel)return;
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  let state={settings:{},automations:[],suggestions:[],timeline:[],engine:{}};
  let entityMap=new Map();

  async function api(path,options={}){
    const response=await fetch(path,{cache:"no-store",...options});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);
    return data;
  }

  function activate(){
    for(const id of ["chat-panel","entities-panel","settings-panel","plugins-panel","files-panel","developer-panel","automations-panel"]){document.getElementById(id)?.classList.toggle("hidden",id!=="automations-panel")}
    for(const id of ["chat-tab","entities-tab","settings-tab","plugins-tab","files-tab","developer-tab","automations-tab"]){document.getElementById(id)?.classList.toggle("active",id==="automations-tab")}
  }

  function showView(name){
    for(const button of panel.querySelectorAll("[data-auto-view]")){const active=button.dataset.autoView===name;button.classList.toggle("active",active);button.setAttribute("aria-selected",String(active))}
    for(const view of panel.querySelectorAll("[data-auto-panel]")){view.classList.toggle("hidden",view.dataset.autoPanel!==name)}
  }

  function modeLabel(value){return ({observe_only:"Observe only",suggest_only:"Suggest only",approval_gated:"Approval-gated",selective_autonomy:"Selective autonomy"})[value]||"Suggest only"}
  function authorityLabel(value){return ({observe:"Observe only",suggest:"Suggest only",approval_required:"Approval required",autonomous:"Fully autonomous"})[value]||"Suggest only"}
  function renderSummary(){
    $("autonomy-engine-status").textContent=state.engine?.status==="foundation_ready"?"Foundation ready":"Unavailable";
    $("autonomy-mode-summary").textContent=modeLabel(state.settings?.operating_mode);
    $("autonomy-mode-detail").textContent=state.settings?.operating_mode==="selective_autonomy"?`Autonomous up to ${state.settings?.autonomous_risk_ceiling||"low"} risk`:"Per-automation authority limited by global policy";
    $("autonomy-draft-count").textContent=String(state.automations.length);
    $("autonomy-suggestion-count").textContent=String(state.suggestions.length);
  }

  function renderSuggestions(){
    const root=$("autonomy-suggestions");root.replaceChildren();
    if(!state.suggestions.length){root.innerHTML='<div class="autonomy-empty">No suggestions yet. ZBRANO will never invent activity before the evaluator is implemented.</div>';return}
    for(const item of state.suggestions){const row=document.createElement("div");row.className="autonomy-draft";row.innerHTML=`<strong>${esc(item.title||"Suggestion")}</strong><span>${esc(item.detail||"")}</span>`;root.appendChild(row)}
  }

  function referencedEntities(){
    const ids=new Set();
    if(state.settings?.presence_entity)ids.add(state.settings.presence_entity);
    for(const item of state.automations){if(item.presence_entity)ids.add(item.presence_entity);for(const id of item.signal_entities||[])ids.add(id);if(item.action_entity)ids.add(item.action_entity)}
    return [...ids];
  }

  function renderContext(){
    const root=$("autonomy-context");root.replaceChildren();const ids=referencedEntities();
    if(!ids.length){root.innerHTML='<div class="autonomy-empty">No entities referenced yet. Add a draft or set the default presence entity.</div>';return}
    for(const id of ids){const entity=entityMap.get(id);const row=document.createElement("div");row.className="autonomy-context-row";row.innerHTML=`<div class="autonomy-draft-head"><strong>${esc(entity?.friendly_name||id)}</strong><span>${esc(entity?.state??"not loaded")}</span></div><small>${esc(id)}${entity?.unit?` · ${esc(entity.unit)}`:""}</small>`;root.appendChild(row)}
  }

  function renderLibrary(){
    const root=$("automation-library");root.replaceChildren();
    if(!state.automations.length){root.innerHTML='<div class="autonomy-empty">No automation drafts. Start with a quick design or create your own.</div>';return}
    for(const item of state.automations){
      const row=document.createElement("div");row.className="autonomy-draft";
      const tags=["Draft",authorityLabel(item.execution_policy),`${Math.round(Number(item.confidence_threshold||0)*100)}% confidence`,`${item.cooldown_minutes} min cooldown`,item.risk_level];
      row.innerHTML=`<div class="autonomy-draft-head"><div><strong>${esc(item.name)}</strong><div>${esc(item.objective)}</div></div><div class="autonomy-draft-actions"><button type="button" data-auto-edit="${esc(item.id)}">Edit</button><button type="button" data-auto-delete="${esc(item.id)}">Delete</button></div></div><div class="autonomy-tags">${tags.map(tag=>`<span>${esc(tag)}</span>`).join("")}</div><small>Signals: ${esc((item.signal_entities||[]).join(", ")||"not selected")} · Proposed action: ${esc(item.action_service||"not specified")}</small>`;
      root.appendChild(row);
    }
  }

  function renderTimeline(){
    const root=$("autonomy-timeline");root.replaceChildren();
    if(!state.timeline.length){root.innerHTML='<div class="autonomy-empty">No activity yet. Configuration changes and future decisions will appear here.</div>';return}
    for(const item of state.timeline){const row=document.createElement("div");row.className="autonomy-event";row.innerHTML=`<strong>${esc(item.title)}</strong>${item.detail?`<span>${esc(item.detail)}</span>`:""}<time>${new Date(Number(item.created_at||0)*1000).toLocaleString()}</time>`;root.appendChild(row)}
  }

  function renderSettings(){
    const settings=state.settings||{};
    const radio=panel.querySelector(`input[name="autonomy-mode"][value="${settings.operating_mode||"suggest_only"}"]`);if(radio)radio.checked=true;
    $("autonomy-presence-entity").value=settings.presence_entity||"";
    $("autonomy-min-confidence").value=String(settings.minimum_confidence??0.75);
    $("autonomy-default-cooldown").value=String(settings.default_cooldown_minutes??30);
    $("autonomy-risk-ceiling").value=settings.autonomous_risk_ceiling||"low";
    $("autonomy-require-presence").checked=settings.require_presence!==false;
    $("autonomy-respect-quiet").checked=settings.respect_quiet_hours!==false;
    $("autonomy-notify-autonomous").checked=settings.notify_after_autonomous_action!==false;
  }

  function renderAll(){renderSummary();renderSuggestions();renderContext();renderLibrary();renderTimeline();renderSettings()}

  async function loadEntityContext(){
    const root=$("autonomy-context");root.innerHTML='<div class="autonomy-empty">Loading Home Assistant context…</div>';
    try{
      const data=await api("api/ha/entities");entityMap=new Map((data.entities||[]).map(item=>[item.entity_id,item]));
      const options=$("automation-entity-options");options.replaceChildren();
      for(const entity of data.entities||[]){const option=document.createElement("option");option.value=entity.entity_id;option.label=entity.friendly_name||entity.entity_id;options.appendChild(option)}
      renderContext();
    }catch(error){root.innerHTML=`<div class="autonomy-empty">Context unavailable: ${esc(error.message||error)}</div>`}
  }

  async function loadWorkspace(){state=await api("api/automations");renderAll();await loadEntityContext()}

  function clearEditor(){
    $("automation-draft-form").reset();$("automation-edit-id").value="";$("automation-editor-title").textContent="New automation draft";$("automation-cancel-edit").hidden=true;$("automation-cooldown").value=String(state.settings?.default_cooldown_minutes||30);$("automation-confidence").value=String(state.settings?.minimum_confidence||0.75);$("automation-risk").value="controlled";$("automation-execution-policy").value="suggest";$("automation-max-actions").value="2";$("automation-notify-action").checked=true;$("automation-reversible-only").checked=true;$("automation-draft-state").textContent="";
  }

  function fillEditor(item){
    $("automation-edit-id").value=item.id||"";$("automation-name").value=item.name||"";$("automation-objective").value=item.objective||"";$("automation-presence").value=item.presence_entity||"";$("automation-signals").value=(item.signal_entities||[]).join(", ");$("automation-context-notes").value=item.context_notes||"";$("automation-proposal").value=item.proposal_template||"";$("automation-action-entity").value=item.action_entity||"";$("automation-action-service").value=item.action_service||"";$("automation-cooldown").value=String(item.cooldown_minutes||30);$("automation-confidence").value=String(item.confidence_threshold||0.75);$("automation-risk").value=item.risk_level||"controlled";$("automation-execution-policy").value=item.execution_policy||"suggest";$("automation-max-actions").value=String(item.max_actions_per_hour||2);$("automation-notify-action").checked=item.notify_on_action!==false;$("automation-reversible-only").checked=item.reversible_only!==false;$("automation-editor-title").textContent=item.id?"Edit automation draft":"New automation draft";$("automation-cancel-edit").hidden=!item.id;showView("library");$("automation-name").focus();
  }

  function template(name){
    const presence=state.settings?.presence_entity||"binary_sensor.workshop_presence";
    const templates={
      comfort:{name:"Workshop comfort advisor",objective:"Notice uncomfortable temperature while I am present and propose an appropriate comfort action",presence_entity:presence,signal_entities:["sensor.workshop_temperature","sensor.outdoor_temperature","sensor.workshop_humidity"],context_notes:"Compare indoor temperature and trend with outdoor conditions, season, time of day, humidity, recent occupancy, and current HVAC state. Avoid reacting to brief sensor spikes.",proposal_template:"It is getting a little hot in the workshop. Would you like me to turn on the air conditioner?",action_entity:"climate.workshop",action_service:"climate.set_hvac_mode",cooldown_minutes:30,confidence_threshold:0.8,risk_level:"controlled",execution_policy:"approval_required",notify_on_action:true,reversible_only:true,max_actions_per_hour:2},
      air:{name:"Workshop air quality advisor",objective:"Notice worsening workshop air quality while occupied and suggest ventilation",presence_entity:presence,signal_entities:["sensor.workshop_co2","sensor.workshop_voc","sensor.workshop_pm25"],context_notes:"Use sustained readings and trends, not one sample. Consider active extraction and outdoor air quality.",proposal_template:"Air quality is getting worse in the workshop. Would you like me to start ventilation?",action_entity:"fan.workshop_extractor",action_service:"fan.turn_on",cooldown_minutes:20,confidence_threshold:0.82,risk_level:"controlled",execution_policy:"approval_required",notify_on_action:true,reversible_only:true,max_actions_per_hour:2},
      security:{name:"Workshop departure safety check",objective:"Notice when the workshop becomes unoccupied while an opening or selected equipment remains active",presence_entity:presence,signal_entities:["binary_sensor.workshop_door","binary_sensor.workshop_window","switch.workshop_equipment"],context_notes:"Require sustained absence and distinguish expected equipment from anything that should be switched off.",proposal_template:"It looks like the workshop is empty, but something may have been left open or running. Would you like a safety check?",action_entity:"",action_service:"",cooldown_minutes:30,confidence_threshold:0.9,risk_level:"high",execution_policy:"suggest",notify_on_action:true,reversible_only:true,max_actions_per_hour:1},
      lighting:{name:"Workshop presence lighting",objective:"Turn workshop lighting on when presence is confirmed and light is low",presence_entity:presence,signal_entities:["sensor.workshop_illuminance","light.workshop"],context_notes:"Require stable presence and low illuminance. Do nothing when daylight is sufficient or lighting is already on.",proposal_template:"Workshop lighting was turned on because presence and low light were confirmed.",action_entity:"light.workshop",action_service:"light.turn_on",cooldown_minutes:10,confidence_threshold:0.9,risk_level:"low",execution_policy:"autonomous",notify_on_action:true,reversible_only:true,max_actions_per_hour:4}
    };fillEditor(templates[name])
  }

  panel.querySelector(".autonomy-tabs")?.addEventListener("click",event=>{const button=event.target.closest("[data-auto-view]");if(button)showView(button.dataset.autoView)});
  panel.addEventListener("click",async event=>{
    const templateButton=event.target.closest("[data-auto-template]");if(templateButton){template(templateButton.dataset.autoTemplate);return}
    const edit=event.target.closest("[data-auto-edit]");if(edit){const item=state.automations.find(value=>value.id===edit.dataset.autoEdit);if(item)fillEditor(item);return}
    const remove=event.target.closest("[data-auto-delete]");if(remove){if(!confirm("Delete this automation draft?"))return;await api(`api/automations/${encodeURIComponent(remove.dataset.autoDelete)}`,{method:"DELETE"});await loadWorkspace()}
  });

  $("automation-draft-form").addEventListener("submit",async event=>{
    event.preventDefault();const id=$("automation-edit-id").value;const status=$("automation-draft-state");status.textContent="Saving…";
    const body={name:$("automation-name").value.trim(),objective:$("automation-objective").value.trim(),presence_entity:$("automation-presence").value.trim(),signal_entities:$("automation-signals").value.split(/[,\n]/).map(v=>v.trim()).filter(Boolean),context_notes:$("automation-context-notes").value.trim(),proposal_template:$("automation-proposal").value.trim(),action_entity:$("automation-action-entity").value.trim(),action_service:$("automation-action-service").value.trim(),cooldown_minutes:Number($("automation-cooldown").value),confidence_threshold:Number($("automation-confidence").value),risk_level:$("automation-risk").value,execution_policy:$("automation-execution-policy").value,notify_on_action:$("automation-notify-action").checked,reversible_only:$("automation-reversible-only").checked,max_actions_per_hour:Number($("automation-max-actions").value)};
    try{await api(id?`api/automations/${encodeURIComponent(id)}`:"api/automations",{method:id?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});clearEditor();await loadWorkspace();status.textContent="Draft saved."}catch(error){status.textContent=`Save failed: ${error.message||error}`}
  });
  $("automation-cancel-edit").addEventListener("click",clearEditor);
  $("autonomy-settings-form").addEventListener("submit",async event=>{
    event.preventDefault();const status=$("autonomy-settings-state");status.textContent="Saving…";const mode=panel.querySelector('input[name="autonomy-mode"]:checked')?.value||"suggest_only";
    const body={operating_mode:mode,presence_entity:$("autonomy-presence-entity").value.trim(),require_presence:$("autonomy-require-presence").checked,respect_quiet_hours:$("autonomy-respect-quiet").checked,minimum_confidence:Number($("autonomy-min-confidence").value),default_cooldown_minutes:Number($("autonomy-default-cooldown").value),autonomous_risk_ceiling:$("autonomy-risk-ceiling").value,notify_after_autonomous_action:$("autonomy-notify-autonomous").checked};
    try{await api("api/automations/settings",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});status.textContent="Authority policy saved.";await loadWorkspace()}catch(error){status.textContent=`Save failed: ${error.message||error}`}
  });
  $("autonomy-refresh-context").addEventListener("click",loadEntityContext);

  document.addEventListener("click",event=>{const other=event.target.closest?.("#chat-tab,#entities-tab,#settings-tab,#plugins-tab,#files-tab,#developer-tab");if(other){panel.classList.add("hidden");tab.classList.remove("active")}},true);
  tab.addEventListener("click",event=>{event.preventDefault();event.stopImmediatePropagation();activate();loadWorkspace().catch(error=>{$("autonomy-context").innerHTML=`<div class="autonomy-empty">Automation workspace unavailable: ${esc(error.message||error)}</div>`})},true);
  clearEditor();
  window.zbranoAutomationWorkspace={ready:true,load:loadWorkspace,showView};
})();
</script>
'''
    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.10 patch missing: body close")
    text = text[:body_close] + runtime + text[body_close:]
    text = text.replace("HUD 0.12.9", "HUD 0.12.10")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required_main = (
        'version="0.12.10"', "class AutonomySettingsRequest", "class AutonomousAutomationRequest",
        'AUTOMATION_STORAGE_PATH = Path("/data/autonomous_automations.json")',
        '@app.get("/api/automations")', '@app.post("/api/automations")',
        '"continuous_monitoring": False', '"automatic_execution": False',
        'execution_policy: str = Field', '"autonomous_risk_ceiling": "low"',
        '"automations": ("/api/automations",)', '"Autonomous Automations API operational"',
        '"automations": automation_store()', '"automation_count": len(automation_store()["automations"])',
    )
    required_index = (
        'id="automations-tab"', 'id="automations-panel"', "AUTONOMOUS AUTOMATIONS",
        "Suggestion Inbox", "Workshop Context Snapshot", "Automation Library",
        "Safety &amp; Authority", "Hard safety boundaries", "Decision &amp; Activity Timeline",
        'id="zbrano-v01210-autonomous-automations"', "Continuous evaluator not active",
        'value="selective_autonomy"', "Per-automation authority", "Workshop presence lighting",
        "HUD 0.12.10",
        "Compatible providers offer Connect and browser authorization",
    )
    missing = [marker for marker in required_main if marker not in main]
    missing += [marker for marker in required_index if marker not in index]
    if missing:
        raise RuntimeError("ZBRANO v0.12.10 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
