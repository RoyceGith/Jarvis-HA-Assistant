import json
from pathlib import Path
import unittest

from jarvis.app.services import grinder_intents


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
DOMAIN = (ROOT / "jarvis/app/domains/grinder.py").read_text(encoding="utf-8")
HUD = (ROOT / "jarvis/app/static/js/grinder/hud.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class OwnerExtensionIsolationReleaseTests(unittest.TestCase):
    def tearDown(self):
        grinder_intents.configure_grinder_intents(grinder_monitor_tools=[])

    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.179"', CONFIG)
        self.assertIn('version="0.13.179"', MAIN)
        self.assertIn("HUD 0.13.179", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.179")

    def test_disabled_extension_has_no_chat_intent_or_tools(self):
        grinder_intents.configure_grinder_intents(grinder_monitor_tools=[])
        self.assertFalse(grinder_intents.is_grinder_diagnostic_intent("Why did the grinder freeze?"))
        self.assertEqual(grinder_intents.grinder_priority_tools(), [])

    def test_explicitly_enabled_extension_preserves_owner_workflow(self):
        tools = [{"name": "get_grinder_diagnostic_status"}]
        grinder_intents.configure_grinder_intents(grinder_monitor_tools=tools)
        self.assertTrue(grinder_intents.is_grinder_diagnostic_intent("Why did the grinder freeze?"))
        self.assertEqual(grinder_intents.grinder_priority_tools(), tools)

    def test_composition_and_ui_are_explicitly_gated(self):
        self.assertIn("def active_grinder_monitor_tools()", DOMAIN)
        self.assertIn("if GRINDER_MONITOR_ENABLED else []", DOMAIN)
        self.assertNotIn("GRINDER_MONITOR_TOOLS +", MAIN)
        self.assertGreaterEqual(MAIN.count("active_grinder_monitor_tools()"), 3)
        self.assertGreaterEqual(MAIN.count('detail="Owner extension is not enabled"'), 2)
        self.assertIn('id="grinder-connection-indicator"', HTML)
        indicator = HTML.split('id="grinder-connection-indicator"', 1)[1].split(">", 1)[0]
        self.assertIn(" hidden", indicator)
        self.assertIn("monitorAvailable = false", HUD)
        self.assertIn("indicator.hidden = true", HUD)
        self.assertIn("monitorAvailable !== false", HUD)

    def test_release_history_includes_v01392(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.178")


if __name__ == "__main__":
    unittest.main()
