import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "jarvis/app/static/js/core.js").read_text(encoding="utf-8")
ONBOARDING = (ROOT / "jarvis/app/static/js/onboarding.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/entity-columns.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class EntityPermissionGuideReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.181"', CONFIG)
        self.assertIn('version="0.13.181"', MAIN)
        self.assertIn("HUD 0.13.181", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.181")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.180")

    def test_inventory_marks_existing_safe_control_domains(self):
        self.assertIn('"control_capable": domain in SAFE_CONTROL_DOMAINS', MAIN)
        self.assertIn('if (entity.control_capable) return "control"', CORE)
        self.assertIn('const sensorEntityDomains = new Set(["sensor", "binary_sensor", "person", "device_tracker", "weather", "sun"])', CORE)

    def test_guide_filters_and_explains_without_bulk_approval(self):
        guide = CORE[CORE.index('entityPermissionGuide.innerHTML'):CORE.index('entityInventoryPanel?.insertBefore')]
        for marker in ("Sensor devices", "Control devices", "All entities", "Nothing is approved", "A checkbox grants access"):
            self.assertIn(marker, guide)
        self.assertNotIn("fetch(", guide)
        self.assertIn('entityPermissionFilter === "all"', CORE)
        self.assertIn("updateEntityPermissionGuide()", CORE)

    def test_onboarding_and_browser_cover_the_permission_handoff(self):
        self.assertIn("window.zbranoOpenEntityPermissionGuide?.()", ONBOARDING)
        self.assertIn(".entity-permission-categories", CSS)
        self.assertIn('[data-entity-permission-filter="control"]', BROWSER)
        self.assertIn("Nothing is approved by opening or filtering", BROWSER)


if __name__ == "__main__":
    unittest.main()
