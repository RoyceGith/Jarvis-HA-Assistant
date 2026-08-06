from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Jarvis agent controls patch could not find: {label}")
    return text.replace(old, new, 1)


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    text = replace_required(
        text,
        '''            <label>Voice
              <select id="voice-select">
                <option value="cedar">Cedar</option>
                <option value="marin">Marin</option>
                <option value="onyx">Onyx</option>
                <option value="coral">Coral</option>
                <option value="nova">Nova</option>
                <option value="sage">Sage</option>
              </select>
            </label>
            <span>↑ ↓ history · AI-generated voice</span>''',
        '''            <label>Voice
              <select id="voice-select">
                <option value="cedar">Cedar</option>
                <option value="marin">Marin</option>
                <option value="onyx">Onyx</option>
                <option value="coral">Coral</option>
                <option value="nova">Nova</option>
                <option value="sage">Sage</option>
              </select>
            </label>
            <label>Agent Model
              <select id="agent-model">
                <option value="gpt-5.5">GPT-5.5</option>
                <option value="gpt-5-mini">GPT-5 mini</option>
              </select>
            </label>
            <label>Intelligence
              <select id="reasoning-effort">
                <option value="none">None</option>
                <option value="minimal">Minimal</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="xhigh">Extra High</option>
              </select>
            </label>
            <span>↑ ↓ history · AI-generated voice</span>''',
        "chat agent controls",
    )
    text = replace_required(
        text,
        'const voiceSelect = document.getElementById("voice-select");',
        'const voiceSelect = document.getElementById("voice-select");\nconst agentModel = document.getElementById("agent-model");\nconst reasoningEffort = document.getElementById("reasoning-effort");',
        "agent control declarations",
    )
    text = replace_required(
        text,
        'let hasSavedSpeechProvider = false;',
        '''let hasSavedSpeechProvider = false;
let agentControlsLoaded = false;

function addAgentModelOption(modelId) {
  const cleanId = String(modelId || "").trim();
  if (!cleanId || [...agentModel.options].some(option => option.value === cleanId)) return;
  const option = document.createElement("option");
  option.value = cleanId;
  option.textContent = cleanId;
  agentModel.appendChild(option);
}

async function loadAgentControls(preferences = null) {
  try {
    const response = await fetch("api/models");
    const data = await response.json();
    const selectedModel = preferences?.agent_model || data.selected_model || "gpt-5-mini";
    for (const modelId of data.models || []) addAgentModelOption(modelId);
    addAgentModelOption(selectedModel);
    agentModel.value = selectedModel;
    reasoningEffort.value = preferences?.reasoning_effort || data.reasoning_effort || "medium";
    agentControlsLoaded = true;
  } catch {
    const selectedModel = preferences?.agent_model || "gpt-5-mini";
    addAgentModelOption(selectedModel);
    agentModel.value = selectedModel;
    reasoningEffort.value = preferences?.reasoning_effort || "medium";
  }
}

async function saveAgentControls() {
  if (!agentControlsLoaded) return;
  const response = await fetch("api/agent/settings", {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({agent_model: agentModel.value, reasoning_effort: reasoningEffort.value}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    setVoiceState("AGENT SETTINGS ERROR", data.detail || `HTTP ${response.status}`);
    return;
  }
  jarvisPreferences = {...jarvisPreferences, ...(data.preferences || {})};
  setVoiceState("AGENT READY");
}

agentModel.addEventListener("change", saveAgentControls);
reasoningEffort.addEventListener("change", saveAgentControls);''',
        "agent control behavior",
    )
    text = replace_required(
        text,
        '    jarvisPreferences = data.preferences || {};\n    elevenLabsModel.value = jarvisPreferences.elevenlabs_model || "eleven_flash_v2_5";',
        '    jarvisPreferences = data.preferences || {};\n    await loadAgentControls(jarvisPreferences);\n    elevenLabsModel.value = jarvisPreferences.elevenlabs_model || "eleven_flash_v2_5";',
        "load agent settings",
    )
    text = replace_required(
        text,
        '        elevenlabs_speaker_boost: elevenLabsSpeakerBoost.checked,\n        auto_speak: settingsAutoSpeak.checked,',
        '        elevenlabs_speaker_boost: elevenLabsSpeakerBoost.checked,\n        agent_model: agentModel.value,\n        reasoning_effort: reasoningEffort.value,\n        auto_speak: settingsAutoSpeak.checked,',
        "save agent settings",
    )
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = replace_required(
        text,
        '    "elevenlabs_speaker_boost": False,\n    "auto_speak": True,',
        '    "elevenlabs_speaker_boost": False,\n    "agent_model": OPENAI_MODEL,\n    "reasoning_effort": "medium",\n    "auto_speak": True,',
        "agent preference defaults",
    )
    text = replace_required(
        text,
        '    elevenlabs_speaker_boost: bool = False\n    auto_speak: bool = True',
        '    elevenlabs_speaker_boost: bool = False\n    agent_model: str = Field(default=OPENAI_MODEL, min_length=1, max_length=120)\n    reasoning_effort: str = Field(default="medium", pattern="^(none|minimal|low|medium|high|xhigh)$")\n    auto_speak: bool = True',
        "agent settings fields",
    )
    text = replace_required(
        text,
        'class SettingsRestoreRequest(BaseModel):',
        '''class AgentSettingsUpdate(BaseModel):
    agent_model: str = Field(min_length=1, max_length=120)
    reasoning_effort: str = Field(default="medium", pattern="^(none|minimal|low|medium|high|xhigh)$")


class SettingsRestoreRequest(BaseModel):''',
        "agent settings request",
    )
    text = replace_required(
        text,
        'async def _run_jarvis_stream_events(message: str, session_id: str = "default") -> AsyncIterator[bytes]:',
        '''def active_agent_model() -> str:
    model = str(load_preferences().get("agent_model") or OPENAI_MODEL).strip()
    return model or OPENAI_MODEL


def active_reasoning_effort() -> str:
    effort = str(load_preferences().get("reasoning_effort") or "medium").strip().lower()
    return effort if effort in {"none", "minimal", "low", "medium", "high", "xhigh"} else "medium"


def agent_reasoning_payload() -> dict[str, Any]:
    effort = active_reasoning_effort()
    return {} if effort == "none" else {"reasoning": {"effort": effort}}


async def _run_jarvis_stream_events(message: str, session_id: str = "default") -> AsyncIterator[bytes]:''',
        "active agent helpers",
    )
    text = text.replace('"model": OPENAI_MODEL,', '"model": active_agent_model(),\n            **agent_reasoning_payload(),')
    text = replace_required(
        text,
        '@app.get("/api/settings")\nasync def read_settings() -> dict[str, Any]:',
        '''@app.get("/api/models")
async def list_openai_models() -> dict[str, Any]:
    preferences = load_preferences()
    selected_model = str(preferences.get("agent_model") or OPENAI_MODEL)
    models = {"gpt-5.5", "gpt-5-mini", selected_model, OPENAI_MODEL}
    if OPENAI_API_KEY:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get("https://api.openai.com/v1/models", headers=headers)
            if not response.is_error:
                for item in response.json().get("data", []):
                    model_id = str(item.get("id") or "")
                    if model_id.startswith("gpt-"):
                        models.add(model_id)
        except (httpx.HTTPError, ValueError, TypeError):
            pass
    return {"models": sorted(models), "selected_model": selected_model, "reasoning_effort": preferences.get("reasoning_effort", "medium")}


@app.put("/api/agent/settings")
async def update_agent_settings(request: AgentSettingsUpdate) -> dict[str, Any]:
    preferences = load_preferences()
    preferences.update({"agent_model": request.agent_model.strip(), "reasoning_effort": request.reasoning_effort})
    return {"saved": True, "preferences": save_preferences(preferences)}


@app.get("/api/settings")
async def read_settings() -> dict[str, Any]:''',
        "agent API endpoints",
    )
    text = replace_required(
        text,
        '                "elevenlabs_speaker_boost": request.elevenlabs_speaker_boost,\n                "auto_speak": request.auto_speak,',
        '                "elevenlabs_speaker_boost": request.elevenlabs_speaker_boost,\n                "agent_model": request.agent_model.strip(),\n                "reasoning_effort": request.reasoning_effort,\n                "auto_speak": request.auto_speak,',
        "persist agent preferences",
    )
    MAIN.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_index()
    patch_main()
