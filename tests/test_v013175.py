import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "zbrano/app/static/js/core.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class ExplicitEntityPermissionReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.243"', CONFIG)
        self.assertIn('version="0.13.243"', MAIN)
        self.assertIn("HUD 0.13.243", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.243")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.242")

    def test_inventory_applies_only_missing_ordinary_control_defaults(self):
        self.assertIn("apply_discovered_control_defaults(raw_states)", MAIN)
        self.assertIn('(policy.get(entity_id) or {}).get("source") == "default_control"', MAIN)

    def test_saved_policy_is_loaded_before_rendering(self):
        self.assertIn("selected: false", CORE)
        self.assertIn('checkbox.title = "Allow ZBRANO to use this entity with the selected access"', CORE)
        self.assertNotIn("checkbox.disabled = Boolean(entity.auto_approved)", CORE)
        self.assertIn("selected: Boolean(existing && existing.enabled)", CORE)
        self.assertIn("access: (existing && existing.access) || entity.risk", CORE)

    def test_browser_confirms_default_control_is_checked_and_editable(self):
        self.assertIn("explicitControlRow", BROWSER)
        self.assertIn("isChecked(), true", BROWSER)
        self.assertIn("isEnabled(), true", BROWSER)


if __name__ == "__main__":
    unittest.main()
