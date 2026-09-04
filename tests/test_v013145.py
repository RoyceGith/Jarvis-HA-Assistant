import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis" / "app" / "static" / "index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "flow.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis" / "app" / "static" / "css" / "automation-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013145FriendlyResultsTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.145")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.144")

    def test_optional_step_starts_with_a_plain_choice(self):
        self.assertIn("Different results", HTML)
        self.assertIn("Should this automation do something different in another situation?", WORKSPACE)
        self.assertIn("Most automations do not need this", WORKSPACE)
        self.assertIn("Add a different result", WORKSPACE)
        self.assertIn("automation-outcome-choice", CSS)

    def test_results_use_when_then_language_without_changing_schema(self):
        for phrase in (
            "Your different results",
            "Every check below is true",
            "At least one check below is true",
            "Name this result",
            "Add a task for this result",
        ):
            self.assertIn(phrase, WORKSPACE)
        for phrase in ("DIFFERENT RESULTS — FIRST MATCH WINS", "WHEN NO RESULT ABOVE MATCHES"):
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
