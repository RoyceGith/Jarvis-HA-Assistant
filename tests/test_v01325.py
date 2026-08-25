from pathlib import Path
import json
import unittest

from jarvis.app.domains import conversations


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
CONVERSATIONS = (APP / "domains/conversations.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ConversationsDomainBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.38"', CONFIG)
        self.assertIn('version="0.13.38"', MAIN)
        self.assertIn("HUD 0.13.38", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.38")

    def test_conversation_store_is_outside_composition_root(self):
        self.assertNotIn("def persist_chat_sessions(", MAIN)
        self.assertNotIn("def append_chat_message(", MAIN)
        self.assertIn("def persist_chat_sessions(", CONVERSATIONS)
        self.assertIn("def append_chat_message(", CONVERSATIONS)
        self.assertIn('CHAT_STORAGE_PATH = Path("/data/chat_sessions.json")', CONVERSATIONS)

    def test_attachment_public_and_model_contract_is_preserved(self):
        content = (
            "Please inspect this"
            + conversations.ATTACHMENT_CONTEXT_MARKER
            + "File: report.txt (id=0123456789abcdef01234567, scope=chat, type=text/plain, bytes=42)\nBody"
        )
        visible, attachments = conversations._attachment_message_parts(content)
        self.assertEqual(visible, "Please inspect this")
        self.assertEqual(attachments[0]["file_id"], "0123456789abcdef01234567")
        self.assertEqual(attachments[0]["size"], 42)

    def test_shared_state_and_callbacks_are_explicit(self):
        import_block = MAIN.split("from .domains.conversations import (", 1)[1].split(")", 1)[0]
        for name in ("CHAT_SESSIONS", "CHAT_SESSION_META", "CHAT_SESSION_ORDER"):
            self.assertIn(name, import_block)
        self.assertIn("configure_conversations_domain(", MAIN)
        self.assertIn("schedule_fast_memory_extraction_fn=schedule_fast_memory_extraction", MAIN)


if __name__ == "__main__":
    unittest.main()
