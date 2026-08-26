import json
from pathlib import Path
import unittest

from jarvis.app.services import automation_intents, calendar_intents, home_assistant_intents


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
AUTOMATION = (APP / "services/automation_intents.py").read_text(encoding="utf-8")
HOME_ASSISTANT = (APP / "services/home_assistant_intents.py").read_text(encoding="utf-8")
CALENDAR = (APP / "services/calendar_intents.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


TOOLS = [
    {"name": name}
    for name in (
        "find_home_assistant_entities", "get_home_assistant_state",
        "turn_on_home_assistant_entity", "turn_off_home_assistant_entity",
        "get_home_assistant_history", "correlate_home_assistant_timeline",
        "search_home_assistant_logbook", "prepare_autonomous_automation",
        "create_notification_watch", "create_calendar_appointment",
        "list_calendar_appointments", "update_calendar_reminders",
        "cancel_calendar_appointment", "unrelated_tool",
    )
]


class IntentRoutingBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        automation_intents.configure_automation_intents(
            workshop_tools=TOOLS,
            entity_memory_context_fn=lambda message: "entity memory",
            brain_memory_context_fn=lambda message: "brain memory",
        )
        home_assistant_intents.configure_home_assistant_intents(workshop_tools=TOOLS)
        calendar_intents.configure_calendar_intents(workshop_tools=TOOLS)

    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.52"', CONFIG)
        self.assertIn('version="0.13.52"', MAIN)
        self.assertIn("HUD 0.13.52", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.52")

    def test_three_services_are_outside_composition_root_and_configured(self):
        self.assertNotIn("def is_automation_intent(", MAIN)
        self.assertNotIn("def is_home_assistant_priority_intent(", MAIN)
        self.assertNotIn("def is_calendar_intent(", MAIN)
        self.assertIn("def is_automation_intent(", AUTOMATION)
        self.assertIn("def is_home_assistant_priority_intent(", HOME_ASSISTANT)
        self.assertIn("def is_calendar_intent(", CALENDAR)
        for marker in (
            "configure_automation_intents(", "configure_home_assistant_intents(",
            "configure_calendar_intents(",
        ):
            self.assertIn(marker, MAIN)

    def test_home_assistant_command_and_history_routing(self):
        self.assertTrue(home_assistant_intents.is_home_assistant_priority_intent("turn on the living room light"))
        self.assertFalse(home_assistant_intents.is_home_assistant_priority_intent("when it is dark turn on the light"))
        self.assertTrue(home_assistant_intents.is_home_assistant_history_intent("show temperature history last day"))
        immediate = {tool["name"] for tool in home_assistant_intents.home_assistant_priority_tools()}
        history = {tool["name"] for tool in home_assistant_intents.home_assistant_history_tools()}
        self.assertEqual(immediate, {
            "find_home_assistant_entities", "get_home_assistant_state",
            "turn_on_home_assistant_entity", "turn_off_home_assistant_entity",
        })
        self.assertIn("get_home_assistant_history", history)
        guidance = home_assistant_intents.home_assistant_history_system_instructions("base")
        self.assertIn("Never request more than seven days or eight entities", guidance)

    def test_automation_and_calendar_routing_context_and_guidance(self):
        self.assertTrue(automation_intents.is_automation_intent("if it is dark then turn on the light"))
        automation_tools = {tool["name"] for tool in automation_intents.automation_priority_tools()}
        self.assertEqual(automation_tools, {
            "find_home_assistant_entities", "get_home_assistant_state",
            "prepare_autonomous_automation", "create_notification_watch",
        })
        memory = automation_intents.automation_memory_input("create an automation")
        self.assertEqual(memory[0]["content"], "entity memory\nbrain memory")
        self.assertIn("stores a disabled draft", automation_intents.automation_system_instructions("base"))

        self.assertTrue(calendar_intents.is_calendar_intent("Dentist 27.08.2026 14.30"))
        calendar_tools = {tool["name"] for tool in calendar_intents.calendar_priority_tools()}
        self.assertEqual(calendar_tools, {
            "create_calendar_appointment", "list_calendar_appointments",
            "update_calendar_reminders", "cancel_calendar_appointment",
        })
        guidance = calendar_intents.calendar_system_instructions("base")
        self.assertIn("Duration defaults to 60 minutes", guidance)
        self.assertIn("offsets 120, 1440, [1440, 120]", guidance)


if __name__ == "__main__":
    unittest.main()
