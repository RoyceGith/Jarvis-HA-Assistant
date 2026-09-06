import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from jarvis.app.services.owner_extensions import (
    grinder_extension_config,
    migrate_legacy_grinder_environment,
)


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = (ROOT / "jarvis/app/domains/grinder.py").read_text(encoding="utf-8")
OWNER_EXTENSIONS = (ROOT / "jarvis/app/services/owner_extensions.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class OwnerExtensionMigrationReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.178"', CONFIG)
        self.assertIn('version="0.13.178"', MAIN)
        self.assertIn("HUD 0.13.178", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.178")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.177")

    def test_default_installation_does_not_create_private_extension_file(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "owner_extensions.json"
            migrated = migrate_legacy_grinder_environment(
                path=path,
                environ={"GRINDER_MONITOR_ENABLED": "false"},
            )
            self.assertFalse(migrated)
            self.assertFalse(path.exists())

    def test_customized_legacy_configuration_is_migrated_without_losing_secrets(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "owner_extensions.json"
            legacy = {
                "GRINDER_MONITOR_ENABLED": "true",
                "GRINDER_MQTT_HOST": "private-broker",
                "GRINDER_MQTT_PORT": "2883",
                "GRINDER_MQTT_USERNAME": "royce",
                "GRINDER_MQTT_PASSWORD": "secret-value",
                "GRINDER_MQTT_TOPIC_PREFIX": "/private/grinder/",
            }
            self.assertTrue(migrate_legacy_grinder_environment(path=path, environ=legacy))
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["version"], 1)
            self.assertEqual(stored["extensions"]["grinder_monitor"]["mqtt_password"], "secret-value")

            loaded = grinder_extension_config(path=path, environ={})
            self.assertTrue(loaded["enabled"])
            self.assertEqual(loaded["mqtt_host"], "private-broker")
            self.assertEqual(loaded["mqtt_port"], 2883)
            self.assertEqual(loaded["mqtt_topic_prefix"], "private/grinder")

    def test_runtime_prefers_private_persisted_configuration(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "owner_extensions.json"
            path.write_text(json.dumps({
                "version": 1,
                "extensions": {"grinder_monitor": {"enabled": True, "mqtt_host": "stored-broker"}},
            }), encoding="utf-8")
            loaded = grinder_extension_config(
                path=path,
                environ={"GRINDER_MONITOR_ENABLED": "false", "GRINDER_MQTT_HOST": "legacy-broker"},
            )
            self.assertTrue(loaded["enabled"])
            self.assertEqual(loaded["mqtt_host"], "stored-broker")

    def test_migration_helper_remains_available_and_grinder_uses_private_loader(self):
        self.assertIn("def migrate_legacy_grinder_environment(", OWNER_EXTENSIONS)
        self.assertIn("from ..services.owner_extensions import grinder_extension_config", DOMAIN)
        self.assertIn("_GRINDER_EXTENSION = grinder_extension_config()", DOMAIN)


if __name__ == "__main__":
    unittest.main()
