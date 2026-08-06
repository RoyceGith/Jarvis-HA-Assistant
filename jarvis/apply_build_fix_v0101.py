from pathlib import Path


ROOT = Path("/opt/jarvis")
PLUGIN_PATCH = ROOT / "apply_plugin_manager_v0100.py"


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Jarvis v0.10.1 build fix could not find: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    text = PLUGIN_PATCH.read_text(encoding="utf-8")
    text = replace_required(
        text,
        "    text = req(text, '<button id=\"settings-tab\">SETTINGS</button>', '<button id=\"settings-tab\">SETTINGS</button>\\n    <button id=\"plugins-tab\">PLUGINS</button>', 'tab')",
        "    settings_button = next((candidate for candidate in ('<button id=\"settings-tab\">Settings</button>', '<button id=\"settings-tab\">SETTINGS</button>') if candidate in text), None)\n    if settings_button is None:\n        raise RuntimeError('Jarvis v0.10.1 patch missing: settings navigation button')\n    text = text.replace(settings_button, settings_button + '\\n    <button id=\"plugins-tab\">Plugins</button>', 1)",
        "case-sensitive settings button patch",
    )
    text = text.replace("Jarvis v0.10.0 patch missing:", "Jarvis v0.10.1 patch missing:")
    text = text.replace("v0.10.0.</p>", "v0.10.1.</p>")
    text = text.replace("'HUD 0.10.0'", "'HUD 0.10.1'")
    text = text.replace('"version":"0.10.0"', '"version":"0.10.1"')
    text = text.replace("version=\"0.10.0\"", "version=\"0.10.1\"")
    text = text.replace("'version=\"0.10.0\"'", "'version=\"0.10.1\"'")
    text = text.replace("'\"version\": \"0.10.0\"'", "'\"version\": \"0.10.1\"'")

    verification = '''\n\ndef verify_patch() -> None:\n    index = INDEX.read_text(encoding="utf-8")\n    main = MAIN.read_text(encoding="utf-8")\n    required_index = (\n        'id="plugins-tab"',\n        'id="plugins-panel"',\n        'id="plugin-list"',\n    )\n    required_main = (\n        '@app.get("/api/plugins")',\n        '@app.post("/api/plugins")',\n        'WORKSHOP_TOOLS + active_mcp_tools()',\n    )\n    missing = [item for item in required_index if item not in index]\n    missing += [item for item in required_main if item not in main]\n    if missing:\n        raise RuntimeError("Jarvis v0.10.1 verification failed: " + ", ".join(missing))\n'''
    text = replace_required(
        text,
        "\n\nif __name__ == '__main__':\n    patch_index();patch_main()\n",
        verification + "\n\nif __name__ == '__main__':\n    patch_index();patch_main();verify_patch()\n",
        "plugin patch entrypoint",
    )
    PLUGIN_PATCH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
