import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "jarvis/app/static/js/core.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ExplicitEntityPermissionReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.205"', CONFIG)
        self.assertIn('version="0.13.205"', MAIN)
        self.assertIn("HUD 0.13.205", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.205")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.204")

    def test_inventory_never_writes_automatic_permission(self):
        inventory_tail = MAIN[MAIN.index('"auto_approved": False'):MAIN.index('entities.sort(key=lambda entity:')]
        self.assertNotIn("save_entity_policy", inventory_tail)
        self.assertNotIn('"enabled": True', inventory_tail)
        self.assertIn("Prime the installation inventory without changing any entity permission", MAIN)

    def test_new_entities_are_unselected_while_saved_policy_is_preserved(self):
        self.assertIn("selected: false", CORE)
        self.assertIn('checkbox.title = "Allow ZBRANO to use this entity with the selected access"', CORE)
        self.assertNotIn("checkbox.disabled = Boolean(entity.auto_approved)", CORE)
        self.assertIn("selected: Boolean(existing && existing.enabled)", CORE)
        self.assertIn("access: (existing && existing.access) || entity.risk", CORE)

    def test_browser_confirms_control_is_unchecked_and_editable(self):
        self.assertIn("explicitControlRow", BROWSER)
        self.assertIn("isChecked(), false", BROWSER)
        self.assertIn("isEnabled(), true", BROWSER)


if __name__ == "__main__":
    unittest.main()
