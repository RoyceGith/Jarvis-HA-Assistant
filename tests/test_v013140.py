import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis" / "app" / "static" / "index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis" / "app" / "static" / "css" / "automation-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013140AutomationStudioUsabilityTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.178")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.177")

    def test_repeatable_cards_explain_their_fields(self):
        for label in (
            "Start when",
            "Device or sensor",
            "Change to watch for",
            "Compared with",
            "Keep this state for (seconds)",
            "Stop waiting after (seconds)",
            "Where to send it",
            "Target temperature",
        ):
            self.assertIn(label, WORKSPACE)
        self.assertIn("friendlyTriggerStepHtml", WORKSPACE)

    def test_advanced_controls_use_progressive_disclosure(self):
        self.assertIn("Fine-tune timing and confidence", WORKSPACE)
        self.assertIn("Safety limits and advanced details", WORKSPACE)
        self.assertIn("automation-inspector-more", CSS)
        for field in (
            "automation-confidence",
            "automation-cooldown",
            "automation-action-data",
            "automation-failure-limit",
        ):
            self.assertIn(field, WORKSPACE)

    def test_toolbar_and_paths_use_clear_action_language(self):
        for label in ("New automation", "Try it safely", "Save automation"):
            self.assertIn(f">{label}</button>", HTML)
        self.assertIn('name:"ELSE IF"', WORKSPACE)
        self.assertNotIn('name:`Branch ${workflowDraft.branches.length+1}`', WORKSPACE)


if __name__ == "__main__":
    unittest.main()
