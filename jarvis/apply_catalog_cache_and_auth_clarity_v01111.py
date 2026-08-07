from pathlib import Path

ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.11 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    old_cache = '''    if not force:
        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True, None'''
    new_cache = '''    if not force:
        cached = _catalog_cache_read()
        if cached is not None and len(cached) > len(FEATURED_REMOTE_PLUGINS):
            return cached, True, None'''
    require(text, old_cache, "catalog cache guard")
    text = text.replace(old_cache, new_cache, 1)

    old_message = '''                "Set github_oauth_client_id in the add-on configuration. "
                "The GitHub App or OAuth App must have Device Flow enabled."'''
    new_message = '''                "GitHub OAuth is unavailable because this Jarvis build does not yet "
                "have a registered Jarvis GitHub App. GitHub requires every MCP host "
                "application to use a registered GitHub App or OAuth App."'''
    require(text, old_message, "GitHub authorization error")
    text = text.replace(old_message, new_message, 1)

    text = text.replace('version="0.11.10"', 'version="0.11.11"')
    text = text.replace('"version": "0.11.10"', '"version": "0.11.11"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    old_error = '''      if (status) status.textContent = `GitHub authorization failed: ${error.message || error}`;'''
    new_error = '''      if (status) {
        const detail = error.message || error;
        status.textContent = `GitHub authorization unavailable: ${detail}`;
      }'''
    require(text, old_error, "GitHub UI error")
    text = text.replace(old_error, new_error, 1)

    text = text.replace("HUD 0.11.10", "HUD 0.11.11")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    missing = []
    for marker in (
        "len(cached) > len(FEATURED_REMOTE_PLUGINS)",
        "registered Jarvis GitHub App",
        "0.11.11",
    ):
        if marker not in main and marker not in index:
            missing.append(marker)
    if missing:
        raise RuntimeError(
            "Jarvis v0.11.11 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
