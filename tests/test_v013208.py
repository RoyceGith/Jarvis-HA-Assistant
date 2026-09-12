import json
from pathlib import Path
import tempfile
import unittest

from zbrano.app.services import knowledge_memory


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
STUDIO = (ROOT / "zbrano/app/static/js/memory/studio.js").read_text(encoding="utf-8")
MEMORY_CSS = (ROOT / "zbrano/app/static/css/memory-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class FormattedMemoryNotesReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.228"', CONFIG)
        self.assertIn('version="0.13.228"', MAIN)
        self.assertIn("HUD 0.13.228", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.228")
        self.assertEqual(MANIFEST["history_backfill"][-21]["version"], "0.13.207")

    def test_existing_notes_include_an_updated_timestamp(self):
        original_root = knowledge_memory.KNOWLEDGE_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            try:
                knowledge_memory.configure_knowledge_memory(root=Path(temporary))
                knowledge_memory.create_memory_space("Recipes", "Food", "blank", "Food")
                knowledge_memory.write_memory_note("Recipes", "Soups", "# Soups\n\n**Beef**", "create")
                listed = knowledge_memory.list_memory_notes("Recipes")
                opened = knowledge_memory.read_memory_note("Recipes", "Soups")
                self.assertGreater(listed["note_details"][0]["updated_at"], 0)
                self.assertGreater(opened["updated_at"], 0)
            finally:
                knowledge_memory.configure_knowledge_memory(root=original_root)

    def test_memory_uses_chat_markdown_in_read_and_print_views(self):
        self.assertIn('typeof renderMarkdownText === "function"', STUDIO)
        self.assertIn('id="memory-note-rendered"', STUDIO)
        self.assertIn('id="memory-edit-note"', STUDIO)
        self.assertIn("Last updated ${formatNoteDate(payload.updated_at)}", STUDIO)
        self.assertIn("content.innerHTML = renderMemoryMarkdown", STUDIO)
        self.assertIn(".memory-note-rendered strong{font-weight:750}", MEMORY_CSS)


if __name__ == "__main__":
    unittest.main()
