from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.6 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    old_description = (
        '            "Run a targeted, read-only investigation of a reported ZBRANO feature failure. "\n'
        '            "Use this whenever the user says a ZBRANO feature is broken, even when general "\n'
        '            "diagnostics are healthy. Return evidence and fault boundaries before proposing code changes."'
    )
    new_description = (
        '            "Run one targeted, read-only ZBRANO feature check. "\n'
        '            "Use this for check, audit, verify, health, version, or broken-feature requests, even when "\n'
        '            "general diagnostics are healthy. Return evidence and fault boundaries before proposing code changes."'
    )
    require(text, old_description, "Developer investigation tool description")
    text = text.replace(old_description, new_description, 1)

    old_instruction = (
        "When the user reports that a ZBRANO feature is not working, call investigate_zbrano_feature exactly once for that report, even if general diagnostics are healthy. "
        "After it returns, do not call it again in the same turn; use only the returned evidence and GitHub repository tools. "
        "While Developer Mode is active, Workshop Memory, Home Assistant, and non-GitHub MCP tools are unavailable."
    )
    new_instruction = (
        "When the user asks to check, audit, verify, inspect, or diagnose any ZBRANO feature, health state, or version, call investigate_zbrano_feature exactly once for that request, even if no failure was reported and general diagnostics are healthy. "
        "Never claim that runtime checks are unavailable before calling this targeted Developer tool. "
        "After it returns, do not call it again in the same turn; use only the returned evidence and GitHub repository tools. "
        "While Developer Mode is active, Workshop Memory, Home Assistant, and non-GitHub MCP tools are unavailable."
    )
    require(text, old_instruction, "Developer automatic investigation instruction")
    text = text.replace(old_instruction, new_instruction, 1)

    old_branch_policy = "Prefer a dedicated development branch for non-trivial changes."
    new_branch_policy = (
        "This repository's release policy is direct updates to main; do not create a branch unless the user explicitly requests one. "
        "Every repository mutation, including a direct-main write, commit, or push, remains separately approval-gated."
    )
    require(text, old_branch_policy, "Developer branch policy")
    text = text.replace(old_branch_policy, new_branch_policy, 1)

    text = text.replace('version="0.12.5"', 'version="0.12.6"')
    text = text.replace('"version": "0.12.5"', '"version": "0.12.6"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    rail_start = text.find('      <aside class="hud-rail right-rail" aria-label="Command deck">')
    rail_end = text.find("      </aside>\n", rail_start)
    if rail_start < 0 or rail_end < 0:
        raise RuntimeError("ZBRANO v0.12.6 patch missing: Command Deck rail")
    text = text[:rail_start] + text[rail_end + len("      </aside>\n"):]

    health = '    <div id="health" class="status">Checking…</div>'
    require(text, health, "online/version display")
    health_stack = '''    <div class="runtime-status-stack">
      <div id="health" class="status">Checking…</div>
      <div id="developer-mode-indicator" class="developer-mode-indicator" role="status" hidden>Developer Mode Active</div>
    </div>'''
    text = text.replace(health, health_stack, 1)

    style_close = text.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.6 patch missing: style close")
    css = r'''
    .hud-layout { grid-template-columns: minmax(0, 1fr); }
    .runtime-status-stack { display: grid; justify-items: end; gap: .32rem; }
    .developer-mode-indicator {
      padding: .28rem .55rem;
      border: 1px solid rgba(255, 200, 87, .5);
      border-radius: 4px;
      color: #ffc857;
      background: rgba(52, 35, 4, .72);
      font-size: .68rem;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
      box-shadow: 0 0 12px rgba(255, 200, 87, .14);
    }
    .developer-mode-indicator[hidden] { display: none; }
    .message.jarvis h2 { font-weight: 650; }
    .message.jarvis h3 { font-weight: 600; }
    .message.jarvis h4 { font-weight: 600; }
    .message.jarvis strong { font-weight: 600; }
    .message.jarvis h2 strong,
    .message.jarvis h3 strong,
    .message.jarvis h4 strong { font-weight: inherit; }
    @media(max-width:620px) { .runtime-status-stack { justify-items: start; } }
'''
    text = text[:style_close] + css + text[style_close:]

    voice_update = "  voiceRailState.textContent = state;"
    require(text, voice_update, "Command Deck voice state dependency")
    text = text.replace(voice_update, "  if (voiceRailState) voiceRailState.textContent = state;", 1)

    session_update = '''  document.getElementById("session-fragment").textContent =
    jarvisChatSessionId.slice(0, 8).toUpperCase();'''
    require(text, session_update, "Command Deck session dependency")
    text = text.replace(
        session_update,
        '''  const sessionFragment = document.getElementById("session-fragment");
  if (sessionFragment) sessionFragment.textContent = jarvisChatSessionId.slice(0, 8).toUpperCase();''',
        1,
    )

    clock_update = '''window.setInterval(() => {
  document.getElementById("hud-clock").textContent = new Date().toLocaleTimeString([], {hour12: false});
}, 1000);'''
    require(text, clock_update, "Command Deck clock dependency")
    text = text.replace(
        clock_update,
        '''const hudClock = document.getElementById("hud-clock");
if (hudClock) window.setInterval(() => {
  hudClock.textContent = new Date().toLocaleTimeString([], {hour12: false});
}, 1000);''',
        1,
    )

    developer_controls = '''  const interfaceStatus = document.getElementById("developer-interface-status");
  if (!tab || !panel || !toggle || !run || !checks) return;'''
    require(text, developer_controls, "Developer controller controls")
    text = text.replace(
        developer_controls,
        '''  const interfaceStatus = document.getElementById("developer-interface-status");
  const modeIndicator = document.getElementById("developer-mode-indicator");
  if (!tab || !panel || !toggle || !run || !checks || !modeIndicator) return;''',
        1,
    )

    sync_toggle = '''    toggle.textContent = enabled ? "Disable Developer Mode" : "Enable Developer Mode";
  }'''
    require(text, sync_toggle, "Developer toggle synchronization")
    text = text.replace(
        sync_toggle,
        '''    toggle.textContent = enabled ? "Disable Developer Mode" : "Enable Developer Mode";
    modeIndicator.hidden = !enabled;
    modeIndicator.textContent = enabled ? "Developer Mode Active" : "";
  }''',
        1,
    )

    controller_end = '''  run.addEventListener("click", runDiagnostics);
  renderInterfaceStatus();
})();'''
    require(text, controller_end, "Developer controller initialization")
    text = text.replace(
        controller_end,
        '''  run.addEventListener("click", runDiagnostics);
  renderInterfaceStatus();
  loadStatus().catch(error => {
    modeIndicator.hidden = true;
    summary.textContent = `Developer status failed: ${error.message || error}`;
  });
})();''',
        1,
    )

    text = text.replace("HUD 0.12.5", "HUD 0.12.6")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required_main = (
        'version="0.12.6"',
        "check, audit, verify, health, version, or broken-feature requests",
        "Never claim that runtime checks are unavailable before calling this targeted Developer tool",
        "direct updates to main; do not create a branch unless the user explicitly requests one",
        "Every repository mutation, including a direct-main write, commit, or push, remains separately approval-gated",
    )
    required_index = (
        'id="developer-mode-indicator"',
        "Developer Mode Active",
        "modeIndicator.hidden = !enabled",
        "loadStatus().catch",
        "HUD 0.12.6",
        "grid-template-columns: minmax(0, 1fr)",
        "if (voiceRailState)",
        "if (sessionFragment)",
        "if (hudClock)",
        ".message.jarvis h2 { font-weight: 650; }",
        ".message.jarvis strong { font-weight: 600; }",
    )
    missing = [marker for marker in required_main if marker not in main]
    missing += [marker for marker in required_index if marker not in index]
    for removed in ("COMMAND DECK", 'aria-label="Command deck"', 'id="session-fragment"', 'id="hud-clock"', 'id="voice-rail-state"'):
        if removed in index:
            missing.append(f"removed marker still present: {removed}")
    if missing:
        raise RuntimeError("ZBRANO v0.12.6 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
