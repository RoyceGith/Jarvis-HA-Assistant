import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.45 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    require(frontend, 'id="automations-panel"', "Automations panel")
    require(frontend, 'data-auto-panel="notifications"', "Notifications panel")
    require(frontend, 'id="notification-watchlist"', "Notification Watchlist")

    notification_open = '      <section class="autonomy-view hidden" data-auto-panel="notifications">\n'
    notification_tabs = r'''      <section class="autonomy-view hidden" data-auto-panel="notifications">
        <div class="notification-subtabs" role="tablist" aria-label="Notification workspace">
          <button type="button" class="active" data-notification-view="center" role="tab" aria-selected="true">Notification Center</button>
          <button type="button" data-notification-view="watchlist" role="tab" aria-selected="false">Watchlist</button>
        </div>
        <div data-notification-panel="center">
'''
    if frontend.count(notification_open) != 1:
        raise RuntimeError("ZBRANO v0.12.45 patch expected one Notifications opening")
    frontend = frontend.replace(notification_open, notification_tabs, 1)

    watchlist_card = r'''        <article class="autonomy-card notification-watchlist-card">
          <div class="autonomy-card-head"><div><h3>Notification Watchlist</h3><p>Notification-only automations created from requests such as “notify me when the workshop door opens.”</p></div><span id="notification-watch-count" class="notification-platform">0 watches</span></div>
          <div id="notification-watchlist" class="notification-watch-list"><div class="autonomy-empty">No notification watches configured.</div></div>
          <p class="muted">Create watches naturally in Chat. An explicit request arms the rule; matching events can notify automatically without another approval.</p>
        </article>
'''
    if frontend.count(watchlist_card) != 1:
        raise RuntimeError("ZBRANO v0.12.45 patch expected one Watchlist card")
    frontend = frontend.replace(watchlist_card, "", 1)

    notification_close = '        </div>\n      </section>\n\n      <section class="autonomy-view hidden" data-auto-panel="activity">\n'
    notification_reorganized = '''        </div>
        </div>
        <div class="hidden" data-notification-panel="watchlist">
''' + watchlist_card + '''        </div>
      </section>
      <section class="autonomy-view hidden" data-auto-panel="activity">
'''
    if frontend.count(notification_close) != 1:
        raise RuntimeError("ZBRANO v0.12.45 patch expected one Notifications closing")
    frontend = frontend.replace(notification_close, notification_reorganized, 1)

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.45 patch could not locate stylesheet")
    css = r'''
    /* v0.12.45: every Automations view, including Notifications, owns a viewport scroll container. */
    #automations-panel {
      min-height:0;
      overflow-x:hidden;
      overflow-y:auto;
      overscroll-behavior:contain;
      scrollbar-gutter:stable;
      scrollbar-color:var(--cyan-dim) transparent;
      -webkit-overflow-scrolling:touch;
    }
    #automations-panel .autonomy-shell { min-height:max-content; padding-bottom:1rem; }
    #automations-panel .autonomy-view { min-width:0; }
    .notification-subtabs { display:flex; gap:.4rem; flex-wrap:wrap; margin-bottom:.75rem; border-bottom:1px solid var(--line); padding-bottom:.55rem; }
    .notification-subtabs button.active { border-color:var(--cyan); color:var(--cyan); }
    [data-notification-panel].hidden { display:none; }
    [data-notification-panel="watchlist"] .notification-watchlist-card { margin-top:0; }
    @media(max-width:700px) {
      #automations-panel { scrollbar-gutter:auto; touch-action:pan-y; }
      #automations-panel .autonomy-shell { padding-bottom:1.5rem; }
    }
'''
    frontend = frontend[:style_close] + css + frontend[style_close:]

    watch_renderer = "  function renderWatchlist() {\n"
    notification_view_runtime = r'''  function showNotificationView(name) {
    for (const button of panel.querySelectorAll("[data-notification-view]")) {
      const active = button.dataset.notificationView === name;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    }
    for (const view of panel.querySelectorAll("[data-notification-panel]")) {
      view.classList.toggle("hidden", view.dataset.notificationPanel !== name);
    }
  }

  panel.querySelector(".notification-subtabs")?.addEventListener("click", event => {
    const button = event.target.closest("[data-notification-view]");
    if (button) showNotificationView(button.dataset.notificationView);
  });

'''
    if frontend.count(watch_renderer) != 1:
        raise RuntimeError("ZBRANO v0.12.45 patch expected one Watchlist renderer")
    frontend = frontend.replace(watch_renderer, notification_view_runtime + watch_renderer, 1)
    old_export = "  window.zbranoNotificationCenter = {load};\n"
    new_export = "  window.zbranoNotificationCenter = {load, showView:showNotificationView};\n"
    if frontend.count(old_export) != 1:
        raise RuntimeError("ZBRANO v0.12.45 patch expected one Notification Center export")
    frontend = frontend.replace(old_export, new_export, 1)
    old_library_route = 'window.zbranoNotificationCenter?.load();return}\n'
    new_library_route = 'window.zbranoNotificationCenter?.showView("watchlist");window.zbranoNotificationCenter?.load();return}\n'
    if frontend.count(old_library_route) != 1:
        raise RuntimeError("ZBRANO v0.12.45 patch expected one Automation Library Watchlist route")
    frontend = frontend.replace(old_library_route, new_library_route, 1)

    backend = backend.replace('version="0.12.44"', 'version="0.12.45"')
    backend = backend.replace('"version": "0.12.44"', '"version": "0.12.45"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.44"', '"X-ZBRANO-Frontend-Version": "0.12.45"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.44"', '"name": "ZBRANO Developer Mode", "version": "0.12.45"')
    frontend = frontend.replace("HUD 0.12.44", "HUD 0.12.45")

    required_backend = ('version="0.12.45"', '"X-ZBRANO-Frontend-Version": "0.12.45"')
    required_frontend = (
        "HUD 0.12.45",
        "#automations-panel {",
        "overflow-y:auto",
        "-webkit-overflow-scrolling:touch",
        "touch-action:pan-y",
        'data-notification-view="center"',
        'data-notification-view="watchlist"',
        'data-notification-panel="watchlist"',
        "showNotificationView",
    )
    for marker in required_backend:
        require(backend, marker, marker)
    for marker in required_frontend:
        require(frontend, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
