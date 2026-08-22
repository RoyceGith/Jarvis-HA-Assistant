import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.92 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.92 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''    try{
      if(input.value.trim()){await window.zbranoHaHistory?.load();return}
      const live=await api('api/ha/live-events?limit=100');
      let ids=[...new Set((live.events||[]).map(item=>item.entity_id).filter(Boolean))].slice(0,8);
      if(!ids.length){const approved=await api('api/ha/approved');ids=[...new Set([...(approved.control_entities||[]),...(approved.read_entities||[])])].slice(0,8)}
      input.value=ids.join(', ');
      if(ids.length)await window.zbranoHaHistory?.load();else status.textContent='No approved entities are available for History.';
    }catch(error){status.textContent=`History initialization failed: ${error.message||error}`}finally{loading=false}''',
        '''    try{
      const live=await api('api/ha/live-events?limit=100');
      const recent=[...new Set((live.events||[]).map(item=>item.entity_id).filter(Boolean))];
      const selected=input.value.split(',').map(value=>value.trim().toLowerCase()).filter(Boolean);
      let ids=[...new Set([...recent,...selected])].slice(0,8);
      if(!ids.length){const approved=await api('api/ha/approved');ids=[...new Set([...(approved.control_entities||[]),...(approved.read_entities||[])])].slice(0,8)}
      input.value=ids.join(', ');
      if(ids.length){
        await window.zbranoHaHistory?.load();
        status.textContent+=` · live capture ${live.connected?'connected':'disconnected'} · journal ${Number(live.count||0)}`;
      }else status.textContent='No approved entities are available for History.';
    }catch(error){status.textContent=`History initialization failed: ${error.message||error}`}finally{loading=false}''',
        "recent entity History refresh",
    )

    backend = backend.replace('version="0.12.91"', 'version="0.12.92"')
    backend = backend.replace('"version": "0.12.91"', '"version": "0.12.92"')
    frontend = frontend.replace("HUD 0.12.91", "HUD 0.12.92")

    for marker, location in [
        ('version="0.12.92"', backend),
        ('const recent=[...new Set((live.events||[])', frontend),
        ('[...recent,...selected]', frontend),
        ("live capture ${live.connected?'connected':'disconnected'}", frontend),
        ('HUD 0.12.92', frontend),
    ]:
        require(location, marker, marker)
    if 'if(input.value.trim()){await window.zbranoHaHistory?.load();return}' in frontend:
        raise RuntimeError("ZBRANO v0.12.92 still contains the stale History selection early return")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
