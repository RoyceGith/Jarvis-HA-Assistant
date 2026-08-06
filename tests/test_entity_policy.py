import ast
import json
from pathlib import Path
import tempfile
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "jarvis/app/main.py"


def load_policy_functions(data_dir: Path, v063_path: Path):
    source = MAIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"load_entity_policy", "save_entity_policy"}
    ]
    module = ast.Module(body=selected, type_ignores=[])
    namespace = {
        "Any": Any,
        "DATA_DIR": data_dir,
        "ENTITY_POLICY_PATH": data_dir / "entity_policy.json",
        "V063_ENTITY_POLICY_PATH": v063_path,
        "V063_MIGRATION_MARKER": data_dir / ".entity_policy_v063_migrated",
        "Path": Path,
        "json": json,
    }
    exec(compile(module, str(MAIN_PATH), "exec"), namespace)
    return namespace["load_entity_policy"], namespace["save_entity_policy"]


class EntityPolicyPersistenceTests(unittest.TestCase):
    def test_disabled_entity_alias_round_trip_uses_data_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_dir = root / "data"
            load_policy, save_policy = load_policy_functions(
                data_dir, root / "share/jarvis/entity_policy.json"
            )
            expected = {
                "sensor.workshop_temperature": {
                    "enabled": False,
                    "aliases": ["bench temperature"],
                }
            }

            save_policy(expected)

            self.assertEqual(load_policy(), expected)
            self.assertTrue((data_dir / "entity_policy.json").is_file())

    def test_v063_share_policy_is_migrated_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_dir = root / "data"
            v063_path = root / "share/jarvis/entity_policy.json"
            v063_path.parent.mkdir(parents=True)
            v063_path.write_text(
                json.dumps({
                    "version": 1,
                    "entities": {
                        "switch.workshop_socket": {
                            "enabled": True,
                            "aliases": ["workshop bench"],
                        }
                    },
                }),
                encoding="utf-8",
            )
            load_policy, _ = load_policy_functions(data_dir, v063_path)

            self.assertEqual(
                load_policy()["switch.workshop_socket"]["aliases"],
                ["workshop bench"],
            )
            self.assertTrue((data_dir / "entity_policy.json").is_file())

    def test_v063_policy_overrides_stale_data_during_migration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_dir = root / "data"
            data_dir.mkdir(parents=True)
            data_path = data_dir / "entity_policy.json"
            data_path.write_text(
                json.dumps({
                    "version": 1,
                    "entities": {
                        "switch.workshop_socket": {"aliases": ["old alias"]},
                        "sensor.unrelated": {"aliases": ["keep me"]},
                    },
                }),
                encoding="utf-8",
            )
            v063_path = root / "share/jarvis/entity_policy.json"
            v063_path.parent.mkdir(parents=True)
            v063_path.write_text(
                json.dumps({
                    "version": 1,
                    "entities": {
                        "switch.workshop_socket": {"aliases": ["new alias"]},
                    },
                }),
                encoding="utf-8",
            )
            load_policy, _ = load_policy_functions(data_dir, v063_path)

            migrated = load_policy()
            self.assertEqual(
                migrated["switch.workshop_socket"]["aliases"], ["new alias"]
            )
            self.assertEqual(migrated["sensor.unrelated"]["aliases"], ["keep me"])
            self.assertTrue((data_dir / ".entity_policy_v063_migrated").is_file())


if __name__ == "__main__":
    unittest.main()
