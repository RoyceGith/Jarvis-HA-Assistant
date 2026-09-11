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


class InteractiveFlowCardReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.214"', CONFIG)
        self.assertIn('version="0.13.214"', MAIN)
        self.assertIn("HUD 0.13.214", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.214")

    def test_cards_support_exact_insertion_and_same_stage_movement(self):
        for marker in (
            "draggedFlowCard",
            "moveFlowCard(kind,fromIndex,insertionIndex)",
            "addStudioBlock(kind,insertionIndex=null)",
            'flowDropPosition(event,sourceKind="")',
            'target&&target.kind===kind?target.index:null',
            'source.kind===target.kind',
        ):
            self.assertIn(marker, WORKSPACE)

    def test_primary_fields_are_normalized_without_losing_task_identity(self):
        for marker in (
            "primaryTriggerValue()",
            "writePrimaryTrigger(item={})",
            "primaryActionValue()",
            "writeFlowSequence(kind,items)",
            '!first?.task_template||first.task_template==="service"',
        ):
            self.assertIn(marker, WORKSPACE)

    def test_repeatable_cards_have_discreet_duplicate_controls(self):
        self.assertIn("duplicateFlowCard(kind,index,branchIndex=null)", WORKSPACE)
        self.assertIn("data-flow-duplicate-kind", WORKSPACE)
        self.assertIn("Presence is a unique context rule", WORKSPACE)
        self.assertIn(".automation-flow-card-actions", STYLES)
        self.assertIn(".automation-flow-card-duplicate", STYLES)
        self.assertIn("opacity:0", STYLES)

    def test_drop_target_and_browser_behavior_are_covered(self):
        self.assertIn(".is-drop-before::before", STYLES)
        self.assertIn(".is-drop-after::before", STYLES)
        self.assertIn('middleTriggerCard.locator(".automation-flow-card-duplicate")', BROWSER)
        self.assertIn("Flow card moved", BROWSER)
        self.assertIn("last_trigger", BROWSER)
        self.assertIn("Choose a device or sensor", BROWSER)

    def test_release_history_includes_v013103(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.213")


if __name__ == "__main__":
    unittest.main()
