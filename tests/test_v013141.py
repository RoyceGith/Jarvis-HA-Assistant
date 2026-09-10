import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis" / "app" / "static" / "index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis" / "app" / "static" / "css" / "automation-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013141AutomationStudioGuideTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.206")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.205")

    def test_numbered_steps_have_live_completion_states(self):
        for kind in ("details", "trigger", "context", "action", "decision"):
            self.assertIn(f'data-studio-step-status="{kind}"', HTML)
        for phrase in ("Needs attention", "Ready", "Optional — message only", "updateStudioGuide"):
            self.assertIn(phrase, WORKSPACE)
        self.assertIn("button[data-studio-node].is-complete small", CSS)
        self.assertIn("is-needs-attention", CSS)

    def test_common_messages_avoid_internal_vocabulary(self):
        for phrase in (
            "choose a device or sensor",
            "The extra action details have an invalid format",
            "% sure",
            "Waits ${item.cooldown_minutes} min before repeating",
            "Before running these tasks",
            "selected outcome",
        ):
            self.assertIn(phrase, WORKSPACE)

    def test_all_settings_remains_available(self):
        self.assertIn('id="automation-studio-advanced" type="button">All settings</button>', HTML)
        self.assertIn("All settings and ready-made designs", HTML)
        self.assertIn('class="automation-advanced"', HTML)


if __name__ == "__main__":
    unittest.main()
