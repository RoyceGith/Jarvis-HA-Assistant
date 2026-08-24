from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "jarvis/app/static"


def load_frontend_source() -> str:
    """Return HTML plus referenced canonical CSS/JS for source-level tests."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    combined = [html]
    assets = re.finditer(r'<script\b([^>]*)>.*?</script>|<link\b([^>]*)>', html, flags=re.I | re.S)
    for match in assets:
        tag = "script" if match.group(1) is not None else "style"
        attrs = match.group(1) if tag == "script" else match.group(2)
        attribute = "src" if tag == "script" else "href"
        location = re.search(rf'\b{attribute}="([^"]+)"', attrs or "", flags=re.I)
        if not location or "://" in location.group(1):
            continue
        source = (STATIC / location.group(1)).read_text(encoding="utf-8")
        identifier = re.search(r'\bid="([^"]+)"', attrs or "", flags=re.I)
        id_text = f' id="{identifier.group(1)}"' if identifier else ""
        combined.append(f"<{tag}{id_text}>\n{source}\n</{tag}>")
    return "\n".join(combined)
