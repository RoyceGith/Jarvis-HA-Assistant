import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "zbrano/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "zbrano/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class PerBranchMessageDeliveryReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.242")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.241")

    def test_branch_schema_and_normalization_store_delivery_choices(self):
        for field in ("delivery_voice", "delivery_notification_center", "delivery_ha_push"):
            self.assertIn(f"{field}: bool | None = None", SCHEMAS)
            self.assertIn(f'"{field}": (payload.get("{field}", True)', AUTOMATIONS)

    def test_runtime_uses_the_selected_branch_delivery(self):
        self.assertIn("def _automation_branch_delivery", AUTOMATIONS)
        self.assertIn('_automation_branch_delivery(item, branch_name, "delivery_voice")', AUTOMATIONS)
        self.assertIn('elif suggestion["delivery_ha_push"]:', AUTOMATIONS)

    def test_message_inspector_owns_plainly_named_delivery_controls(self):
        for phrase in (
            "Say this message aloud",
            "Show in ZBRANO notifications",
            "Send to Home Assistant notifications",
        ):
            self.assertIn(phrase, HTML)
            self.assertIn(phrase, WORKSPACE)
        self.assertIn("data-branch-delivery", WORKSPACE)
        self.assertIn("branchDeliveryDefaults", WORKSPACE)

    def test_redundant_path_mode_is_removed_and_checks_use_and(self):
        self.assertNotIn("This path runs when", WORKSPACE)
        self.assertNotIn("data-branch-mode", WORKSPACE)
        self.assertIn('logic("all",false,"branch",bi)', FLOW)

    def test_browser_checks_independent_branch_settings(self):
        self.assertIn("[data-branch-delivery]').count(), 3", BROWSER)
        self.assertIn('data-branch-delivery="delivery_voice"', BROWSER)
        self.assertIn("This path runs when", BROWSER)


if __name__ == "__main__":
    unittest.main()
