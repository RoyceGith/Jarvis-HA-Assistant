from pathlib import Path
import builtins
import json
import symtable
import unittest

from tests.backend_source import load_backend_source


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
CALENDAR = (APP / "domains/calendar.py").read_text(encoding="utf-8")
GOOGLE = (APP / "domains/google_calendar.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class CalendarDomainExtractionTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.41"', CONFIG)
        self.assertIn('version="0.13.41"', MAIN)
        self.assertIn("HUD 0.13.41", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.41")
        current_patch = int(MANIFEST["version"].rsplit(".", 1)[1])
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], f"0.13.{current_patch - 1}")

    def test_local_calendar_engine_is_a_configured_domain(self):
        for marker in (
            "def calendar_store", "async def _create_calendar_appointment",
            "async def _update_calendar_reminders", "async def calendar_reminder_worker",
        ):
            self.assertIn(marker, CALENDAR)
            self.assertNotIn(marker, MAIN)
        self.assertIn("from .domains.calendar import (", MAIN)
        self.assertIn("configure_calendar_domain(", MAIN)
        self.assertIn('Path("/data/zbrano_calendar.json")', CALENDAR)

    def test_google_calendar_engine_is_a_configured_domain(self):
        for marker in (
            "def google_calendar_sync_store", "async def google_calendar_preview",
            "async def google_calendar_sync_once", "async def google_calendar_sync_worker",
        ):
            self.assertIn(marker, GOOGLE)
            self.assertNotIn(marker, MAIN)
        self.assertIn("from .domains.google_calendar import (", MAIN)
        self.assertIn("configure_google_calendar_domain(", MAIN)
        self.assertIn('Path("/data/zbrano_google_calendar_sync.json")', GOOGLE)

    def test_routes_and_worker_lifecycle_remain_in_composition_root(self):
        for route in (
            '@app.get("/api/calendar")', '@app.post("/api/calendar")',
            '@app.get("/api/calendar/google/status")', '@app.post("/api/calendar/google/sync")',
        ):
            self.assertIn(route, MAIN)
        self.assertIn('asyncio.create_task(calendar_reminder_worker(), name="zbrano-calendar-reminders")', MAIN)
        self.assertIn('asyncio.create_task(google_calendar_sync_worker(), name="zbrano-google-calendar-sync")', MAIN)
        self.assertIn("sync_task_provider=lambda: GOOGLE_CALENDAR_SYNC_TASK", MAIN)
        self.assertIn('"worker_active": google_calendar_worker_active()', GOOGLE)

    def test_calendar_domains_have_no_undeclared_global_dependencies(self):
        builtin_names = set(dir(builtins))
        for name, source in (("calendar", CALENDAR), ("google_calendar", GOOGLE)):
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

    def test_modular_test_source_includes_calendar_domains(self):
        combined = load_backend_source()
        self.assertIn("def configure_calendar_domain", combined)
        self.assertIn("def configure_google_calendar_domain", combined)


if __name__ == "__main__":
    unittest.main()
