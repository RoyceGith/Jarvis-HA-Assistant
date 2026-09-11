import ast
import json
from pathlib import Path
import tempfile
import unittest
from typing import Any

from zbrano.app.services import entity_policy


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "zbrano/app/services/entity_policy.py"


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
    def test_discovered_ordinary_controls_default_on_without_overriding_choices(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            originals = (
                entity_policy.DATA_DIR,
                entity_policy.ENTITY_POLICY_PATH,
                entity_policy.V063_ENTITY_POLICY_PATH,
                entity_policy.V063_MIGRATION_MARKER,
            )
            entity_policy.DATA_DIR = root
            entity_policy.ENTITY_POLICY_PATH = root / "entity_policy.json"
            entity_policy.V063_ENTITY_POLICY_PATH = root / "missing-legacy.json"
            entity_policy.V063_MIGRATION_MARKER = root / ".legacy-migrated"
            try:
                entity_policy.save_entity_policy({
                    "light.keep_blocked": {
                        "enabled": False,
                        "access": "restricted",
                        "friendly_name": "Keep blocked",
                    }
                })
                added = entity_policy.apply_discovered_control_defaults([
                    {"entity_id": "light.kitchen", "attributes": {"friendly_name": "Kitchen light"}},
                    {"entity_id": "switch.coffee", "attributes": {"friendly_name": "Coffee switch"}},
                    {"entity_id": "climate.living_room", "attributes": {"friendly_name": "Living room AC"}},
                    {"entity_id": "fan.bedroom_ac", "attributes": {"friendly_name": "Bedroom air conditioner"}},
                    {"entity_id": "fan.ceiling", "attributes": {"friendly_name": "Ceiling fan"}},
                    {"entity_id": "binary_sensor.ac_status", "attributes": {"friendly_name": "AC status"}},
                    {"entity_id": "light.keep_blocked", "attributes": {"friendly_name": "Keep blocked"}},
                ])
                self.assertEqual(added, {
                    "light.kitchen", "switch.coffee", "climate.living_room", "fan.bedroom_ac",
                })
                saved = entity_policy.load_entity_policy()
                for entity_id in added:
                    self.assertTrue(saved[entity_id]["enabled"])
                    self.assertEqual(saved[entity_id]["access"], "low_risk_control_proposed")
                    self.assertEqual(saved[entity_id]["source"], "default_control")
                self.assertNotIn("fan.ceiling", saved)
                self.assertNotIn("binary_sensor.ac_status", saved)
                self.assertFalse(saved["light.keep_blocked"]["enabled"])
                self.assertEqual(saved["light.keep_blocked"]["access"], "restricted")
            finally:
                (
                    entity_policy.DATA_DIR,
                    entity_policy.ENTITY_POLICY_PATH,
                    entity_policy.V063_ENTITY_POLICY_PATH,
                    entity_policy.V063_MIGRATION_MARKER,
                ) = originals

    def test_disabled_entity_alias_round_trip_uses_data_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_dir = root / "data"
            load_policy, save_policy = load_policy_functions(
                data_dir, root / "share/zbrano/entity_policy.json"
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
            v063_path = root / "share/zbrano/entity_policy.json"
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
            v063_path = root / "share/zbrano/entity_policy.json"
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
