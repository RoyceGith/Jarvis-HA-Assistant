import json
from pathlib import Path
import unittest

from jarvis.app.services import mcp_approvals, tool_progress, workshop_approvals


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
WORKSHOP = (APP / "services/workshop_approvals.py").read_text(encoding="utf-8")
MCP = (APP / "services/mcp_approvals.py").read_text(encoding="utf-8")
PROGRESS = (APP / "services/tool_progress.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ApprovalAndToolProgressBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.38"', CONFIG)
        self.assertIn('version="0.13.38"', MAIN)
        self.assertIn("HUD 0.13.38", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.38")

    def test_three_services_are_outside_composition_root_and_configured(self):
        self.assertNotIn("def workshop_memory_approval_decision(", MAIN)
        self.assertNotIn("def mcp_approval_decision(", MAIN)
        self.assertNotIn("def openai_tool_activity(", MAIN)
        self.assertIn("def workshop_memory_approval_decision(", WORKSHOP)
        self.assertIn("def mcp_approval_decision(", MCP)
        self.assertIn("def openai_tool_activity(", PROGRESS)
        for marker in (
            "configure_workshop_approvals(", "configure_mcp_approvals(",
            "configure_tool_progress(",
        ):
            self.assertIn(marker, MAIN)

    def test_workshop_approval_decisions_redaction_and_pending_state(self):
        workshop_approvals.configure_workshop_approvals(
            tool_permission_fn=lambda name: "write" if name == "replace_note" else "read_only",
            gmail_write_calls_fn=lambda calls: [],
        )
        self.assertEqual(workshop_approvals.workshop_memory_approval_decision("approve task"), "task")
        self.assertEqual(workshop_approvals.workshop_memory_approval_decision("cancel"), "deny")
        summary = workshop_approvals.summarize_workshop_memory_arguments({
            "relative_path": "Project.md",
            "content": "# Private note\n" + ("sensitive " * 100),
        })
        self.assertIn("note content:", summary)
        self.assertNotIn("sensitive sensitive", summary)
        calls = [{"call_id": "call-1", "name": "replace_note", "arguments": "{}"}]
        prompt = workshop_approvals.store_workshop_memory_approval("chat", "response", calls)
        self.assertIn("approve task", prompt)
        self.assertEqual(workshop_approvals.PENDING_WORKSHOP_APPROVALS["chat"]["response_id"], "response")
        self.assertEqual(workshop_approvals.workshop_write_call_ids(calls), {"call-1"})

    def test_mcp_provider_summary_prompt_and_progress_contracts(self):
        mcp_approvals.configure_mcp_approvals(
            plugin_registry_fn=lambda: {"github": {"name": "GitHub"}},
        )
        request = {
            "type": "mcp_approval_request",
            "id": "approval-1",
            "server_label": "plugin_github",
            "name": "execute_request",
            "arguments": json.dumps({"method": "post", "path": "/repos/example/issues"}),
        }
        self.assertTrue(mcp_approvals.mcp_approval_decision("approve"))
        self.assertFalse(mcp_approvals.mcp_approval_decision("deny"))
        self.assertEqual(mcp_approvals.mcp_approval_plugin_id(request), "github")
        self.assertEqual(
            mcp_approvals.mcp_approval_summary(request),
            "GitHub · POST /repos/example/issues",
        )
        self.assertIn("No action has run", mcp_approvals.mcp_approval_prompt([request]))

        tool_progress.configure_tool_progress(
            gmail_direct_tool_names={"gmail_search"},
            gmail_plugin_id_fn=lambda: "gmail",
        )
        activity = tool_progress.openai_tool_activity({
            "type": "response.output_item.added", "item": request,
        })
        self.assertEqual(activity["state"], "waiting_approval")
        self.assertEqual(activity["plugin_id"], "github")
        self.assertEqual(
            tool_progress.local_tool_activity(["gmail_search"])["label"],
            "Reading Gmail",
        )
        self.assertIn("longer than expected", tool_progress._tool_progress_phases([])[-1])


if __name__ == "__main__":
    unittest.main()
