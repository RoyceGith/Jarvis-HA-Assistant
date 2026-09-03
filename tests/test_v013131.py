import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_CSS = (ROOT / "jarvis" / "app" / "static" / "css" / "base.css").read_text(encoding="utf-8")
AUTOMATION_CSS = (ROOT / "jarvis" / "app" / "static" / "css" / "automation-studio.css").read_text(encoding="utf-8")
ENTITY_CSS = (ROOT / "jarvis" / "app" / "static" / "css" / "entity-columns.css").read_text(encoding="utf-8")
WORKSPACE_CSS = (ROOT / "jarvis" / "app" / "static" / "css" / "workspace-modern.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013131PaletteTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.136")
        self.assertIn('version: "0.13.136"', (ROOT / "jarvis" / "config.yaml").read_text(encoding="utf-8"))
        self.assertIn('version="0.13.136"', (ROOT / "jarvis" / "app" / "main.py").read_text(encoding="utf-8"))
        self.assertIn("HUD 0.13.136", (ROOT / "jarvis" / "app" / "static" / "index.html").read_text(encoding="utf-8"))

    def test_legacy_green_theme_tokens_match_talk_blue(self):
        self.assertEqual(BASE_CSS.count("--phosphor: #5cecff;"), 1)
        self.assertEqual(BASE_CSS.count("--phosphor: #006d82;"), 1)
        self.assertEqual(BASE_CSS.count("--phosphor: #9fc9d5;"), 1)
        for legacy_color in ("#74f8bd", "#287052", "#b8d7c8", "rgba(101,255,155", "rgba(40,255,110"):
            self.assertNotIn(legacy_color, BASE_CSS.lower())

    def test_feature_accents_use_theme_blue(self):
        self.assertIn('data-status="pass"] { border-color: color-mix(in srgb,var(--cyan)', AUTOMATION_CSS)
        self.assertIn('data-state="completed"] { color:var(--cyan);', ENTITY_CSS)
        self.assertIn('data-settings-category="setup"] { --settings-accent: var(--cyan);', WORKSPACE_CSS)
        self.assertIn('data-settings-category="updates"] { --settings-accent: var(--cyan);', WORKSPACE_CSS)


if __name__ == "__main__":
    unittest.main()
