import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.48 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.48 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}", "Content-Type": "application/json"}\n    message = request.message.strip()\n',
        '    message = request.message.strip()\n',
        "obsolete notification REST headers",
    )

    old_delivery = '''    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(f"{HA_API_BASE}/services/notify/send_message", headers=headers, json=body)
        if response.is_error:
            raise RuntimeError(f"Home Assistant returned HTTP {response.status_code}: {response.text[:300]}")
        delivery = _notification_delivery(
            data, target=request.target, severity=request.severity,
            title=title, status="delivered",
            detail=(
                "Sent through telegram via Home Assistant using verified exact-message compatibility"
                if channel["platform"] == "telegram"
                else f"Sent through {channel['platform']} via Home Assistant"
            ),
        )
        _notification_save(data)
        return {"delivered": True, "delivery": delivery}
    except (httpx.HTTPError, RuntimeError) as exc:
        delivery = _notification_delivery(
            data, target=request.target, severity=request.severity,
            title=title, status="failed", detail=str(exc),
        )
        _notification_save(data)
        raise HTTPException(status_code=502, detail=f"Notification delivery failed: {exc}") from exc
'''
    new_delivery = '''    try:
        # Use Home Assistant's WebSocket action path. The REST endpoint can
        # return HTTP 500 after Telegram has already accepted the message,
        # producing a false failure and risking duplicate retries.
        await ha_ws.call_service("notify", "send_message", body)
        delivery = _notification_delivery(
            data, target=request.target, severity=request.severity,
            title=title, status="delivered",
            detail=(
                "Sent through telegram via Home Assistant WebSocket"
                if channel["platform"] == "telegram"
                else f"Sent through {channel['platform']} via Home Assistant WebSocket"
            ),
        )
        _notification_save(data)
        return {"delivered": True, "delivery": delivery}
    except (RuntimeError, OSError, asyncio.TimeoutError, ConnectionClosed) as exc:
        delivery = _notification_delivery(
            data, target=request.target, severity=request.severity,
            title=title, status="failed", detail=str(exc),
        )
        _notification_save(data)
        raise HTTPException(status_code=502, detail=f"Notification delivery failed: {exc}") from exc
'''
    backend = replace_once(backend, old_delivery, new_delivery, "notification WebSocket delivery")

    activity_api = '''@app.get("/api/notifications/activity")
async def read_notification_activity() -> dict[str, Any]:
    deliveries = notification_store().get("deliveries") or []
    newest = deliveries[0] if deliveries else {}
    return {
        "latest_id": str(newest.get("id") or ""),
        "latest_at": float(newest.get("created_at") or 0.0),
        "count": len(deliveries),
    }


'''
    backend = replace_once(
        backend,
        '@app.delete("/api/notifications/deliveries")\n',
        activity_api + '@app.delete("/api/notifications/deliveries")\n',
        "notification activity summary API",
    )

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.48 patch could not locate stylesheet")
    indicator_css = '''
    /* Unseen content indicator shared by primary and nested tabs. */
    .zbrano-tab-unseen { position:relative; }
    .zbrano-tab-unseen::after {
      content:"";
      position:absolute;
      top:.28rem;
      right:.28rem;
      width:.48rem;
      height:.48rem;
      border-radius:50%;
      background:#f39a32;
      box-shadow:0 0 0 2px var(--surface-strong), 0 0 8px rgba(243,154,50,.55);
      pointer-events:none;
    }
'''
    frontend = frontend[:style_close] + indicator_css + frontend[style_close:]

    body_close = frontend.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.48 patch could not locate body close")
    activity_runtime = r'''
<script id="zbrano-v01248-tab-activity">
(() => {
  let armed = false;
  const bindings = [];

  function isViewed(button, panel) {
    const selected = button.classList.contains("active") || button.getAttribute("aria-selected") === "true";
    return selected && !panel.hidden && !panel.closest(".hidden");
  }

  function mark(button) {
    if (button.classList.contains("zbrano-tab-unseen")) return;
    button.classList.add("zbrano-tab-unseen");
    if (!button.hasAttribute("aria-label")) {
      button.dataset.zbranoActivityLabel = "generated";
      button.setAttribute("aria-label", `${button.textContent.trim()} · new activity`);
    }
  }

  function clear(button) {
    button.classList.remove("zbrano-tab-unseen");
    if (button.dataset.zbranoActivityLabel === "generated") {
      button.removeAttribute("aria-label");
      delete button.dataset.zbranoActivityLabel;
    }
  }

  function markIfUnseen(button) {
    const binding = bindings.find(item => item.button === button);
    if (binding && !isViewed(binding.button, binding.panel)) mark(binding.button);
  }

  function bind(button, panel) {
    if (!button || !panel || bindings.some(item => item.button === button)) return;
    const observer = new MutationObserver(changes => {
      if (!armed || isViewed(button, panel)) return;
      if (changes.some(change => change.type === "characterData" || change.addedNodes.length || change.removedNodes.length)) mark(button);
    });
    observer.observe(panel, {subtree:true, childList:true, characterData:true});
    button.addEventListener("click", () => requestAnimationFrame(() => clear(button)));
    bindings.push({button, panel, observer});
  }

  for (const name of ["chat", "files", "plugins", "entities", "automations", "settings", "developer"]) {
    bind(document.getElementById(`${name}-tab`), document.getElementById(`${name}-panel`));
  }
  for (const button of document.querySelectorAll("[data-auto-view]")) {
    bind(button, document.querySelector(`[data-auto-panel="${CSS.escape(button.dataset.autoView)}"]`));
  }
  for (const button of document.querySelectorAll("[data-notification-view]")) {
    bind(button, document.querySelector(`[data-notification-panel="${CSS.escape(button.dataset.notificationView)}"]`));
  }
  for (const button of document.querySelectorAll(".settings-category-tab[data-settings-target]")) {
    bind(button, document.querySelector(`[data-settings-category="${CSS.escape(button.dataset.settingsTarget)}"]`));
  }
  for (const button of document.querySelectorAll("#plugins-installed-tab, #plugins-browse-tab")) {
    bind(button, document.getElementById(button.getAttribute("aria-controls")));
  }

  let notificationSignature = null;
  async function checkNotificationActivity() {
    try {
      const response = await fetch("api/notifications/activity", {cache:"no-store"});
      if (!response.ok) return;
      const activity = await response.json();
      const signature = `${activity.latest_id || ""}:${activity.count || 0}`;
      if (notificationSignature !== null && signature !== notificationSignature) {
        markIfUnseen(document.getElementById("automations-tab"));
        markIfUnseen(document.querySelector('[data-auto-view="notifications"]'));
        markIfUnseen(document.querySelector('[data-notification-view="logs"]'));
      }
      notificationSignature = signature;
    } catch (_) {}
  }

  window.zbranoMarkTabChanged = tabId => markIfUnseen(document.getElementById(tabId));
  window.zbranoClearTabChanged = tabId => clear(document.getElementById(tabId));
  checkNotificationActivity();
  setInterval(checkNotificationActivity, 15000);
  setTimeout(() => { armed = true; }, 2500);
})();
</script>
'''
    frontend = frontend[:body_close] + activity_runtime + frontend[body_close:]

    backend = backend.replace('version="0.12.47"', 'version="0.12.48"')
    backend = backend.replace('"version": "0.12.47"', '"version": "0.12.48"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.47"', '"X-ZBRANO-Frontend-Version": "0.12.48"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.47"', '"name": "ZBRANO Developer Mode", "version": "0.12.48"')
    frontend = frontend.replace("HUD 0.12.47", "HUD 0.12.48")

    required_backend = (
        'version="0.12.48"',
        'await ha_ws.call_service("notify", "send_message", body)',
        "Home Assistant WebSocket",
        '@app.get("/api/notifications/activity")',
    )
    for marker in required_backend:
        require(backend, marker, marker)
    notification_function = backend.split('async def test_notification_channel(', 1)[1].split('\n\n@app.get("/api/settings")', 1)[0]
    if 'HA_API_BASE}/services/notify/send_message' in notification_function or "httpx.AsyncClient" in notification_function:
        raise RuntimeError("ZBRANO v0.12.48 notification delivery still uses the REST endpoint")

    required_frontend = (
        "HUD 0.12.48",
        'id="zbrano-v01248-tab-activity"',
        "zbrano-tab-unseen",
        "MutationObserver",
        "zbranoMarkTabChanged",
        "checkNotificationActivity",
        'background:#f39a32',
    )
    for marker in required_frontend:
        require(frontend, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
