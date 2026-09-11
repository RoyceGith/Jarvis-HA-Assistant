import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "zbrano/app/static/js/core.js").read_text(encoding="utf-8")
COLUMNS = (ROOT / "zbrano/app/static/js/entities/columns.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class PermissionFirstEntityInventoryReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.218"', CONFIG)
        self.assertIn('version="0.13.218"', MAIN)
        self.assertIn("HUD 0.13.218", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.218")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.217")

    def test_default_columns_put_permission_work_first(self):
        self.assertIn('const sourceOrder = DEFAULTS.map(column => column.key)', COLUMNS)
        self.assertIn(
            'const defaultOrder = ["select", "name", "state", "access", "area", "entity_id", "aliases", "domain", "class_unit", "site", "labels"]',
            COLUMNS,
        )
        self.assertIn("const order = savedOrder.length ? savedOrder : [...defaultOrder]", COLUMNS)

    def test_column_names_are_understandable(self):
        for label in ("Allow", "Device or sensor", "Current value", "How ZBRANO may use it", "Room / area"):
            self.assertIn(f'label:"{label}"', COLUMNS)
        self.assertIn("entityHeaders.slice(0, 5)", BROWSER)

    def test_permission_filter_reveals_the_table_from_its_start(self):
        self.assertIn("entityPermissionGuide.open = false", CORE)
        self.assertIn("function resetEntityInventoryScroll()", CORE)
        self.assertIn("tableWrap.scrollTop = 0", CORE)
        self.assertIn("tableWrap.scrollLeft = 0", CORE)
        self.assertIn("{top:0,left:0}", BROWSER)


if __name__ == "__main__":
    unittest.main()
