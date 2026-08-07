from pathlib import Path

PATCH = Path("/opt/jarvis/apply_github_tool_approval_policy_v01129.py")


def main() -> None:
    text = PATCH.read_text(encoding="utf-8")
    old = 'plugin_public_end = text.find("\\n\\nasync def discover_plugin_tools", plugin_public_start)'
    new = 'plugin_public_end = text.find("\\ndef _is_github_plugin", plugin_public_start)'
    if old not in text:
        raise RuntimeError("ZBRANO v0.11.29 build fix missing: plugin_public boundary")
    text = text.replace(old, new, 1)
    if old in text or new not in text:
        raise RuntimeError("ZBRANO v0.11.29 build fix verification failed")
    PATCH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
