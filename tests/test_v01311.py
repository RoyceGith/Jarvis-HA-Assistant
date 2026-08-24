from pathlib import Path
import ast
import json
import re
import unittest
from tests.frontend_source import load_frontend_source
from tests.backend_source import load_backend_source


ROOT = Path(__file__).resolve().parents[1]
INDEX = load_frontend_source()
MAIN = load_backend_source()
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_functions(*names):
    tree = ast.parse(MAIN)
    selected = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    namespace = {"Any": object, "re": re}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "jarvis/app/main.py", "exec"), namespace)
    return namespace


class SiteAwareAutomationBrainTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.22"', CONFIG)
        self.assertIn('version="0.13.22"', MAIN)
        self.assertIn("HUD 0.13.22", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.22")

    def test_labels_and_zones_are_imported_without_coordinates(self):
        self.assertIn('"type": "config/label_registry/list"', MAIN)
        self.assertIn('entity_id.startswith("zone.")', MAIN)
        zone_block = MAIN[MAIN.index('if not entity_id.startswith("zone.")') : MAIN.index("areas: dict", MAIN.index('if not entity_id.startswith("zone.")'))]
        self.assertNotIn('"latitude"', zone_block)
        self.assertNotIn('"longitude"', zone_block)

    def test_site_labels_resolve_to_matching_zones(self):
        self.assertIn("def _automation_site_key", MAIN)
        self.assertIn('("site_", "location_", "property_")', MAIN)
        self.assertIn('zone = zone_keys.get(_automation_site_key(site_label))', MAIN)
        self.assertIn('"zone_entity_id": str((zone or {}).get("entity_id") or "")', MAIN)
        functions = load_functions("_automation_context_key", "_automation_site_key")
        self.assertEqual(functions["_automation_site_key"]("site-factory-workshop"), "factory_workshop")
        self.assertEqual(functions["_automation_site_key"]("Factory workshop"), "factory_workshop")

    def test_presence_is_scoped_to_the_room_site(self):
        self.assertIn('def _automation_presence_confirmed(item: dict[str, Any], settings: dict[str, Any], expected_zone: str = "")', MAIN)
        self.assertIn('_automation_presence_confirmed({}, data["settings"], zone_entity_id)', MAIN)
        self.assertIn("def _automation_expected_zone", MAIN)
        self.assertIn("_automation_expected_zone(data, item)", MAIN)
        self.assertIn('expected {expected_zone}', MAIN)
        functions = load_functions("_automation_context_key", "_automation_presence_confirmed")
        functions["ha_ws"] = type("HA", (), {"state_cache": {"person.royce": {"state": "factory_workshop"}}})()
        functions["automation_store"] = lambda: {"area_context": {"zones": [
            {"entity_id": "zone.factory_workshop", "name": "Factory workshop"},
            {"entity_id": "zone.home", "name": "Home"},
        ]}}
        settings = {"require_presence": True, "presence_entity": "person.royce"}
        self.assertTrue(functions["_automation_presence_confirmed"]({}, settings, "zone.factory_workshop")[0])
        self.assertFalse(functions["_automation_presence_confirmed"]({}, settings, "zone.home")[0])

    def test_semantic_and_safety_labels_are_enforced(self):
        self.assertIn('{"presence_signal", "room_presence", "occupancy_signal"}', MAIN)
        self.assertIn('{"never_automate", "observe_only", "no_control"}', MAIN)
        self.assertIn("_automation_label_blocks_control(data, entity_id)", MAIN)
        self.assertIn("Automation Brain control is blocked by a Home Assistant label", MAIN)

    def test_learning_and_interface_follow_ha_organization(self):
        self.assertIn("def _automation_reconcile_learning", MAIN)
        self.assertIn('item["zone_entity_id"] = mapping.get("zone_entity_id") or ""', MAIN)
        self.assertIn("Site / Zone", INDEX)
        self.assertIn("HA Labels", INDEX)
        self.assertIn('entity.site_name || "Unlinked"', INDEX)
        self.assertIn("api/ha/entities?refresh=1", INDEX)


if __name__ == "__main__":
    unittest.main()
