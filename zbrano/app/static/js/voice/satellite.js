(function () {
  const pairButton = document.getElementById("assist-bridge-pair");
  if (!pairButton) return;
  const state = document.getElementById("assist-bridge-state");
  const message = document.getElementById("assist-bridge-message");
  const secret = document.getElementById("assist-bridge-secret");
  const token = document.getElementById("assist-bridge-token");
  const address = document.getElementById("assist-bridge-url");
  const copyButton = document.getElementById("assist-bridge-copy");

  address.value = `http://${window.location.hostname}:8099`;

  function renderStatus(payload = {}) {
    state.dataset.state = payload.paired ? "ready" : "off";
    state.textContent = payload.paired ? "PAIRED" : "NOT PAIRED";
    pairButton.textContent = payload.paired ? "Generate new key" : "Generate pairing key";
  }

  async function loadStatus() {
    try {
      const response = await fetch("api/assist/bridge", {cache:"no-store"});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
      renderStatus(payload);
    } catch (error) {
      message.textContent = `Could not check satellite pairing: ${error.message || error}`;
    }
  }

  pairButton.addEventListener("click", async () => {
    if (state.dataset.state === "ready" && !window.confirm("Generate a new key? The existing ZBRANO integration must be reconfigured with it.")) return;
    pairButton.disabled = true;
    message.textContent = "Creating a new private key...";
    try {
      const response = await fetch("api/assist/bridge/pair", {method:"POST"});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
      token.value = payload.pairing_token || "";
      secret.hidden = false;
      renderStatus(payload);
      message.textContent = "Key ready. Add the ZBRANO integration, then choose it in an Assist pipeline.";
    } catch (error) {
      message.textContent = `Could not create pairing key: ${error.message || error}`;
    } finally {
      pairButton.disabled = false;
    }
  });

  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(token.value);
      copyButton.textContent = "Copied";
      window.setTimeout(() => { copyButton.textContent = "Copy key"; }, 1400);
    } catch {
      token.select();
      message.textContent = "Copy the selected key manually.";
    }
  });

  document.querySelector('[data-settings-target="voice"]')?.addEventListener("click", loadStatus);
  loadStatus();
})();
