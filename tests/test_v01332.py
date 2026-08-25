import ast
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN_PATH = APP / "main.py"
MAIN = MAIN_PATH.read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_frontend_source_function():
    tree = ast.parse(MAIN)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_developer_frontend_source"
    )
    namespace = {
        "Path": Path,
        "re": re,
        "DEVELOPER_FRONTEND_PATH": APP / "static/index.html",
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(MAIN_PATH), "exec"), namespace)
    return namespace["_developer_frontend_source"]


class ModularDiagnosticsRegressionTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.37"', CONFIG)
        self.assertIn('version="0.13.37"', MAIN)
        self.assertIn("HUD 0.13.37", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.37")

    def test_health_and_entity_routes_import_extracted_policy_constants(self):
        import_block = MAIN[MAIN.index("from .services.entity_policy import ("):]
        import_block = import_block[:import_block.index(")")]
        for name in ("HA_READ_ENTITIES", "HA_CONTROL_ENTITIES", "SAFE_CONTROL_DOMAINS"):
            self.assertIn(name, import_block)
        self.assertIn('"ha_read_entity_count": len((await approved_ha_entities())', MAIN)
        self.assertIn('sorted(set(read_entities) | HA_READ_ENTITIES)', MAIN)

    def test_diagnostics_read_all_referenced_frontend_controllers(self):
        source = load_frontend_source_function()()
        markers = (
            "createNewChat",
            'picker.addEventListener("change", uploadSelectedFiles, true)',
            'deleteButton.addEventListener("click", deleteSelected, true)',
            "plugin-settings-toggle",
            "loadEntities",
            "startRecording",
            "stopAudioPlayback",
        )
        for marker in markers:
            self.assertIn(marker, source)
        self.assertIn("frontend_text = _developer_frontend_source()", MAIN)


if __name__ == "__main__":
    unittest.main()
