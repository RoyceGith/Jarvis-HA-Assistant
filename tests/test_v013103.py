import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
STYLES = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class DirectFlowCardDeletionReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.142"', CONFIG)
        self.assertIn('version="0.13.142"', MAIN)
        self.assertIn("HUD 0.13.142", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.142")

    def test_exact_cards_have_direct_delete_controls(self):
        for marker in (
            "selectedFlowCard",
            "deleteFlowCard(kind,index,branchIndex=null)",
            "data-flow-delete-kind",
            "flowDeleteIndex",
            "clearPrimaryTrigger()",
            'workflowDraft.triggers.splice(index-1,1)',
            'workflowDraft.conditions.splice(signalIndex-signals.length,1)',
            'deleteBranchPath(index)',
            'workflowDraft.actions.splice(index-(primary?1:0),1)',
        ):
            self.assertIn(marker, WORKSPACE)

    def test_deletion_is_recoverable_and_accessible(self):
        self.assertIn("Use Undo to restore it.", WORKSPACE)
        self.assertIn('remove.setAttribute("aria-label",`Delete ${kind} card ${index+1}`)', WORKSPACE)
        self.assertIn(".automation-flow-card-delete", STYLES)
        self.assertIn("opacity:0", STYLES)
        self.assertIn("focus-within .automation-flow-card-actions", STYLES)

    def test_dense_and_narrow_canvases_keep_controls_reachable(self):
        self.assertIn("min-width:90px", STYLES)
        self.assertIn("@media (max-width:1250px)", STYLES)
        self.assertIn("minmax(0,1fr)", STYLES)

    def test_browser_covers_hover_delete_and_undo(self):
        self.assertIn('lastTriggerCard.locator(".automation-flow-card-delete").isVisible()', BROWSER)
        self.assertIn("Use Undo to restore", BROWSER)
        self.assertIn('temperatureCard.locator(".automation-flow-card-delete").click()', BROWSER)

    def test_release_history_includes_v013102(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.141")


if __name__ == "__main__":
    unittest.main()
