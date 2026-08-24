from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ProactiveSuggestionSpeechTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.14"', CONFIG)
        self.assertIn('version="0.13.14"', MAIN)
        self.assertIn("HUD 0.13.14", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.14")

    def test_spoken_suggestion_omits_internal_automation_name(self):
        start = INDEX.index("async function announceSuggestion(item)")
        end = INDEX.index("async function pollSuggestions()", start)
        announcement = INDEX[start:end]
        self.assertIn('const prompt=String(item.detail||"").trim()', announcement)
        self.assertIn("await speakText(prompt,true)", announcement)
        self.assertNotIn("item.title", announcement)
        self.assertNotIn("Say approve or decline.", announcement)

    def test_visual_suggestion_keeps_automation_name(self):
        start = INDEX.index("function renderSuggestions()")
        end = INDEX.index("function referencedEntities()", start)
        rendering = INDEX[start:end]
        self.assertIn('item.title||"Suggestion"', rendering)

    def test_automation_brain_prepares_disabled_review_drafts(self):
        self.assertIn('"name": "prepare_autonomous_automation"', MAIN)
        start = MAIN.index("async def _prepare_chat_automation")
        end = MAIN.index("def _activate_automation", start)
        preparation = MAIN[start:end]
        self.assertIn("enabled=False", preparation)
        self.assertIn('"status": "review_required"', preparation)
        self.assertIn('"confirmation_required": True', preparation)
        self.assertIn("PENDING_AUTOMATION_CONFIRMATIONS[session_id]", preparation)

    def test_automation_activation_requires_separate_confirmation(self):
        route = MAIN[MAIN.index("async def try_local_ha_route") : MAIN.index("def runtime_tool_round_limit")]
        self.assertIn('pending_automation_store = globals().get("PENDING_AUTOMATION_CONFIRMATIONS", {})', route)
        self.assertIn('_activate_automation(pending_automation, "chat_confirmation")', route)
        self.assertIn("The automation remains saved as a disabled draft", route)

    def test_entity_mappings_are_persisted_and_reused_safely(self):
        self.assertIn('"entity_memory": []', MAIN)
        self.assertIn("def _automation_remember_entity", MAIN)
        self.assertIn("def automation_entity_memory_context", MAIN)
        self.assertIn("remembered automation mappings only as candidates and verify them", MAIN)
        self.assertIn('@app.delete("/api/automations/entity-memory/{memory_id}")', MAIN)

    def test_if_then_automation_cannot_route_as_immediate_control(self):
        intent = MAIN[MAIN.index("def is_home_assistant_priority_intent") : MAIN.index("def home_assistant_priority_tools")]
        self.assertIn("if is_automation_intent(message):", intent)
        self.assertIn("return False", intent)
        self.assertIn("def is_automation_intent", MAIN)
        self.assertIn("AUTOMATION BRAIN WORKFLOW IS ACTIVE", MAIN)

    def test_unapproved_entities_return_a_clear_http_error(self):
        self.assertIn("def _automation_payload_http", MAIN)
        self.assertIn("raise HTTPException(status_code=403, detail=str(exc))", MAIN)

    def test_practical_create_and_library_interface(self):
        for marker in (
            'data-automation-library-view="create"',
            'data-automation-library-view="saved"',
            'id="automation-chat-builder-form"',
            'id="automation-chat-request"',
            'id="automation-memory-list"',
            'data-auto-activate',
            'showLibraryView("saved")',
        ):
            self.assertIn(marker, INDEX)


if __name__ == "__main__":
    unittest.main()
