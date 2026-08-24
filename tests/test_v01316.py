from pathlib import Path
import builtins
import json
import symtable
import unittest

from tests.backend_source import load_backend_source


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
AUTOMATIONS = (APP / "domains/automations.py").read_text(encoding="utf-8")
NOTIFICATIONS = (APP / "domains/notifications.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class StatefulDomainExtractionTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.21"', CONFIG)
        self.assertIn('version="0.13.21"', MAIN)
        self.assertIn("HUD 0.13.21", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.21")
        current_patch = int(MANIFEST["version"].rsplit(".", 1)[1])
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], f"0.13.{current_patch - 1}")

    def test_automation_engine_is_a_configured_domain(self):
        for marker in (
            "def automation_store", "async def _automation_refresh_area_context",
            "async def _automation_evaluate_state_change", "async def _automation_execute_action",
        ):
            self.assertIn(marker, AUTOMATIONS)
            self.assertNotIn(marker, MAIN)
        self.assertIn("from .domains.automations import (", MAIN)
        self.assertIn("configure_automation_domain(", MAIN)
        self.assertIn('Path("/data/autonomous_automations.json")', AUTOMATIONS)

    def test_notification_engine_is_a_configured_domain(self):
        for marker in (
            "def notification_store", "async def notification_channels",
            "async def _create_notification_watch", "async def notification_watch_worker",
        ):
            self.assertIn(marker, NOTIFICATIONS)
            self.assertNotIn(marker, MAIN)
        self.assertIn("from .domains.notifications import (", MAIN)
        self.assertIn("configure_notification_domain(", MAIN)
        self.assertIn('Path("/data/notification_center.json")', NOTIFICATIONS)

    def test_routes_and_runtime_order_remain_in_composition_root(self):
        for route in (
            '@app.get("/api/automations")',
            '@app.post("/api/automations/suggestions/{suggestion_id}/approve")',
            '@app.get("/api/notifications")',
            '@app.post("/api/notifications/test")',
        ):
            self.assertIn(route, MAIN)
        self.assertGreater(MAIN.rindex("configure_notification_domain("), MAIN.index("async def list_ha_entities"))
        self.assertGreater(MAIN.rindex("configure_automation_domain("), MAIN.index("async def test_notification_channel"))

    def test_domain_modules_have_no_undeclared_global_dependencies(self):
        builtin_names = set(dir(builtins))
        for name, source in (("automations", AUTOMATIONS), ("notifications", NOTIFICATIONS)):
            table = symtable.symtable(source, name, "exec")
            module_names = set(table.get_identifiers())
            unresolved = set()

            def inspect_scope(scope):
                for child in scope.get_children():
                    for identifier in child.get_identifiers():
                        symbol = child.lookup(identifier)
                        if symbol.is_referenced() and symbol.is_global() and identifier not in module_names and identifier not in builtin_names:
                            unresolved.add(identifier)
                    inspect_scope(child)

            inspect_scope(table)
            self.assertEqual(unresolved, set(), name)

    def test_modular_test_source_includes_domain_engines(self):
        combined = load_backend_source()
        self.assertIn("def configure_automation_domain", combined)
        self.assertIn("def configure_notification_domain", combined)
        helper = (ROOT / "tests/backend_source.py").read_text(encoding="utf-8")
        self.assertIn('APP / "domains"', helper)


if __name__ == "__main__":
    unittest.main()
