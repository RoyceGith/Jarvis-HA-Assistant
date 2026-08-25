from pathlib import Path
import ast
import asyncio
import json
import unittest
from tests.frontend_source import load_frontend_source
from tests.backend_source import load_backend_source


ROOT = Path(__file__).resolve().parents[1]
MAIN = load_backend_source()
INDEX = load_frontend_source()
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_functions(*names):
    tree = ast.parse(MAIN)
    selected = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    namespace = {
        "Any": object,
        "MCPError": RuntimeError,
        "httpx": type("Httpx", (), {"HTTPError": RuntimeError}),
        "re": __import__("re"),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), "jarvis/app/main.py", "exec"), namespace)
    return namespace


class ReleaseMemoryWriteVerificationTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.30"', CONFIG)
        self.assertIn('version="0.13.30"', MAIN)
        self.assertIn("HUD 0.13.30", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.30")

    def test_plain_and_structured_statuses_are_recognized(self):
        status = load_functions("release_sync_write_status")["release_sync_write_status"]
        self.assertEqual(status({"status": "replaced"}), "replaced")
        self.assertEqual(status({"structuredContent": {"status": "UPDATED"}}), "updated")
        self.assertEqual(status({"result": {"status": "ok"}}), "ok")
        self.assertEqual(status({"text": "write complete"}), "")

    def test_read_back_comparison_tolerates_only_newline_policy(self):
        matches = load_functions("release_sync_content_matches")["release_sync_content_matches"]
        self.assertTrue(matches("# Release\r\n", "# Release"))
        self.assertFalse(matches("# Release\nold", "# Release\nnew"))

    def test_ambiguous_write_uses_uncached_exact_read_back(self):
        self.assertIn("async def confirm_release_note_write", MAIN)
        self.assertIn('"read_project_note",\n            {"relative_path": relative_path}', MAIN)
        self.assertIn("release_sync_content_matches(verified.get(\"content\"), expected_content)", MAIN)
        self.assertIn("await confirm_release_note_write(result, relative_path, updated)", MAIN)
        self.assertNotIn("unexpected write status: {status or 'missing'}", MAIN)

        functions = load_functions(
            "workshop_result_error",
            "release_sync_write_status",
            "release_sync_content_matches",
            "confirm_release_note_write",
        )

        async def read_back(tool_name, arguments):
            self.assertEqual(tool_name, "read_project_note")
            self.assertEqual(arguments["relative_path"], "ZBRANO/Release and Change Log.md")
            return {"content": "# Releases\n\nupdated\n"}

        functions["confirm_release_note_write"].__globals__["call_workshop_memory_tool_uncached"] = read_back
        confirmed = asyncio.run(functions["confirm_release_note_write"](
            {"text": "write completed"},
            "ZBRANO/Release and Change Log.md",
            "# Releases\n\nupdated",
        ))
        self.assertEqual(confirmed, "verified")

    def test_prior_canonical_release_descriptions_are_backfilled_in_order(self):
        records = MANIFEST["history_backfill"]
        self.assertEqual([item["version"] for item in records], [f"0.13.{index}" for index in range(30)])
        self.assertTrue(all(item["summary"] for item in records))
        functions = load_functions("release_marker", "render_release_history_backfill")
        entries = functions["render_release_history_backfill"](MANIFEST)
        self.assertEqual(len(entries), 30)
        self.assertIn("zbrano-release:0.13.0", entries[0])
        self.assertIn("zbrano-release:0.13.29", entries[-1])
        self.assertIn("reconcile_release_history_backfill(updated, manifest)", MAIN)


if __name__ == "__main__":
    unittest.main()
