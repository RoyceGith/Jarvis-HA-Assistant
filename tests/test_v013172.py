import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
ONBOARDING = (ROOT / "jarvis/app/static/js/onboarding.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/onboarding.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class InstallationReadinessReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.212"', CONFIG)
        self.assertIn('version="0.13.212"', MAIN)
        self.assertIn("HUD 0.13.212", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.212")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.211")

    def test_report_combines_live_setup_storage_and_automation_health(self):
        for marker in (
            "storage_ready = DATA_DIR.exists()",
            "_automation_readiness(automation, automation_data)",
            "_automation_failure_circuit(automation, time.time())",
            '"installation_report"',
            '"support_summary": support_summary',
            '"title": "Persistent storage"',
            '"title": "Backup and restore"',
            '"title": "Automation safety"',
        ):
            self.assertIn(marker, MAIN)

    def test_support_payload_has_explicit_privacy_boundary(self):
        report_source = MAIN[MAIN.index("storage_ready = DATA_DIR.exists()"):MAIN.index('@app.get("/api/onboarding")')]
        for private_marker in ("OPENAI_API_KEY", "SUPERVISOR_TOKEN", "entity_id", "messages"):
            self.assertNotIn(private_marker, report_source)
        self.assertIn("excludes keys, tokens, entity IDs, messages, and personal data", ONBOARDING)

    def test_completed_setup_can_copy_download_and_refresh_report(self):
        for marker in (
            "function installationReportElement(data)",
            "copyInstallationSummary",
            "Copy support summary",
            "Download report",
            "Refresh report",
        ):
            self.assertIn(marker, ONBOARDING)
        self.assertIn(".onboarding-installation-report", CSS)
        self.assertIn(".onboarding-report-actions", CSS)
        self.assertIn("Installation report · Ready", BROWSER)
        self.assertIn("Download report", BROWSER)


if __name__ == "__main__":
    unittest.main()
