import asyncio
import ast
import json
from pathlib import Path
import unittest

from jarvis.app.services import automation_intents


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
AUTOMATION_INTENTS = (ROOT / "jarvis/app/services/automation_intents.py").read_text(encoding="utf-8")


def load_automation_function(name):
    tree = ast.parse(AUTOMATIONS)
    selected = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    namespace = {"Any": object, "asyncio": asyncio}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace[name]


class ConversationalAutomationContextReleaseTests(unittest.TestCase):
    def tearDown(self):
        automation_intents.configure_automation_intents(
            workshop_tools=[],
            entity_memory_context_fn=lambda message: "",
            brain_memory_context_fn=lambda message: "",
        )

    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.112"', CONFIG)
        self.assertIn('version="0.13.112"', MAIN)
        self.assertIn("HUD 0.13.112", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.112")

    def test_location_aware_automation_tool_is_routed(self):
        tools = [
            {"name": "find_home_assistant_entities"},
            {"name": "get_home_assistant_automation_context"},
            {"name": "prepare_autonomous_automation"},
        ]
        automation_intents.configure_automation_intents(
            workshop_tools=tools,
            entity_memory_context_fn=lambda message: "",
            brain_memory_context_fn=lambda message: "",
        )
        self.assertEqual(
            {tool["name"] for tool in automation_intents.automation_priority_tools()},
            {tool["name"] for tool in tools},
        )
        self.assertIn('"name": "get_home_assistant_automation_context"', MAIN)
        self.assertIn('result = await automation_chat_context(arguments.get("entity_ids") or [])', MAIN)
        self.assertIn("Never claim Zones are", AUTOMATION_INTENTS)

    def test_context_exposes_known_zone_links_and_person_state(self):
        snapshot = {
            "zones": [{"entity_id": "zone.factory_site", "name": "Factory Site", "occupants": 1}],
            "areas": [{
                "area_id": "office", "name": "Workshop Office", "site_name": "Factory Site",
                "zone_entity_id": "zone.factory_site", "labels": ["site-factory-site"],
            }],
            "entities": [{
                "entity_id": "sensor.office_temperature", "area_id": "office",
                "area_name": "Workshop Office", "site_name": "Factory Site",
                "zone_entity_id": "zone.factory_site", "role": "temperature",
            }],
        }
        fake_ha = type("HA", (), {"state_cache": {
            "person.resident": {"state": "factory_site", "attributes": {"friendly_name": "Resident"}},
            "zone.factory_site": {"state": "1", "attributes": {"friendly_name": "Factory Site"}},
        }})()
        async def refresh_context():
            return snapshot

        context_function = load_automation_function("automation_chat_context")
        context_function.__globals__.update({
            "_automation_refresh_area_context": refresh_context,
            "effective_entity_access": lambda entity_id: "read_only",
            "ha_ws": fake_ha,
        })
        context = asyncio.run(context_function(["sensor.office_temperature"]))
        self.assertEqual(context["areas"][0]["zone_entity_id"], "zone.factory_site")
        self.assertEqual(context["linked_entities"][0]["area_name"], "Workshop Office")
        self.assertEqual(context["presence_candidates"][0]["entity_id"], "person.resident")
        self.assertIn("person.* or device_tracker.*", context["presence_semantics"])

    def test_release_history_includes_v01393(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.111")


if __name__ == "__main__":
    unittest.main()
