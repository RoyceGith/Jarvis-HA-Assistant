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

    require(text, "while pages < 5:", "registry page limit")
    text = text.replace("while pages < 5:", "while pages < 20:", 1)

    marker = '\n\nasync def _fetch_plugin_catalog(force=False):'
    require(text, marker, "catalog parser insertion point")
    parser = r'''

# v0.11.11: keep package-only Registry entries discoverable. Installation is
# offered only when the Registry advertises a validated remote HTTPS endpoint.
def _catalog_remote_entry(server):
    if not isinstance(server, dict):
        return None

    wrapper = server
    if isinstance(server.get("server"), dict):
        server = server["server"]

    name = str(server.get("name") or "").strip()
    description = str(server.get("description") or "").strip()
    version = str(server.get("version") or "").strip()
    title = str(server.get("title") or name).strip()
    if not name:
        return None

    remotes = server.get("remotes") or []
    if isinstance(remotes, dict):
        remotes = [remotes]

    url = ""
    auth_required = False
    for remote in remotes:
        if not isinstance(remote, dict):
            continue
        candidate = str(
            remote.get("url") or remote.get("endpoint") or remote.get("uri") or ""
        ).strip()
        if not candidate.startswith("https://"):
            continue
        try:
            validate_plugin_url(candidate)
        except ValueError:
            continue
        url = candidate
        auth_required = bool(
            remote.get("authentication") or remote.get("auth") or remote.get("headers")
        )
        break

    packages = server.get("packages") or []
    if isinstance(packages, dict):
        packages = [packages]
    package_labels = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        identifier = str(
            package.get("identifier") or package.get("name") or package.get("package") or ""
        ).strip()
        registry_type = str(
            package.get("registryType") or package.get("registry_type") or package.get("type") or ""
        ).strip()
        if identifier:
            package_labels.append(
                f"{registry_type}:{identifier}" if registry_type else identifier
            )
    package_ref = ", ".join(package_labels[:4])

    lower = f"{name} {title} {description} {package_ref}".lower()
    if any(word in lower for word in ("github", "gitlab", "code", "developer", "repository")):
        category = "developer-tools"
    elif any(word in lower for word in ("calendar", "mail", "task", "docs", "productivity")):
        category = "productivity"
    elif any(word in lower for word in ("database", "data", "analytics", "search", "redis", "sql")):
        category = "data"
    else:
        category = "other"

    meta = wrapper.get("_meta") or wrapper.get("meta") or {}
    identity = url or package_ref or name
    return {
        "id": hashlib.sha256(f"{name}|{version}|{identity}".encode()).hexdigest()[:20],
        "name": name,
        "title": title[:120],
        "description": description[:1000],
        "version": version[:80],
        "url": url,
        "package_ref": package_ref[:500],
        "installable": bool(url),
        "category": category,
        "verified": bool(server.get("verified") or server.get("official") or meta.get("official")),
        "auth_required": auth_required,
        "publisher": str(server.get("publisher") or "")[:120],
    }
'''
    text = text.replace(marker, parser + marker, 1)

    old_message = '''                "Set github_oauth_client_id in the add-on configuration. "
                "The GitHub App or OAuth App must have Device Flow enabled."'''
    new_message = '''                "GitHub one-click OAuth requires Jarvis to have a registered GitHub "
                "OAuth/GitHub App client ID. This build has no centrally registered Jarvis "
                "GitHub App, so OAuth cannot be started safely without one."'''
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

    runtime = r'''
(() => {
  const baseCatalogCard = catalogCard;
  catalogCard = function(item) {
    const card = baseCatalogCard(item);
    const install = card.querySelector("button[data-catalog-install]");
    const details = card.querySelectorAll(".catalog-details");
    if (item.installable === false || !item.url) {
      if (install) {
        install.disabled = true;
        install.textContent = "Package entry";
        install.title = "Discovered in the MCP Registry, but this entry has no remote HTTPS endpoint for Jarvis to install.";
      }
      if (item.package_ref) {
        const packageLine = document.createElement("div");
        packageLine.className = "catalog-details";
        packageLine.textContent = `Package: ${item.package_ref}`;
        card.querySelector(".catalog-actions")?.before(packageLine);
      }
    }
    return card;
  };
})();
'''
    last_script = text.rfind("</script>")
    if last_script < 0:
        raise RuntimeError("Jarvis v0.11.11 patch missing: final script close")
    text = text[:last_script] + runtime + "\n" + text[last_script:]

    text = text.replace("HUD 0.11.10", "HUD 0.11.11")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required = (
        "len(cached) > len(FEATURED_REMOTE_PLUGINS)",
        "while pages < 20:",
        '"installable": bool(url)',
        '"package_ref": package_ref[:500]',
        'install.textContent = "Package entry"',
        "centrally registered Jarvis",
        "0.11.11",
    )
    missing = [marker for marker in required if marker not in main and marker not in index]
    if missing:
        raise RuntimeError(
            "Jarvis v0.11.11 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
