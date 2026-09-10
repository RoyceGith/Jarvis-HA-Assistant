import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "jarvis/app/static/js/core.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class FinalConversationDeletionReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.209"', CONFIG)
        self.assertIn('version="0.13.209"', MAIN)
        self.assertIn("HUD 0.13.209", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.209")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.208")

    def test_last_deleted_row_is_removed_before_draft_is_rendered(self):
        self.assertIn('if (!listResponse.ok) throw new Error', CORE)
        self.assertIn('chatList.innerHTML = "";\n    await createNewChat();', CORE)
        self.assertLess(
            CORE.index('chatList.innerHTML = "";\n    await createNewChat();'),
            CORE.index("newChatButton.addEventListener", CORE.index("async function deleteChat")),
        )

    def test_browser_replays_the_one_chat_delete_sequence(self):
        self.assertIn('session_id: "only-saved-chat"', BROWSER)
        self.assertIn("browserChatFixture = browserChatFixture.filter", BROWSER)
        self.assertIn('assert.equal(await page.locator("#chat-list .chat-list-item").count(), 1)', BROWSER)
        self.assertIn('assert.equal(await page.locator("#chat-list").innerText(), "New chat")', BROWSER)
        self.assertIn("assert.equal(browserChatFixture.length, 0)", BROWSER)


if __name__ == "__main__":
    unittest.main()
