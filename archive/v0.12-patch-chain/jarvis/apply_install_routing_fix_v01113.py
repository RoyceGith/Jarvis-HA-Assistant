from pathlib import Path

ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.13 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    old_return = '''    return {
        "plugins": result[:100],
        "cached": cached,
        "registry_error": registry_error,
    }'''
    new_return = '''    oauth_available = bool(_github_oauth_client_id())
    for item in result:
        if item.get("id") == "github-official":
            item["auth_mode"] = "github-oauth"
            item["oauth_available"] = oauth_available
        else:
            item["auth_mode"] = "bearer" if item.get("auth_required") else "none"
            item["oauth_available"] = False

    return {
        "plugins": result[:100],
        "cached": cached,
        "registry_error": registry_error,
    }'''
    require(text, old_return, "catalog response")
    text = text.replace(old_return, new_return, 1)

    text = text.replace('version="0.11.12"', 'version="0.11.13"')
    text = text.replace('"version": "0.11.12"', '"version": "0.11.13"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    old_wrapper = '''  catalogCard = function(item) {
    const card = baseCatalogCard(item);
    const install = card.querySelector("button[data-catalog-install]");
    const details = card.querySelectorAll(".catalog-details");
    if (item.installable === false || !item.url) {'''
    new_wrapper = '''  catalogCard = function(item) {
    const card = baseCatalogCard(item);
    const install = card.querySelector("button[data-catalog-install]");
    const details = card.querySelectorAll(".catalog-details");
    if (install) {
      install.dataset.authMode = item.auth_mode || "none";
      install.dataset.oauthAvailable = item.oauth_available ? "1" : "0";
    }
    if (item.auth_mode === "github-oauth" && !item.oauth_available && install) {
      install.disabled = true;
      install.textContent = "GitHub OAuth unavailable";
      install.title =
        "This Jarvis build does not yet include a registered Jarvis GitHub OAuth application.";
    }
    if (item.installable === false || !item.url) {'''
    require(text, old_wrapper, "catalog card wrapper")
    text = text.replace(old_wrapper, new_wrapper, 1)

    old_click = '''  document.addEventListener("click", event => {
    const button = event.target.closest?.("button[data-catalog-install]");
    if (!button) return;
    const card = button.closest(".catalog-card");
    const isGitHub = /github/i.test(card?.textContent || "");
    if (!isGitHub) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    authorizeAndInstallGitHub(button);
  }, true);'''
    new_click = '''  document.addEventListener("click", event => {
    const button = event.target.closest?.("button[data-catalog-install]");
    if (!button || button.dataset.authMode !== "github-oauth") return;

    event.preventDefault();
    event.stopImmediatePropagation();

    if (button.dataset.oauthAvailable !== "1") {
      const status = catalogStatusNode();
      if (status) {
        status.textContent =
          "GitHub OAuth is unavailable in this build because Jarvis does not yet have a registered GitHub OAuth application.";
      }
      return;
    }

    authorizeAndInstallGitHub(button);
  }, true);'''
    require(text, old_click, "GitHub install interception")
    text = text.replace(old_click, new_click, 1)

    old_start = '''  async function authorizeAndInstallGitHub(button) {
    const status = catalogStatusNode();
    button.disabled = true;
    let authWindow = null;
    try {
      authWindow = window.open("about:blank", "_blank");'''
    new_start = '''  async function authorizeAndInstallGitHub(button) {
    const status = catalogStatusNode();
    if (button.dataset.oauthAvailable !== "1") {
      if (status) {
        status.textContent =
          "GitHub OAuth is unavailable in this build because Jarvis does not yet have a registered GitHub OAuth application.";
      }
      return;
    }

    button.disabled = true;
    let authWindow = null;
    try {
      authWindow = window.open("about:blank", "_blank", "noopener");'''
    require(text, old_start, "GitHub authorization start")
    text = text.replace(old_start, new_start, 1)

    text = text.replace("HUD 0.11.12", "HUD 0.11.13")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")

    missing = []
    for marker in (
        'item["auth_mode"] = "github-oauth"',
        'item["oauth_available"] = oauth_available',
        'install.dataset.authMode = item.auth_mode || "none"',
        'install.dataset.oauthAvailable = item.oauth_available ? "1" : "0"',
        'button.dataset.authMode !== "github-oauth"',
        'button.dataset.oauthAvailable !== "1"',
        "GitHub OAuth unavailable",
    ):
        if marker not in main and marker not in index:
            missing.append(marker)

    if '/github/i.test(card?.textContent' in index:
        missing.append("broad GitHub text interception still present")

    popup_pos = index.find('window.open("about:blank"')
    guard_pos = index.rfind('button.dataset.oauthAvailable !== "1"', 0, popup_pos)
    if popup_pos >= 0 and guard_pos < 0:
        missing.append("popup not guarded by OAuth availability")

    if "0.11.13" not in main:
        missing.append("backend version 0.11.13")

    if missing:
        raise RuntimeError(
            "Jarvis v0.11.13 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
