from pathlib import Path
import json
import unittest
from tests.frontend_source import load_frontend_source
from tests.backend_source import load_backend_source


ROOT = Path(__file__).resolve().parents[1]
INDEX = load_frontend_source()
MAIN = load_backend_source()
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class EntitiesScrollingTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.31"', CONFIG)
        self.assertIn('version="0.13.31"', MAIN)
        self.assertIn("HUD 0.13.31", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.31")

    def test_entity_views_are_independent_siblings(self):
        inventory_start = INDEX.index('<div data-entity-view-panel="inventory">')
        inventory_end = INDEX.index('    </div>\n    <div data-entity-view-panel="history"', inventory_start)
        history_start = INDEX.index('<div data-entity-view-panel="history"', inventory_start)
        self.assertLess(inventory_end, history_start)

    def test_inventory_has_a_bounded_scroll_viewport(self):
        self.assertIn('#entities-panel > [data-entity-view-panel] { flex:1 1 auto; min-height:0; }', INDEX)
        self.assertIn('#entities-panel > [data-entity-view-panel="inventory"] { display:flex; flex-direction:column; overflow:hidden; }', INDEX)
        self.assertIn('#entities-panel .table-wrap { flex:1 1 auto; min-height:0;', INDEX)
        self.assertIn('overflow:auto; overscroll-behavior:contain;', INDEX)

    def test_hidden_and_history_views_keep_correct_overflow(self):
        self.assertIn('#entities-panel > [data-entity-view-panel="history"] { overflow:auto;', INDEX)
        self.assertIn('#entities-panel > [data-entity-view-panel].hidden { display:none; }', INDEX)


if __name__ == "__main__":
    unittest.main()
