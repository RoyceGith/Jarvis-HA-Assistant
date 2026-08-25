from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
RELEASE_SYNC = (ROOT / "jarvis/app/domains/release_sync.py").read_text(encoding="utf-8")
CORE = (ROOT / "jarvis/app/static/js/core.js").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ReleaseSyncTerminalStateTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.32"', CONFIG)
        self.assertIn('version="0.13.32"', MAIN)
        self.assertIn("HUD 0.13.32", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.32")

    def test_worker_has_bounded_total_runtime_and_unexpected_exception_recovery(self):
        self.assertIn("RELEASE_SYNC_WORKER_TIMEOUT_SECONDS = 300", RELEASE_SYNC)
        self.assertIn("await asyncio.wait_for(\n            _release_sync_worker_attempts(),", RELEASE_SYNC)
        self.assertIn("except Exception as exc:", RELEASE_SYNC)
        self.assertIn("Release synchronization exceeded", RELEASE_SYNC)

    def test_inactive_transient_worker_becomes_failed(self):
        self.assertIn('status.get("state") in {"pending", "synchronizing", "retrying"}', RELEASE_SYNC)
        self.assertIn("and not status[\"task_active\"]", RELEASE_SYNC)
        self.assertIn("worker stopped before reaching a terminal state", RELEASE_SYNC)

    def test_note_progress_is_reported_and_diagnosable(self):
        self.assertIn('"current_note": note_name', RELEASE_SYNC)
        self.assertIn('"note_progress": f"{note_index}/{len(note_names)}"', RELEASE_SYNC)
        self.assertIn("task_active={payload.get('task_active')}", MAIN)
        self.assertIn("current_note={payload.get('current_note')}", MAIN)

    def test_frontend_polls_only_while_work_is_non_terminal(self):
        self.assertIn("let releaseMemorySyncPollTimer = 0", CORE)
        self.assertIn('["pending", "synchronizing", "retrying"].includes(status.state)', CORE)
        self.assertIn("window.setTimeout(refreshReleaseSyncStatus, 2500)", CORE)
        self.assertIn('[status.note_progress, status.current_note]', CORE)


if __name__ == "__main__":
    unittest.main()
