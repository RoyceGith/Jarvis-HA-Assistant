from pathlib import Path
import ast
import json
import re
import time
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
    namespace = {"Any": object, "MCPError": RuntimeError, "json": json, "re": re, "time": time}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "jarvis/app/main.py", "exec"), namespace)
    return namespace


class ReleaseMemoryProtocolAndCompactionTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.20"', CONFIG)
        self.assertIn('version="0.13.20"', MAIN)
        self.assertIn("HUD 0.13.20", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.20")

    def test_decoder_prefers_structured_content(self):
        decode = load_functions("decode_workshop_tool_result")["decode_workshop_tool_result"]
        result = decode({
            "isError": False,
            "content": [{"type": "text", "text": '{"status":"old"}'}],
            "structuredContent": {"status": "replaced", "size_bytes": 42},
        })
        self.assertEqual(result, {"status": "replaced", "size_bytes": 42})

    def test_decoder_surfaces_tool_error_text(self):
        decode = load_functions("decode_workshop_tool_result")["decode_workshop_tool_result"]
        with self.assertRaisesRegex(RuntimeError, "larger than 1 MB"):
            decode({
                "isError": True,
                "content": [{"type": "text", "text": "Project note is larger than 1 MB."}],
            })

    def test_managed_release_blocks_are_compacted_without_touching_legacy_history(self):
        functions = load_functions(
            "release_marker",
            "render_release_history_backfill",
            "insert_release_history",
            "upsert_marked_release_history_entry",
            "reconcile_release_history_backfill",
        )
        source = """# Release Log

## Release History

<!-- zbrano-release:0.13.12 -->
### v0.13.12 — Installed previously

#### New features
- huge repeated detail

### v0.12.112 — Legacy release
- preserve this unmarked history exactly
"""
        compacted = functions["reconcile_release_history_backfill"](source, MANIFEST)
        self.assertNotIn("huge repeated detail", compacted)
        self.assertIn("### v0.12.112 — Legacy release", compacted)
        self.assertIn("preserve this unmarked history exactly", compacted)
        self.assertEqual(compacted.count("<!-- zbrano-release:0.13.12 -->"), 1)
        self.assertEqual(compacted.count("<!-- zbrano-release:0.13.13 -->"), 1)

    def test_current_entry_uses_release_specific_details(self):
        functions = load_functions("release_marker", "render_release_entry")
        entry = functions["render_release_entry"](MANIFEST)
        self.assertIn(MANIFEST["release_entry"]["features"][0], entry)
        self.assertIn(MANIFEST["release_entry"]["fixes"][0], entry)
        self.assertNotIn("Import the Home Assistant Label registry", entry)


if __name__ == "__main__":
    unittest.main()
