import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis" / "app" / "static" / "index.html").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "flow.js").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013139FriendlyAutomationStudioTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.193")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.192")

    def test_flow_remains_central_with_numbered_steps(self):
        self.assertIn('id="automation-studio-canvas"', HTML)
        for label in ("Setup &amp; safety", "WHEN · Events", "IF · Conditions", "THEN · Actions", "ELSE IF"):
            self.assertIn(f"<strong>{label}</strong>", HTML)
        self.assertIn("Click any card to change it", HTML)

    def test_cards_use_icons_symbols_and_plain_branch_language(self):
        self.assertIn("automation-flow-entity-icon", FLOW)
        self.assertIn('above:">"', FLOW)
        self.assertIn('below:"<"', FLOW)
        self.assertNotIn("WATCH ${", FLOW)
        self.assertIn("ELSE IF", FLOW)

    def test_technical_settings_have_friendly_labels(self):
        for label in (
            "How sure should ZBRANO be?",
            "Wait before offering again (minutes)",
            "Offer again if the reading worsens by",
            "Ready for a new alert after the reading improves by",
        ):
            self.assertIn(label, WORKSPACE)


if __name__ == "__main__":
    unittest.main()
