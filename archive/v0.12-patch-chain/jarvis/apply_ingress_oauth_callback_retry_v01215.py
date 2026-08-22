from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.15 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    require(backend, 'version="0.12.14"', "backend version")
    require(frontend, "HUD 0.12.14", "frontend version")
    backend = backend.replace('version="0.12.14"', 'version="0.12.15"')
    backend = backend.replace('"version": "0.12.14"', '"version": "0.12.15"')
    frontend = frontend.replace("HUD 0.12.14", "HUD 0.12.15")

    popup_marker = '''    const popup=window.open("about:blank","zbrano-plugin-oauth","popup,width=680,height=760");
    if(!popup){throw new Error("Allow pop-ups for ZBRANO, then press Connect again")}'''
    require(frontend, popup_marker, "OAuth popup creation")
    popup_replacement = popup_marker + r'''
    // Home Assistant Ingress uses a SameSite session cookie. An OAuth redirect
    // arriving from another site can therefore receive one Supervisor 401 before
    // the browser is back in the Home Assistant site context. Detect only that
    // exact callback failure and repeat it once as a same-site navigation.
    let ingressCallbackRetryUsed=false;
    const ingressCallbackMonitor=window.setInterval(()=>{
      if(popup.closed){window.clearInterval(ingressCallbackMonitor);return;}
      try{
        const popupUrl=new URL(popup.location.href);
        const callbackPath=popupUrl.pathname.endsWith("/api/plugin-oauth/callback");
        const callbackState=popupUrl.searchParams.has("state");
        if(popupUrl.origin!==window.location.origin||!callbackPath||!callbackState)return;
        const pageText=`${popup.document.title||""} ${popup.document.body?.textContent||""}`;
        if(!ingressCallbackRetryUsed&&/\b401\b[\s\S]*unauthorized/i.test(pageText)){
          ingressCallbackRetryUsed=true;
          const status=statusNode();
          if(status)status.textContent="Completing authorization through Home Assistant…";
          popup.location.replace(popupUrl.href);
        }
      }catch(_error){/* The popup is on Cloudflare; cross-origin access is expected. */}
    },250);
    window.setTimeout(()=>window.clearInterval(ingressCallbackMonitor),600000);'''
    frontend = frontend.replace(popup_marker, popup_replacement, 1)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


def verify() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    for marker in ('version="0.12.15"', '"version": "0.12.15"'):
        require(backend, marker, marker)
    for marker in (
        "HUD 0.12.15",
        "ingressCallbackRetryUsed",
        'popupUrl.origin!==window.location.origin',
        'popupUrl.pathname.endsWith("/api/plugin-oauth/callback")',
        'popupUrl.searchParams.has("state")',
        "Completing authorization through Home Assistant…",
    ):
        require(frontend, marker, marker)


if __name__ == "__main__":
    main()
    verify()
