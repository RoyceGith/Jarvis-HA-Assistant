from pathlib import Path

ROOT = Path("/opt/jarvis")
PATCH_01113 = ROOT / "apply_install_routing_fix_v01113.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.14 source repair missing: {label}")


def main() -> None:
    text = PATCH_01113.read_text(encoding="utf-8")

    old = '''    old_return = \'\'\'    return {
        "plugins": result[:100],
        "cached": cached,
        "registry_error": registry_error,
    }\'\'\'
    new_return = \'\'\'    oauth_available = bool(_github_oauth_client_id())
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
    }\'\'\'
    require(text, old_return, "catalog response")
    text = text.replace(old_return, new_return, 1)'''

    new = '''    old_returns = (
        \'    return {"plugins": result[:100], "cached": cached, "registry_error": registry_error}\',
        \'\'\'    return {
        "plugins": result[:100],
        "cached": cached,
        "registry_error": registry_error,
    }\'\'\',
    )
    new_return = \'\'\'    oauth_available = bool(_github_oauth_client_id())
    for item in result:
        if item.get("id") == "github-official":
            item["auth_mode"] = "github-oauth"
            item["oauth_available"] = oauth_available
        else:
            item["auth_mode"] = "bearer" if item.get("auth_required") else "none"
            item["oauth_available"] = False

    return {"plugins": result[:100], "cached": cached, "registry_error": registry_error}\'\'\'

    for old_return in old_returns:
        if old_return in text:
            text = text.replace(old_return, new_return, 1)
            break
    else:
        raise RuntimeError("Jarvis v0.11.13 patch missing: catalog response")'''

    require(text, old, "v0.11.13 catalog matcher source")
    text = text.replace(old, new, 1)

    replacements = (
        (
            "text = text.replace('version=\"0.11.12\"', 'version=\"0.11.13\"')",
            "text = text.replace('version=\"0.11.12\"', 'version=\"0.11.14\"')",
        ),
        (
            "text = text.replace('\"version\": \"0.11.12\"', '\"version\": \"0.11.13\"')",
            "text = text.replace('\"version\": \"0.11.12\"', '\"version\": \"0.11.14\"')",
        ),
        (
            'text = text.replace("HUD 0.11.12", "HUD 0.11.13")',
            'text = text.replace("HUD 0.11.12", "HUD 0.11.14")',
        ),
        (
            'if "0.11.13" not in main:',
            'if "0.11.14" not in main:',
        ),
        (
            'missing.append("backend version 0.11.13")',
            'missing.append("backend version 0.11.14")',
        ),
    )

    for old_marker, new_marker in replacements:
        require(text, old_marker, old_marker)
        text = text.replace(old_marker, new_marker, 1)

    PATCH_01113.write_text(text, encoding="utf-8")


def verify() -> None:
    text = PATCH_01113.read_text(encoding="utf-8")
    required = (
        "for old_return in old_returns:",
        "0.11.14",
        "backend version 0.11.14",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError(
            "Jarvis v0.11.14 source repair verification failed: "
            + ", ".join(missing)
        )


if __name__ == "__main__":
    main()
    verify()
