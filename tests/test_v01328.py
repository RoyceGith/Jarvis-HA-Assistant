import ast
from pathlib import Path
import json
import re
import unittest
from typing import Any
from urllib.parse import urlsplit

from jarvis.app.services import web_search


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
PLAYWRIGHT = (APP / "services/playwright_bridge.py").read_text(encoding="utf-8")
WEB_SEARCH = (APP / "services/web_search.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_playwright_functions(*names: str) -> dict[str, Any]:
    tree = ast.parse(PLAYWRIGHT)
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace = {
        "Any": Any,
        "re": re,
        "urlsplit": urlsplit,
        "PLAYWRIGHT_LOCAL_ORIGIN": "http://127.0.0.1:8099",
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<playwright>", "exec"), namespace)
    return namespace


class PlaywrightAndWebSearchBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.46"', CONFIG)
        self.assertIn('version="0.13.46"', MAIN)
        self.assertIn("HUD 0.13.46", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.46")

    def test_both_services_are_outside_composition_root(self):
        self.assertNotIn("def _playwright_local_url(", MAIN)
        self.assertNotIn("def canonical_web_source_url(", MAIN)
        self.assertIn("def _playwright_local_url(", PLAYWRIGHT)
        self.assertIn("def canonical_web_source_url(", WEB_SEARCH)
        self.assertIn("configure_playwright_bridge(", MAIN)
        self.assertIn("configure_web_search_service(", MAIN)

    def test_playwright_remains_local_only_and_redacts_evidence(self):
        namespace = load_playwright_functions("_playwright_local_url", "playwright_redact_evidence")
        self.assertEqual(namespace["_playwright_local_url"]("/settings"), "http://127.0.0.1:8099/settings")
        for rejected in ("https://example.com", "/settings?token=x", "/../data", r"/settings\escape"):
            with self.assertRaises(ValueError):
                namespace["_playwright_local_url"](rejected)
        redacted = namespace["playwright_redact_evidence"](
            "Authorization=secret Bearer abc123 cookie=value",
            limit=200,
        )
        self.assertNotIn("abc123", redacted)
        self.assertNotIn("secret", redacted)
        self.assertNotIn("value", redacted)

    def test_web_sources_are_normalized_and_citations_take_priority(self):
        normalized = web_search.canonical_web_source_url(
            "https://Example.COM/article/?utm_source=test&keep=yes#fragment"
        )
        self.assertEqual(normalized, "https://example.com/article?keep=yes")
        response = {
            "output": [
                {"type": "web_search_call", "action": {"sources": [{"url": "https://fallback.example/a"}]}},
                {"content": [{"annotations": [{
                    "type": "url_citation",
                    "url": "https://official.example/doc?utm_campaign=x",
                    "title": "Official",
                }]}]},
            ],
        }
        self.assertEqual(web_search.response_web_sources(response), [{
            "url": "https://official.example/doc",
            "title": "Official",
        }])

    def test_web_search_preferences_and_forced_choice_are_preserved(self):
        original_developer = web_search.developer_mode_enabled
        original_preferences = web_search.load_preferences
        try:
            web_search.configure_web_search_service(
                developer_mode_enabled_fn=lambda: False,
                load_preferences_fn=lambda: {
                    "web_search_enabled": True,
                    "web_search_context_size": "high",
                },
            )
            self.assertEqual(web_search.native_web_search_tool(), {
                "type": "web_search",
                "search_context_size": "high",
            })
            self.assertEqual(web_search.web_search_tool_choice("search"), {"type": "web_search"})
        finally:
            web_search.developer_mode_enabled = original_developer
            web_search.load_preferences = original_preferences


if __name__ == "__main__":
    unittest.main()
