import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "zbrano" / "app" / "static" / "index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano" / "app" / "static" / "js" / "automations" / "flow.js").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano" / "app" / "static" / "css" / "automation-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano" / "release_manifest.json").read_text(encoding="utf-8"))


class V013145FriendlyResultsTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.218")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.217")

    def test_optional_step_starts_with_a_plain_choice(self):
        self.assertIn("ELSE IF", HTML)
        self.assertIn("Add an ELSE IF path", WORKSPACE)
        self.assertIn("current IF conditions and THEN actions become the first path", WORKSPACE)
        self.assertIn("Add ELSE IF", WORKSPACE)
        self.assertIn("automation-outcome-choice", CSS)

    def test_results_use_when_then_language_without_changing_schema(self):
        for phrase in (
            "IF / ELSE IF paths",
            "Write what ZBRANO should say",
            "Send this message",
            "Show in ZBRANO notifications",
        ):
            self.assertIn(phrase, WORKSPACE)
        for phrase in ("IF / ELSE IF — FIRST MATCH RUNS", "WHEN NO PATH ABOVE MATCHES"):
            self.assertIn(phrase, FLOW)
        self.assertIn('conditions:[newBranchCondition()]', WORKSPACE)
        self.assertIn("branches:workflowDraft.branches", WORKSPACE)

    def test_existing_advanced_controls_have_friendlier_explanations(self):
        for phrase in (
            "Main message from ZBRANO",
            "Offer again if the reading worsens by",
            "Ready for a new alert after the reading improves by",
        ):
            self.assertIn(phrase, WORKSPACE)


if __name__ == "__main__":
    unittest.main()
