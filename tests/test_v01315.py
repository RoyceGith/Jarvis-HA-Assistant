from pathlib import Path
import json
import re
import unittest

from tests.backend_source import load_backend_source
from tests.frontend_source import load_frontend_source


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
STATIC = APP / "static"
MAIN_RAW = (APP / "main.py").read_text(encoding="utf-8")
BACKEND = load_backend_source()
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
FRONTEND = load_frontend_source()
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class CanonicalModuleArchitectureTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.49"', CONFIG)
        self.assertIn('version="0.13.49"', MAIN_RAW)
        self.assertIn("HUD 0.13.49", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.49")

    def test_frontend_is_directly_split_with_stable_order(self):
        stylesheet_paths = re.findall(r'<link[^>]+href="([^"]+\.css)"', HTML)
        script_paths = re.findall(r'<script[^>]+src="([^"]+\.js)"', HTML)
        self.assertEqual(stylesheet_paths, [
            "css/base.css",
            "css/diagnostics.css",
            "css/entity-columns.css",
            "css/interface-refresh.css",
        ])
        self.assertEqual(len(script_paths), 27)
        self.assertEqual(script_paths[0], "js/core.js")
        self.assertEqual(script_paths[-1], "js/voice/proactive.js")
        self.assertTrue(all((STATIC / path).is_file() for path in stylesheet_paths + script_paths))
        self.assertLess(len(HTML.encode("utf-8")), 100_000)
        self.assertIn("function renderMarkdownText", FRONTEND)
        self.assertIn('id="zbrano-v01294-proactive-voice"', HTML)

    def test_backend_services_are_real_imported_modules(self):
        expected = {
            "entity_policy.py": ("def should_auto_approve_entity", "def classify_entity_risk"),
            "ha_client.py": ("class HomeAssistantWebSocketClient", "async def call_service"),
            "mcp_protocol.py": ("class MCPError", "def decode_workshop_tool_result"),
            "release_notes.py": ("def release_marker", "def reconcile_release_history_backfill"),
        }
        for filename, markers in expected.items():
            source = (APP / "services" / filename).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, source)
                self.assertNotIn(marker, MAIN_RAW)
                self.assertIn(marker, BACKEND)
        self.assertIn("from .services.entity_policy import", MAIN_RAW)
        self.assertIn("from .services.ha_client import", MAIN_RAW)
        self.assertIn("from .services.mcp_protocol import", MAIN_RAW)
        self.assertIn("from .services.release_notes import", MAIN_RAW)
        self.assertIn("app = FastAPI(", MAIN_RAW)

    def test_request_schemas_have_a_dedicated_module(self):
        schemas = (APP / "schemas.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^class \w+\(BaseModel\)", schemas, re.MULTILINE)), 33)
        self.assertIn("from .schemas import (", MAIN_RAW)
        self.assertNotIn("class ChatRequest(BaseModel)", MAIN_RAW)
        self.assertIn("class ChatRequest(BaseModel)", BACKEND)

    def test_build_and_asset_delivery_cover_modules(self):
        self.assertIn("python3 -m compileall -q ./app", DOCKER)
        self.assertIn('if path and candidate.is_file():', MAIN_RAW)
        asset_branch = MAIN_RAW[MAIN_RAW.index('if path and candidate.is_file():') : MAIN_RAW.index('return FileResponse(\n        STATIC_DIR / "index.html"')]
        self.assertIn('"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"', asset_branch)
        self.assertIn("JavaScript source", (ROOT / "jarvis/validate_inline_js.py").read_text(encoding="utf-8"))
        self.assertIn("source_path.read_text", (ROOT / "jarvis/validate_new_chat_wiring.py").read_text(encoding="utf-8"))

    def test_architecture_contract_is_documented(self):
        architecture = (ROOT / "docs/MODULE_ARCHITECTURE.md").read_text(encoding="utf-8")
        self.assertIn("uvicorn app.main:app", architecture)
        self.assertIn("classic scripts", architecture)
        self.assertIn("dependency injection rather than circular imports", architecture)


if __name__ == "__main__":
    unittest.main()
