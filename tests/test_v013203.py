import json
from pathlib import Path
import tempfile
import unittest

from jarvis.app.services import knowledge_memory, workshop_approvals


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
STUDIO = (ROOT / "jarvis/app/static/js/memory/studio.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class OrganizedMemorySaveReleaseTests(unittest.TestCase):
    def setUp(self):
        self.original_root = knowledge_memory.KNOWLEDGE_ROOT
        self.temporary = tempfile.TemporaryDirectory()
        knowledge_memory.configure_knowledge_memory(root=Path(self.temporary.name))
        workshop_approvals.PENDING_MEMORY_ORGANIZATION.clear()
        workshop_approvals.configure_workshop_approvals(
            tool_permission_fn=lambda name: "write" if name == "save_to_memory_database" else "read_only",
            gmail_write_calls_fn=lambda calls: [],
        )

    def tearDown(self):
        knowledge_memory.configure_knowledge_memory(root=self.original_root)
        workshop_approvals.PENDING_MEMORY_ORGANIZATION.clear()
        self.temporary.cleanup()

    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.206"', CONFIG)
        self.assertIn('version="0.13.206"', MAIN)
        self.assertIn("HUD 0.13.206", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.206")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.205")

    def test_soup_recipes_get_a_descriptive_topic_note(self):
        suggested = knowledge_memory.remember_automatically(
            "Two winter beef soup recipes with stock, carrots, and barley.",
            "Winter soups",
        )
        self.assertTrue(suggested["choice_required"])
        saved = knowledge_memory.remember_automatically(
            "Two winter beef soup recipes with stock, carrots, and barley.",
            "Winter soups", organization="append_existing", destination_note="Soup Recipes.md",
        )
        self.assertTrue(saved["saved"])
        self.assertEqual(saved["note"], "Soup Recipes.md")
        self.assertEqual(saved["confirmation"], "Saved in Food & Recipes → Soup Recipes")

    def test_existing_collection_offers_append_or_narrower_collection(self):
        knowledge_memory.remember_automatically(
            "Chicken soup recipe with rice.", organization="append_existing", destination_note="Soup Recipes.md",
        )
        pending = knowledge_memory.remember_automatically("Beef soup recipe with barley.")
        self.assertFalse(pending["saved"])
        self.assertTrue(pending["choice_required"])
        self.assertEqual(pending["existing_note"], "Soup Recipes.md")
        self.assertEqual(pending["new_note"], "Beef Soup Recipes.md")

    def test_only_an_offered_followup_destination_inherits_save_authorization(self):
        initial_call = {
            "call_id": "initial",
            "name": "save_to_memory_database",
            "arguments": json.dumps({
                "content": "Beef soup recipe with barley.", "title": "Beef soup",
                "preferred_area": "auto", "organization": "auto", "destination_note": "",
            }),
        }
        result = {
            "choice_required": True,
            "choices": [{"id": "create_new", "destination_note": "Beef Soup Recipes.md"}],
        }
        workshop_approvals.remember_memory_organization_choice("chat", initial_call, result)
        selected = json.loads(initial_call["arguments"])
        selected.update({"organization": "create_new", "destination_note": "Beef Soup Recipes.md"})
        selected_call = {**initial_call, "call_id": "selected", "arguments": json.dumps(selected)}
        self.assertTrue(workshop_approvals.memory_organization_choice_authorized("chat", [selected_call]))
        selected_call["arguments"] = json.dumps({**selected, "destination_note": "Other note.md"})
        self.assertFalse(workshop_approvals.memory_organization_choice_authorized("chat", [selected_call]))

    def test_memory_studio_renders_the_same_one_time_choice(self):
        self.assertIn("Choose how to organize this memory", STUDIO)
        self.assertIn("data-memory-organization", STUDIO)
        self.assertIn("destination_note:destinationNote", STUDIO)


if __name__ == "__main__":
    unittest.main()
