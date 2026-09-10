import json
from pathlib import Path
import unittest

from jarvis.app.services import workshop_approvals


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
KNOWLEDGE = (ROOT / "jarvis/app/services/knowledge_memory.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def call(call_id: str, name: str, content: str = "A useful memory") -> dict:
    return {
        "call_id": call_id,
        "name": name,
        "arguments": json.dumps({
            "content": content,
            "title": "",
            "preferred_area": "auto",
        }),
    }


class DirectMemorySaveReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workshop_approvals.configure_workshop_approvals(
            tool_permission_fn=lambda name: (
                "write" if name in {
                    "save_to_memory_database", "remember_automatically",
                    "write_memory_note", "create_memory_category", "gmail_create_draft",
                } else "read_only"
            ),
            gmail_write_calls_fn=lambda calls: [
                item for item in calls if item.get("name") == "gmail_create_draft"
            ],
        )

    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.204"', CONFIG)
        self.assertIn('version="0.13.204"', MAIN)
        self.assertIn("HUD 0.13.204", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.204")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.203")

    def test_explicit_save_authorizes_only_automatic_memory_database_calls(self):
        saves = [call("save-1", "save_to_memory_database")]
        self.assertTrue(workshop_approvals.explicit_memory_save_authorized(
            "Save this to the Memory Database", saves,
        ))
        self.assertTrue(workshop_approvals.explicit_memory_save_authorized(
            "Remember this for later", saves,
        ))
        self.assertFalse(workshop_approvals.explicit_memory_save_authorized(
            "What is in my Memory Database?", saves,
        ))
        for name in ("write_memory_note", "create_memory_category", "gmail_create_draft"):
            self.assertFalse(workshop_approvals.explicit_memory_save_authorized(
                "Save this to the Memory Database", [call("unsafe", name)],
            ))

    def test_large_save_notice_reports_one_upfront_phase_count(self):
        calls = [
            call("save-1", "save_to_memory_database", "a" * 21_000),
            call("save-2", "save_to_memory_database", "b" * 21_000),
        ]
        notice = workshop_approvals.memory_save_phase_notice(calls)
        self.assertIn("2 bounded phases", notice)
        self.assertIn("without asking for approval again", notice)
        self.assertEqual(
            workshop_approvals.memory_save_phase_notice([calls[0]]),
            "",
        )

    def test_runtime_gate_and_tool_schema_keep_the_boundary_bounded(self):
        self.assertEqual(MAIN.count("explicit_memory_save_authorized("), 3)
        self.assertIn("memory_phase_notice_sent", MAIN)
        self.assertIn('"maxLength": 40000', KNOWLEDGE)
        self.assertIn("Other advertised tools", MAIN)


if __name__ == "__main__":
    unittest.main()
