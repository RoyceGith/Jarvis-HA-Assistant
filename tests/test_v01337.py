import json
from pathlib import Path
import unittest

from jarvis.app.services import developer_tools, fast_memory_intents, grinder_intents


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
GRINDER = (APP / "services/grinder_intents.py").read_text(encoding="utf-8")
FAST_MEMORY = (APP / "services/fast_memory_intents.py").read_text(encoding="utf-8")
DEVELOPER = (APP / "services/developer_tools.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


TOOLS = [
    {"name": "remember_fast_memory"},
    {"name": "search_fast_memory"},
    {"name": "forget_fast_memory"},
    {"name": "write_project_note"},
]
GRINDER_TOOLS = [
    {"name": "get_grinder_monitor_status"},
    {"name": "list_grinder_incidents"},
    {"name": "get_grinder_incident"},
]


class RemainingIntentBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.44"', CONFIG)
        self.assertIn('version="0.13.44"', MAIN)
        self.assertIn("HUD 0.13.44", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.44")

    def test_three_boundaries_are_outside_the_composition_root(self):
        for marker in (
            "def is_grinder_diagnostic_intent(",
            "def is_fast_memory_intent(",
            "def developer_runtime_tools(",
        ):
            self.assertNotIn(marker, MAIN)
        self.assertIn("def is_grinder_diagnostic_intent(", GRINDER)
        self.assertIn("def is_fast_memory_intent(", FAST_MEMORY)
        self.assertIn("def developer_runtime_tools(", DEVELOPER)
        for marker in (
            "configure_grinder_intents(",
            "configure_fast_memory_intents(",
            "configure_developer_tools(",
        ):
            self.assertIn(marker, MAIN)

    def test_grinder_detection_tools_and_safety_guidance(self):
        grinder_intents.configure_grinder_intents(grinder_monitor_tools=GRINDER_TOOLS)
        self.assertTrue(grinder_intents.is_grinder_diagnostic_intent("Why did the grinder freeze?"))
        self.assertFalse(grinder_intents.is_grinder_diagnostic_intent("show application telemetry"))
        self.assertEqual(grinder_intents.grinder_priority_tools(), GRINDER_TOOLS)
        guidance = grinder_intents.grinder_system_instructions("base")
        self.assertIn("read-only", guidance)
        self.assertIn("separate\nmeasured evidence from inference", guidance)

    def test_fast_memory_detection_and_bounded_tools(self):
        fast_memory_intents.configure_fast_memory_intents(workshop_tools=TOOLS)
        self.assertTrue(fast_memory_intents.is_fast_memory_intent("remember this for later"))
        self.assertFalse(fast_memory_intents.is_fast_memory_intent("write this to Workshop Memory"))
        self.assertEqual(
            {tool["name"] for tool in fast_memory_intents.fast_memory_priority_tools()},
            {"remember_fast_memory", "search_fast_memory", "forget_fast_memory"},
        )

    def test_developer_tools_remain_mode_gated(self):
        developer_tools.configure_developer_tools(developer_mode_enabled_fn=lambda: False)
        self.assertEqual(developer_tools.developer_runtime_tools(), [])
        developer_tools.configure_developer_tools(developer_mode_enabled_fn=lambda: True)
        tools = developer_tools.developer_runtime_tools()
        self.assertEqual(
            [tool["name"] for tool in tools],
            ["investigate_zbrano_feature", "inspect_zbrano_ui_with_playwright"],
        )
        self.assertTrue(all(tool["strict"] for tool in tools))


if __name__ == "__main__":
    unittest.main()
