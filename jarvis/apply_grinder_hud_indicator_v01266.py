from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.66 expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''      <div id="developer-mode-indicator" class="developer-mode-indicator" role="status" hidden>Developer Mode Active</div>
      <div id="health" class="status">''',
        '''      <div id="developer-mode-indicator" class="developer-mode-indicator" role="status" hidden>Developer Mode Active</div>
      <div id="grinder-connection-indicator" class="grinder-connection-indicator is-checking" role="status" aria-live="polite" title="Checking grinder diagnostic connection">
        <span class="grinder-connection-dot" aria-hidden="true"></span>
        <span class="grinder-connection-label">Grinder Checking</span>
      </div>
      <div id="health" class="status">''',
        "grinder HUD indicator",
    )

    styles = r'''

    .grinder-connection-indicator {
      --grinder-indicator-color: #8da19e;
      display: inline-flex;
      align-items: center;
      gap: .42rem;
      min-height: 1.45rem;
      padding: .18rem .54rem;
      border: 1px solid color-mix(in srgb, var(--grinder-indicator-color) 48%, transparent);
      border-radius: 999px;
      background: color-mix(in srgb, var(--grinder-indicator-color) 9%, transparent);
      color: var(--grinder-indicator-color);
      font-size: .68rem;
      font-weight: 650;
      letter-spacing: .035em;
      line-height: 1;
      white-space: nowrap;
    }
    .grinder-connection-dot {
      width: .48rem;
      height: .48rem;
      flex: 0 0 .48rem;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 .65rem color-mix(in srgb, currentColor 56%, transparent);
    }
    .grinder-connection-indicator.is-online { --grinder-indicator-color: #24cfa0; }
    .grinder-connection-indicator.is-waiting { --grinder-indicator-color: #d7a643; }
    .grinder-connection-indicator.is-offline { --grinder-indicator-color: #ef765f; }
    .grinder-connection-indicator.is-disabled { --grinder-indicator-color: #84908f; opacity: .72; }
    .grinder-connection-indicator.is-checking .grinder-connection-dot {
      animation: grinder-indicator-pulse 1.4s ease-in-out infinite;
    }
    @keyframes grinder-indicator-pulse { 50% { opacity: .35; transform: scale(.72); } }
    @media(max-width:620px) {
      .grinder-connection-indicator { padding: .16rem .42rem; font-size: .59rem; }
    }
'''
    frontend = replace_once(
        frontend,
        "    .runtime-status-stack { display: grid; justify-items: end; gap: .32rem; }",
        "    .runtime-status-stack { display: grid; justify-items: end; gap: .32rem; }" + styles,
        "grinder HUD styles",
    )

    controller = r'''

<script id="zbrano-v01266-grinder-hud-indicator">
(() => {
  const indicator = document.getElementById("grinder-connection-indicator");
  const label = indicator?.querySelector(".grinder-connection-label");
  if (!indicator || !label) return;
  const stateClasses = ["is-checking", "is-online", "is-waiting", "is-offline", "is-disabled"];
  let requestActive = false;

  function render(state, text, title) {
    indicator.classList.remove(...stateClasses);
    indicator.classList.add(`is-${state}`);
    label.textContent = text;
    indicator.title = title || text;
  }

  async function refreshGrinderIndicator() {
    if (requestActive) return;
    requestActive = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 4000);
    try {
      const response = await fetch("api/grinder-monitor/status", {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const devices = Array.isArray(data.devices) ? data.devices : [];
      const online = devices.filter(device => device?.online === true);
      if (!data.enabled) {
        render("disabled", "Grinder Monitor Off", "Grinder diagnostic monitoring is disabled");
      } else if (!data.connected) {
        render("offline", "Grinder Broker Offline", data.last_error || "ZBRANO cannot reach the grinder MQTT broker");
      } else if (online.length) {
        const device = online[0];
        const age = Number(device.heartbeat_age_seconds);
        const ageText = Number.isFinite(age) ? ` · heartbeat ${age.toFixed(1)}s` : "";
        render("online", "Grinder Online", `${device.device_id || "Grinder"} connected${ageText}`);
      } else if (devices.length) {
        render("offline", "Grinder Offline", "The broker is connected, but no grinder heartbeat is active");
      } else {
        render("waiting", "Grinder Waiting", "The broker is connected and waiting for grinder telemetry");
      }
    } catch (error) {
      render("offline", "Grinder Status Unavailable", error?.name === "AbortError" ? "Grinder status check timed out" : "Could not read grinder diagnostic status");
    } finally {
      window.clearTimeout(timeout);
      requestActive = false;
    }
  }

  refreshGrinderIndicator();
  window.setInterval(() => {
    if (!document.hidden) refreshGrinderIndicator();
  }, 5000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refreshGrinderIndicator();
  });
})();
</script>
'''
    frontend = replace_once(
        frontend,
        "\n</body>\n</html>",
        controller + "\n</body>\n</html>",
        "grinder HUD controller",
    )

    backend = backend.replace('version="0.12.65"', 'version="0.12.66"')
    backend = backend.replace('"version": "0.12.65"', '"version": "0.12.66"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.65"', '"X-ZBRANO-Frontend-Version": "0.12.66"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.65"', '"name": "ZBRANO Developer Mode", "version": "0.12.66"')
    frontend = frontend.replace("HUD 0.12.65", "HUD 0.12.66")

    required_frontend = (
        'id="grinder-connection-indicator"',
        'fetch("api/grinder-monitor/status"',
        '"Grinder Online"',
        '"Grinder Broker Offline"',
        '"Grinder Waiting"',
        "HUD 0.12.66",
    )
    missing = [marker for marker in required_frontend if marker not in frontend]
    if missing or 'version="0.12.66"' not in backend:
        raise RuntimeError("ZBRANO v0.12.66 verification failed: " + ", ".join(missing))

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
