import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
STYLES = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))
READMES = [
    (ROOT / "README.md").read_text(encoding="utf-8"),
    (ROOT / "zbrano/README.md").read_text(encoding="utf-8"),
    (ROOT / "distribution/public-repository/README.md").read_text(encoding="utf-8"),
    (ROOT / "distribution/public-repository/zbrano/README.md").read_text(encoding="utf-8"),
]


class AutomationStudioBuildRepairTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.232"', CONFIG)
        self.assertIn('version="0.13.232"', MAIN)
        self.assertIn("HUD 0.13.232", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.232")

    def test_decorative_connectors_do_not_intercept_flow_nodes(self):
        rule = next(rule for rule in STYLES.splitlines() if rule.startswith(".automation-flow-stage-connector {"))
        self.assertIn("pointer-events: none", rule)
        node_rule = next(rule for rule in STYLES.splitlines() if rule.startswith(".automation-flow-node {"))
        self.assertIn("z-index: 1", node_rule)
        self.assertIn('panel.addEventListener("pointerdown"', WORKSPACE)

    def test_release_history_and_readmes_are_current(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.231")
        for readme in READMES:
            self.assertIn("0.13.232", readme)


if __name__ == "__main__":
    unittest.main()
