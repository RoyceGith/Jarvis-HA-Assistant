from pathlib import Path

ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.19 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.18"', 'version="0.11.19"', 1)
    text = text.replace('"version": "0.11.18"', '"version": "0.11.19"', 1)
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    broken_start = r'\n(()=>{const tab=document.getElementById("files-tab")'
    fixed_start = '(()=>{const tab=document.getElementById("files-tab")'
    require(text, broken_start, "malformed shared-files script start")
    text = text.replace(broken_start, fixed_start, 1)

    broken_end = r'})();\n</script>'
    fixed_end = '})();\n</script>'
    require(text, broken_end, "malformed shared-files script end")
    text = text.replace(broken_end, fixed_end, 1)

    old_ws = r'''const W=window.WebSocket;window.WebSocket=function(...a){let w=new W(...a),send=w.send.bind(w);w.send=d=>{try{let p=JSON.parse(d);if(p?.session_id&&typeof p.message==="string"&&!p.type){p.attachment_ids=pending.map(x=>x.file_id);pending=[];draw();return send(JSON.stringify(p))}}catch{}return send(d)};return w};window.WebSocket.prototype=W.prototype'''
    require(text, old_ws, "v0.11.18 global WebSocket override")
    text = text.replace(
        old_ws,
        'window.zbranoAttachmentIds=()=>pending.map(x=>x.file_id);'
        'window.zbranoClearPendingAttachments=()=>{pending=[];draw()};',
        1,
    )

    old_send = 'socket.send(JSON.stringify({session_id: jarvisChatSessionId, message}));'
    new_send = '''const attachmentIds =
      typeof window.zbranoAttachmentIds === "function"
        ? window.zbranoAttachmentIds()
        : [];
    socket.send(JSON.stringify({
      session_id: jarvisChatSessionId,
      message,
      attachment_ids: attachmentIds,
    }));
    if (typeof window.zbranoClearPendingAttachments === "function") {
      window.zbranoClearPendingAttachments();
    }'''
    require(text, old_send, "native chat WebSocket send")
    text = text.replace(old_send, new_send, 1)

    picker = '<input id="attachment-input" type="file" multiple hidden>'
    require(text, picker, "native file picker")
    text = text.replace(
        picker,
        '<input id="attachment-input" type="file" multiple hidden '
        'title="Choose files from this device">',
        1,
    )

    text = text.replace("HUD 0.11.18", "HUD 0.11.19", 1)
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required = (
        'version="0.11.19"',
        'attachment_ids: attachmentIds',
        'window.zbranoAttachmentIds',
        'window.zbranoClearPendingAttachments',
        'title="Choose files from this device"',
        'HUD 0.11.19',
    )
    missing = [m for m in required if m not in main and m not in index]
    if 'window.WebSocket=function' in index:
        missing.append("global WebSocket override removed")
    if r'\n(()=>{const tab=document.getElementById("files-tab")' in index:
        missing.append("literal backslash-n removed")
    if missing:
        raise RuntimeError("Jarvis v0.11.19 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
