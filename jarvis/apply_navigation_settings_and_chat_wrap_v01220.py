from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.20 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


def patch_frontend(frontend: str) -> str:
    old_nav = '''  <nav>
    <button id="chat-tab" class="active">Chat</button>
    <button id="automations-tab">Automations</button>
    <button id="entities-tab">Entities</button>
    <button id="settings-tab">Settings</button>
    <button id="developer-tab">Developer</button>
    <button id="files-tab">Shared Files</button>
    <button id="plugins-tab">Plugins</button>
  </nav>'''
    new_nav = '''  <nav aria-label="Primary navigation">
    <button id="chat-tab" class="active">Chat</button>
    <button id="files-tab">Shared Files</button>
    <button id="plugins-tab">Plugins</button>
    <button id="entities-tab">Entities</button>
    <button id="automations-tab">Automations</button>
    <button id="settings-tab">Settings</button>
    <button id="developer-tab">Developer</button>
  </nav>'''
    frontend = replace_once(frontend, old_nav, new_nav, "ordered primary navigation")

    settings_stack = '    <div class="settings-stack">\n    <div class="settings-card">\n      <h2>APPEARANCE</h2>'
    settings_tabs = '''    <div class="settings-stack">
    <div class="settings-category-tabs" role="tablist" aria-label="Settings categories">
      <button type="button" class="settings-category-tab active" role="tab" aria-selected="true" data-settings-target="appearance">Appearance</button>
      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="voice">Voice</button>
      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="responses">Responses</button>
      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="instructions">Instructions</button>
      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="playback">Playback</button>
      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="memory">Memory</button>
    </div>
    <div class="settings-card" data-settings-category="appearance">
      <h2>APPEARANCE</h2>'''
    frontend = replace_once(frontend, settings_stack, settings_tabs, "settings category tabs")

    cards = (
        ("ELEVENLABS VOICE", "voice"),
        ("RESPONSES &amp; BEHAVIOR", "responses"),
        ("GENERAL INSTRUCTIONS", "instructions"),
        ("VOICE PLAYBACK &amp; QUIET HOURS", "playback"),
        ("CONVERSATION MEMORY", "memory"),
    )
    for heading, category in cards:
        old = f'    <div class="settings-card">\n      <h2>{heading}</h2>'
        new = f'    <div class="settings-card" data-settings-category="{category}" hidden>\n      <h2>{heading}</h2>'
        frontend = replace_once(frontend, old, new, f"{category} settings card")

    style_close = frontend.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.20 patch missing: style close")
    css = r'''
    /* v0.12.20 navigation, settings categories, and resilient response wrapping. */
    nav { width: 100%; flex-wrap: wrap; align-items: center; }
    #developer-tab {
      margin-left: auto;
      border-color: color-mix(in srgb, var(--cyan) 34%, var(--line));
    }
    #developer-tab::before { content: "◇"; margin-right: .4rem; color: var(--cyan); }
    .settings-category-tabs {
      position: sticky;
      top: -1rem;
      z-index: 5;
      display: flex;
      gap: .4rem;
      flex-wrap: wrap;
      padding: .75rem 0;
      background: color-mix(in srgb, var(--panel) 94%, transparent);
      backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--line);
    }
    .settings-category-tab { padding: .58rem .8rem; font-size: .82rem; font-weight: 600; }
    .settings-category-tab.active { color: var(--cyan); }
    .settings-card[data-settings-category][hidden] { display: none !important; }
    .message.jarvis,
    .message.jarvis p,
    .message.jarvis li,
    .message.jarvis a,
    .message.jarvis blockquote,
    .message.jarvis h2,
    .message.jarvis h3,
    .message.jarvis h4 {
      min-width: 0;
      max-width: 100%;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .message.jarvis pre {
      max-width: 100%;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .message.jarvis code { white-space: break-spaces; overflow-wrap: anywhere; word-break: break-word; }
    .core-stage.neuron-intense #brain-network { opacity: 1 !important; }
    body.jarvis-input-active .core-stage.neuron-intense #brain-network { opacity: 1 !important; }
    @media (max-width: 760px) {
      nav { gap: .35rem; }
      nav button { padding: .55rem .7rem; }
      #developer-tab { margin-left: auto; }
      .settings-category-tabs { top: -.65rem; }
    }
'''
    frontend = frontend[:style_close] + css + frontend[style_close:]

    submit_clear = '''  input.value = "";
  resizeComposer();
  startResponseActivity("Thinking");'''
    frontend = replace_once(
        frontend,
        submit_clear,
        '''  input.value = "";
  resizeComposer();
  document.body.classList.remove("jarvis-input-active");
  startResponseActivity("Thinking");''',
        "restore saved neural opacity after first message",
    )

    script_marker = 'startBrainNetwork();\n</script>'
    settings_script = r'''startBrainNetwork();

(() => {
  const tabs = [...document.querySelectorAll(".settings-category-tab")];
  const cards = [...document.querySelectorAll(".settings-card[data-settings-category]")];
  if (!tabs.length || !cards.length) return;
  const activate = target => {
    const selected = tabs.some(tab => tab.dataset.settingsTarget === target) ? target : "appearance";
    for (const tab of tabs) {
      const active = tab.dataset.settingsTarget === selected;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    }
    for (const card of cards) card.hidden = card.dataset.settingsCategory !== selected;
    try { localStorage.setItem("zbrano_settings_category_v1", selected); } catch (_) {}
  };
  for (const tab of tabs) {
    tab.addEventListener("click", () => activate(tab.dataset.settingsTarget));
    tab.addEventListener("keydown", event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const current = tabs.indexOf(tab);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
        : (current + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      activate(tabs[next].dataset.settingsTarget);
      tabs[next].focus();
    });
  }
  let initial = "appearance";
  try { initial = localStorage.getItem("zbrano_settings_category_v1") || initial; } catch (_) {}
  activate(initial);
})();
</script>'''
    frontend = replace_once(frontend, script_marker, settings_script, "settings category controller")
    frontend = frontend.replace("HUD 0.12.19", "HUD 0.12.20")
    return frontend


def patch_backend(backend: str) -> str:
    backend = backend.replace('version="0.12.19"', 'version="0.12.20"')
    backend = backend.replace('"version": "0.12.19"', '"version": "0.12.20"')
    return backend


def verify() -> None:
    frontend = INDEX.read_text(encoding="utf-8")
    backend = MAIN.read_text(encoding="utf-8")
    required_frontend = (
        "HUD 0.12.20",
        'aria-label="Primary navigation"',
        'id="chat-tab" class="active">Chat</button>\n    <button id="files-tab">Shared Files</button>\n    <button id="plugins-tab">Plugins</button>\n    <button id="entities-tab">Entities</button>\n    <button id="automations-tab">Automations</button>\n    <button id="settings-tab">Settings</button>\n    <button id="developer-tab">Developer</button>',
        "#developer-tab {",
        "margin-left: auto",
        'data-settings-target="appearance"',
        'data-settings-target="memory"',
        'data-settings-category="voice" hidden',
        "zbrano_settings_category_v1",
        ".message.jarvis pre",
        "overflow-wrap: anywhere",
        ".core-stage.neuron-intense #brain-network { opacity: 1 !important; }",
        "setNeuronIntensity(false);",
        'document.body.classList.remove("jarvis-input-active");',
    )
    for marker in required_frontend:
        require(frontend, marker, marker)
    for marker in ('version="0.12.20"', '"version": "0.12.20"'):
        require(backend, marker, marker)


def main() -> None:
    frontend = patch_frontend(INDEX.read_text(encoding="utf-8"))
    backend = patch_backend(MAIN.read_text(encoding="utf-8"))
    INDEX.write_text(frontend, encoding="utf-8")
    MAIN.write_text(backend, encoding="utf-8")
    verify()


if __name__ == "__main__":
    main()
