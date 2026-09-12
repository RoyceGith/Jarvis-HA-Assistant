from pathlib import Path
import json
import unittest

from zbrano.app.services import web_search


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "zbrano/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
WEB_SEARCH = (APP / "services/web_search.py").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "zbrano/Dockerfile").read_text(encoding="utf-8")
RUN_SCRIPT = (ROOT / "zbrano/run.sh").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class BrowserTestAndWebSearchBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.232"', CONFIG)
        self.assertIn('version="0.13.232"', MAIN)
        self.assertIn("HUD 0.13.232", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.232")

    def test_web_search_service_is_outside_composition_root(self):
        self.assertNotIn("def canonical_web_source_url(", MAIN)
        self.assertIn("def canonical_web_source_url(", WEB_SEARCH)
        self.assertIn("configure_web_search_service(", MAIN)

    def test_playwright_is_build_only_not_a_runtime_plugin(self):
        self.assertNotIn("playwright", MAIN.lower())
        self.assertNotIn("playwright", RUN_SCRIPT.lower())
        self.assertIn("node ./tests/browser_smoke.cjs", DOCKERFILE)
        self.assertIn("npm uninstall --global @playwright/mcp", DOCKERFILE)
        self.assertIn("apk del nodejs npm chromium", DOCKERFILE)

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
