import json
from pathlib import Path
import tempfile
import unittest

from jarvis.app.services import agent_runtime, tab_activity


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
AGENT_RUNTIME = (APP / "services/agent_runtime.py").read_text(encoding="utf-8")
TAB_ACTIVITY = (APP / "services/tab_activity.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AgentRuntimeAndTabActivityBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.46"', CONFIG)
        self.assertIn('version="0.13.46"', MAIN)
        self.assertIn("HUD 0.13.46", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.46")

    def test_both_services_are_outside_composition_root_and_configured(self):
        self.assertNotIn("def effective_system_instructions(", MAIN)
        self.assertNotIn("def _tab_activity_revision(", MAIN)
        self.assertIn("def effective_system_instructions(", AGENT_RUNTIME)
        self.assertIn("def _tab_activity_revision(", TAB_ACTIVITY)
        self.assertIn("configure_agent_runtime(", MAIN)
        self.assertIn("configure_tab_activity_service(", MAIN)
        self.assertIn('return {"revisions": tab_activity_revisions()}', MAIN)

    def test_agent_preferences_keep_existing_bounds_and_payloads(self):
        preferences = {
            "response_length": "balanced",
            "confirmation_strictness": "standard",
            "preferred_language": "auto",
            "context_messages": 100,
            "agent_model": "gpt-test",
            "reasoning_effort": "high",
        }
        agent_runtime.configure_agent_runtime(
            openai_model="gpt-default",
            chat_context_max_messages=20,
            base_system_instructions="BASE POLICY",
            load_preferences_fn=lambda: preferences,
            load_general_instructions_fn=lambda: "Remember the workshop name.",
        )
        self.assertEqual(agent_runtime.active_agent_model(), "gpt-test")
        self.assertEqual(agent_runtime.chat_context_limit(), 50)
        self.assertEqual(agent_runtime.agent_reasoning_payload(), {"reasoning": {"effort": "high"}})
        instructions = agent_runtime.effective_system_instructions()
        self.assertIn("BASE POLICY", instructions)
        self.assertIn("Remember the workshop name.", instructions)

    def test_tab_revisions_ignore_volatile_watch_state_but_track_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {name: root / name for name in (
                "chat", "plugins", "oauth", "notifications", "calendar", "settings", "developer"
            )}
            state = {"automations": [{"id": "one", "status": "armed", "trigger_count": 1}]}
            tab_activity.configure_tab_activity_service(
                automation_store_fn=lambda: state,
                list_files_fn=lambda path: [],
                shared_file_root=root / "files",
                revision_paths=paths,
            )
            first = tab_activity.tab_activity_revisions()
            state["automations"][0]["status"] = "suppressed"
            state["automations"][0]["trigger_count"] = 9
            second = tab_activity.tab_activity_revisions()
            self.assertEqual(first["automations"], second["automations"])
            state["automations"][0]["name"] = "Comfort monitoring"
            third = tab_activity.tab_activity_revisions()
            self.assertNotEqual(second["automations"], third["automations"])
            self.assertEqual(first["chat"], "missing")


if __name__ == "__main__":
    unittest.main()
