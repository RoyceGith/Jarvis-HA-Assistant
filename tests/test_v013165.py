import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
RUN = (ROOT / "jarvis/run.sh").read_text(encoding="utf-8")
DOMAIN = (ROOT / "jarvis/app/domains/grinder.py").read_text(encoding="utf-8")
OWNER_EXTENSIONS = (ROOT / "jarvis/app/services/owner_extensions.py").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class PrivateOwnerExtensionReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.169"', CONFIG)
        self.assertIn('version="0.13.169"', MAIN)
        self.assertIn("HUD 0.13.169", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.169")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.168")

    def test_general_addon_configuration_has_no_grinder_fields(self):
        for marker in ("grinder_monitor_enabled", "grinder_mqtt_"):
            self.assertNotIn(marker, CONFIG.lower())

    def test_startup_no_longer_exports_owner_specific_settings(self):
        self.assertNotIn("GRINDER_MONITOR_ENABLED", RUN)
        self.assertNotIn("GRINDER_MQTT_", RUN)
        self.assertNotIn("owner_extensions migrate", RUN)

    def test_private_persisted_compatibility_path_remains_active(self):
        self.assertIn('/data/zbrano_owner_extensions.json', OWNER_EXTENSIONS)
        self.assertIn("grinder_extension_config()", DOMAIN)
        self.assertIn('if GRINDER_MONITOR_ENABLED else []', DOMAIN)


if __name__ == "__main__":
    unittest.main()
