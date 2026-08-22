from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.5 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    card_marker = 'function catalogCard(item){'
    require(text, card_marker, "catalogCard")

    helper = r'''function catalogEsc(value){
  return String(value??"")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#39;");
}

'''
    text = text.replace(card_marker, helper + card_marker, 1)

    card_start = text.find(card_marker)
    card_end = text.find("\n}\n\nasync function loadCatalog", card_start)
    if card_start < 0 or card_end < 0:
        raise RuntimeError("Jarvis v0.11.5 patch missing: catalogCard boundaries")

    card = text[card_start:card_end]
    if "esc(" not in card:
        raise RuntimeError("Jarvis v0.11.5 patch missing: catalog esc dependency")
    card = card.replace("esc(", "catalogEsc(")
    text = text[:card_start] + card + text[card_end:]

    text = text.replace("HUD 0.11.4", "HUD 0.11.5")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.4"', 'version="0.11.5"')
    text = text.replace('"version": "0.11.4"', '"version": "0.11.5"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")

    missing = []
    for marker in (
        "function catalogEsc(value)",
        "catalogEsc(item.title||item.name)",
        "catalogEsc(item.description||",
        "catalogEsc(item.id)",
    ):
        if marker not in index:
            missing.append(marker)

    card_start = index.find("function catalogCard(item){")
    card_end = index.find("\n}\n\nasync function loadCatalog", card_start)
    card = index[card_start:card_end]
    if "esc(" in card:
        missing.append("catalogCard still depends on esc")
    if "0.11.5" not in main:
        missing.append("backend version 0.11.5")

    if missing:
        raise RuntimeError(
            "Jarvis v0.11.5 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
