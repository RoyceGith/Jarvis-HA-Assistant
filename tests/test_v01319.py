from pathlib import Path
import builtins
import json
import runpy
import symtable
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
RELEASE_NOTES_PATH = APP / "services/release_notes.py"
RELEASE_NOTES = RELEASE_NOTES_PATH.read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ReleaseNotesModuleBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.39"', CONFIG)
        self.assertIn('version="0.13.39"', MAIN)
        self.assertIn("HUD 0.13.39", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.39")

    def test_release_note_constants_live_with_their_consumers(self):
        for name in ("CURRENT_VERSION_LABELS", "CURRENT_RELEASE_BLOCK_START", "CURRENT_RELEASE_BLOCK_END"):
            self.assertIn(name, RELEASE_NOTES)
            self.assertNotIn(f"{name} =", MAIN)

    def test_release_note_service_executes_in_isolation(self):
        functions = runpy.run_path(str(RELEASE_NOTES_PATH))
        reconciled = functions["reconcile_explicit_current_versions"](
            "# Project\n\n- **Current version:** 0.13.18\n",
            "0.13.39",
        )
        self.assertIn("**Current version:** 0.13.39", reconciled)
        block = functions["render_current_release_truth"](MANIFEST, release_log=False)
        self.assertIn("<!-- zbrano-current-release:start -->", block)
        self.assertIn("Source and runtime version:** 0.13.39", block)

    def test_all_extracted_backend_modules_declare_their_globals(self):
        builtin_names = set(dir(builtins))
        module_paths = [APP / "schemas.py"]
        module_paths.extend(sorted((APP / "services").glob("*.py")))
        module_paths.extend(sorted((APP / "domains").glob("*.py")))
        for path in module_paths:
            if path.name == "__init__.py":
                continue
            source = path.read_text(encoding="utf-8")
            table = symtable.symtable(source, str(path), "exec")
            module_names = set(table.get_identifiers())
            unresolved = set()

            def inspect_scope(scope):
                for child in scope.get_children():
                    for identifier in child.get_identifiers():
                        symbol = child.lookup(identifier)
                        if symbol.is_referenced() and symbol.is_global() and identifier not in module_names and identifier not in builtin_names:
                            unresolved.add(identifier)
                    inspect_scope(child)

            inspect_scope(table)
            self.assertEqual(unresolved, set(), str(path.relative_to(ROOT)))


if __name__ == "__main__":
    unittest.main()
