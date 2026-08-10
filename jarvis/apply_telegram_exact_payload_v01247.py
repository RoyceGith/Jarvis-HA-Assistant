import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.47 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.47 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    old = '''        # Preserve the visible heading while using the proven message-only shape.
        body = {
            "entity_id": request.target,
            "message": f"{title}\\n{message}" if title else message,
        }
'''
    new = '''        # Match the Home Assistant action that was verified against this bot:
        # send only entity_id and the unmodified message. The title remains in
        # ZBRANO Delivery History but is not part of the Telegram service call.
        body = {
            "entity_id": request.target,
            "message": message,
        }
'''
    backend = replace_once(backend, old, new, "exact Telegram message payload")
    backend = replace_once(
        backend,
        '"Sent through telegram via Home Assistant using message-only compatibility"',
        '"Sent through telegram via Home Assistant using verified exact-message compatibility"',
        "Telegram exact-message evidence",
    )

    notification_delete_api = '''class NotificationDeliveryDeleteRequest(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)


@app.delete("/api/notifications/deliveries")
async def delete_notification_deliveries(request: NotificationDeliveryDeleteRequest) -> dict[str, Any]:
    requested = {item.strip() for item in request.ids if item.strip()}
    if not requested:
        raise HTTPException(status_code=400, detail="Select at least one delivery log")
    data = notification_store()
    original = list(data.get("deliveries") or [])
    data["deliveries"] = [item for item in original if str(item.get("id") or "") not in requested]
    deleted = len(original) - len(data["deliveries"])
    if deleted:
        _notification_save(data)
    return {"deleted": deleted, "remaining": len(data["deliveries"])}


'''
    backend = replace_once(
        backend,
        '@app.get("/api/notifications")\n',
        notification_delete_api + '@app.get("/api/notifications")\n',
        "notification delivery deletion API",
    )

    tabs_marker = '''          <button type="button" data-notification-view="watchlist" role="tab" aria-selected="false">Watchlist</button>
'''
    tabs_replacement = tabs_marker + '''          <button type="button" data-notification-view="logs" role="tab" aria-selected="false">Delivery Logs</button>
'''
    frontend = replace_once(frontend, tabs_marker, tabs_replacement, "Delivery Logs tab")

    delivery_card = '''          <article class="autonomy-card">
            <div class="autonomy-card-head"><div><h3>Delivery Log</h3><p>Recent delivery outcomes without storing message bodies or credentials.</p></div></div>
            <div id="notification-deliveries" class="notification-delivery-list"><div class="autonomy-empty">No deliveries recorded.</div></div>
          </article>
'''
    frontend = replace_once(frontend, delivery_card, "", "Delivery Log card removal")
    watchlist_close = '''        </article>
        </div>
      </section>
      <section class="autonomy-view hidden" data-auto-panel="activity">
'''
    logs_panel = '''        </article>
        </div>
        <div class="hidden" data-notification-panel="logs">
          <article class="autonomy-card notification-delivery-log-card">
            <div class="autonomy-card-head"><div><h3>Delivery Logs</h3><p>Recent delivery outcomes without storing message bodies or credentials.</p></div></div>
            <div class="notification-log-toolbar">
              <label><input id="notification-log-select-all" type="checkbox"> Select all</label>
              <span id="notification-log-selection-count" class="muted">0 selected</span>
              <button id="notification-log-delete" type="button" disabled>Delete selected</button>
            </div>
            <div id="notification-deliveries" class="notification-delivery-list"><div class="autonomy-empty">No deliveries recorded.</div></div>
          </article>
        </div>
      </section>
      <section class="autonomy-view hidden" data-auto-panel="activity">
'''
    frontend = replace_once(frontend, watchlist_close, logs_panel, "Delivery Logs panel")

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.47 patch could not locate stylesheet")
    frontend = frontend[:style_close] + '''
    [data-notification-panel="logs"] .notification-delivery-log-card { margin-top:0; }
    .notification-log-toolbar { display:flex; align-items:center; gap:.6rem; flex-wrap:wrap; margin-top:.65rem; }
    .notification-log-toolbar label { display:flex; align-items:center; gap:.35rem; }
    .notification-log-toolbar input, .notification-delivery-select { width:auto; flex:0 0 auto; }
    .notification-log-toolbar button { margin-left:auto; }
    .notification-delivery-title { display:flex; align-items:center; gap:.5rem; min-width:0; }
    @media(max-width:600px) { .notification-log-toolbar button { margin-left:0; } }
''' + frontend[style_close:]

    frontend = replace_once(
        frontend,
        '  let state = {settings:{}, channels:[], watches:[], deliveries:[]};\n',
        '  let state = {settings:{}, channels:[], watches:[], deliveries:[]};\n  const selectedDeliveries = new Set();\n',
        "delivery selection state",
    )

    old_render = '''  function renderDeliveries() {
    const root = $("notification-deliveries"); root.replaceChildren();
    for (const delivery of state.deliveries || []) {
      const row = document.createElement("div"); row.className = "notification-delivery"; row.dataset.status = delivery.status;
      const head = document.createElement("div"); head.className = "notification-delivery-head";
      const title = document.createElement("strong"); title.textContent = delivery.title || "Notification";
      const status = document.createElement("span"); status.className = "notification-platform"; status.textContent = delivery.status;
      const detail = document.createElement("small"); detail.textContent = `${delivery.target} · ${delivery.severity} · ${new Date(delivery.created_at * 1000).toLocaleString()}`;
      const evidence = document.createElement("small"); evidence.textContent = delivery.detail || "";
      head.append(title, status); row.append(head, detail, evidence); root.appendChild(row);
    }
    if (!state.deliveries?.length) root.innerHTML = '<div class="autonomy-empty">No deliveries recorded.</div>';
  }
'''
    new_render = '''  function updateDeliverySelection() {
    const available = new Set((state.deliveries || []).map(item => item.id));
    for (const id of [...selectedDeliveries]) if (!available.has(id)) selectedDeliveries.delete(id);
    const count = selectedDeliveries.size;
    const all = (state.deliveries || []).length;
    $("notification-log-selection-count").textContent = `${count} selected`;
    $("notification-log-delete").disabled = count === 0;
    const selectAll = $("notification-log-select-all");
    selectAll.checked = all > 0 && count === all;
    selectAll.indeterminate = count > 0 && count < all;
  }

  function renderDeliveries() {
    const root = $("notification-deliveries"); root.replaceChildren();
    for (const delivery of state.deliveries || []) {
      const row = document.createElement("div"); row.className = "notification-delivery"; row.dataset.status = delivery.status;
      const head = document.createElement("div"); head.className = "notification-delivery-head";
      const titleGroup = document.createElement("label"); titleGroup.className = "notification-delivery-title";
      const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.className = "notification-delivery-select"; checkbox.checked = selectedDeliveries.has(delivery.id); checkbox.setAttribute("aria-label", `Select ${delivery.title || "notification"}`);
      checkbox.addEventListener("change", () => { checkbox.checked ? selectedDeliveries.add(delivery.id) : selectedDeliveries.delete(delivery.id); updateDeliverySelection(); });
      const title = document.createElement("strong"); title.textContent = delivery.title || "Notification";
      const status = document.createElement("span"); status.className = "notification-platform"; status.textContent = delivery.status;
      const detail = document.createElement("small"); detail.textContent = `${delivery.target} · ${delivery.severity} · ${new Date(delivery.created_at * 1000).toLocaleString()}`;
      const evidence = document.createElement("small"); evidence.textContent = delivery.detail || "";
      titleGroup.append(checkbox, title); head.append(titleGroup, status); row.append(head, detail, evidence); root.appendChild(row);
    }
    if (!state.deliveries?.length) root.innerHTML = '<div class="autonomy-empty">No deliveries recorded.</div>';
    updateDeliverySelection();
  }
'''
    frontend = replace_once(frontend, old_render, new_render, "selectable delivery log renderer")

    runtime_close = '''  tab.addEventListener("click", load);
  $("notification-refresh").addEventListener("click", load);
  window.zbranoNotificationCenter = {load, showView:showNotificationView};
'''
    selection_handlers = '''  $("notification-log-select-all").addEventListener("change", event => {
    selectedDeliveries.clear();
    if (event.target.checked) for (const delivery of state.deliveries || []) selectedDeliveries.add(delivery.id);
    renderDeliveries();
  });

  $("notification-log-delete").addEventListener("click", async () => {
    const ids = [...selectedDeliveries];
    if (!ids.length) return;
    const button = $("notification-log-delete"); button.disabled = true; button.textContent = "Deleting…";
    try {
      await api("api/notifications/deliveries", {method:"DELETE", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ids})});
      selectedDeliveries.clear(); await load();
    } catch (error) {
      $("notification-log-selection-count").textContent = `Delete failed: ${error.message || error}`;
    } finally { button.textContent = "Delete selected"; updateDeliverySelection(); }
  });

''' + runtime_close
    frontend = replace_once(frontend, runtime_close, selection_handlers, "delivery selection handlers")

    backend = backend.replace('version="0.12.46"', 'version="0.12.47"')
    backend = backend.replace('"version": "0.12.46"', '"version": "0.12.47"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.46"', '"X-ZBRANO-Frontend-Version": "0.12.47"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.46"', '"name": "ZBRANO Developer Mode", "version": "0.12.47"')
    frontend = frontend.replace("HUD 0.12.46", "HUD 0.12.47")

    required_backend = (
        'version="0.12.47"',
        'if channel["platform"] == "telegram":',
        '"message": message',
        "verified exact-message compatibility",
    )
    for marker in required_backend:
        require(backend, marker, marker)
    required_frontend = (
        "HUD 0.12.47",
        'data-notification-view="center"',
        'data-notification-view="watchlist"',
        'data-notification-view="logs"',
        'data-notification-panel="logs"',
        "Delivery Logs",
        'id="notification-log-select-all"',
        'id="notification-log-delete"',
    )
    for marker in required_frontend:
        require(frontend, marker, marker)

    for marker in ('@app.delete("/api/notifications/deliveries")', "NotificationDeliveryDeleteRequest", '"deleted": deleted'):
        require(backend, marker, marker)

    telegram_branch = backend.split('if channel["platform"] == "telegram":', 1)[1].split("    else:", 1)[0]
    if '"title":' in telegram_branch or "f\"{title}" in telegram_branch:
        raise RuntimeError("ZBRANO v0.12.47 Telegram branch still modifies or sends title")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
