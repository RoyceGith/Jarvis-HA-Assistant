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
