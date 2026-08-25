import json
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from jarvis.app.services import developer_support, runtime_routing, wake_calibration


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
ROUTING = (APP / "services/runtime_routing.py").read_text(encoding="utf-8")
DEVELOPER = (APP / "services/developer_support.py").read_text(encoding="utf-8")
WAKE = (APP / "services/wake_calibration.py").read_text(encoding="utf-8")
ARCHITECTURE = (ROOT / "docs/MODULE_ARCHITECTURE.md").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class FinalModularizationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.developer_enabled = False
        runtime_routing.configure_runtime_routing(
            developer_mode_enabled_fn=lambda: self.developer_enabled,
            developer_system_instructions_fn=lambda base: base + "|developer",
            is_ha_history_fn=lambda message: message == "history",
            ha_history_instructions_fn=lambda base: base + "|history",
            is_automation_fn=lambda message: message == "automation",
            automation_instructions_fn=lambda base: base + "|automation",
            calendar_instructions_fn=lambda base: base + "|calendar-guidance",
            is_grinder_fn=lambda message: message == "grinder",
            grinder_instructions_fn=lambda base: base + "|grinder",
            is_ha_priority_fn=lambda message: message == "control",
            developer_tools_fn=lambda: [{"name": "developer"}],
            developer_mcp_tools_fn=lambda: [{"name": "developer-mcp"}],
            grinder_tools_fn=lambda: [{"name": "grinder"}],
            is_fast_memory_fn=lambda message: message == "memory",
            fast_memory_tools_fn=lambda: [{"name": "memory"}],
            automation_tools_fn=lambda: [{"name": "automation"}],
            is_calendar_fn=lambda message: message == "calendar",
            calendar_tools_fn=lambda: [{"name": "calendar"}],
            ha_history_tools_fn=lambda: [{"name": "history"}],
            ha_priority_tools_fn=lambda: [{"name": "control"}],
            default_tools_fn=lambda: [{"name": "default"}],
            native_web_search_tool_fn=lambda mode: {"name": f"search-{mode}"} if mode != "off" else None,
        )

    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.42"', CONFIG)
        self.assertIn('version="0.13.42"', MAIN)
        self.assertIn("HUD 0.13.42", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.42")

    def test_final_implementations_are_outside_the_composition_root(self):
        for definition in (
            "def priority_system_instructions(",
            "def runtime_chat_tools(",
            "def _developer_frontend_source(",
            "def _resolve_developer_feature(",
            "def _new_wake_shadow_model(",
            "def _wake_calibration_status(",
            "def _train_personal_wake_verifier(",
        ):
            self.assertNotIn(definition, MAIN)
        self.assertIn("def priority_system_instructions(", ROUTING)
        self.assertIn("def _developer_frontend_source(", DEVELOPER)
        self.assertIn("def _train_personal_wake_verifier(", WAKE)
        self.assertIn("configure_runtime_routing(", MAIN)

    def test_runtime_routing_preserves_priority_and_exact_tool_sets(self):
        self.assertEqual(runtime_routing.priority_system_instructions("base", "history"), "base|history")
        self.assertEqual(runtime_routing.priority_system_instructions("base", "automation"), "base|automation")
        self.assertEqual(runtime_routing.priority_system_instructions("base", "grinder"), "base|calendar-guidance|grinder")
        self.assertIn("HOME ASSISTANT DEVICE CONTROL INTENT IS ACTIVE", runtime_routing.priority_system_instructions("base", "control"))
        self.assertEqual(runtime_routing.runtime_chat_tools(message="grinder"), [{"name": "grinder"}])
        self.assertEqual(runtime_routing.runtime_chat_tools(message="memory"), [{"name": "memory"}])
        self.assertEqual(runtime_routing.runtime_chat_tools(message="automation"), [{"name": "automation"}])
        self.assertEqual(runtime_routing.runtime_chat_tools(message="calendar"), [{"name": "calendar"}])
        self.assertEqual(runtime_routing.runtime_chat_tools(message="history"), [{"name": "history"}])
        self.assertEqual(runtime_routing.runtime_chat_tools(message="control"), [{"name": "control"}])
        self.assertEqual(runtime_routing.runtime_chat_tools("auto", "other"), [{"name": "default"}, {"name": "search-auto"}])
        self.developer_enabled = True
        self.assertEqual(runtime_routing.runtime_chat_tools(message="control"), [{"name": "developer"}, {"name": "developer-mcp"}])

    def test_developer_support_resolves_aliases_and_reads_split_frontend(self):
        self.assertEqual(developer_support._resolve_developer_feature("", "upload attachment"), "attachments")
        source = developer_support._developer_frontend_source()
        self.assertIn("createNewChat", source)
        self.assertIn("startRecording", source)

    def test_wake_quality_contract_and_model_paths(self):
        self.assertEqual(wake_calibration.WAKE_SHADOW_MODEL_PATH.name, "hey_zbrano.onnx")
        self.assertEqual(wake_calibration.WAKE_CALIBRATION_DIR, Path("/data/wakeword_calibration"))
        with tempfile.TemporaryDirectory() as directory:
            clip_path = Path(directory) / "sample.wav"
            samples = [5000 if index % 2 else -5000 for index in range(1600)]
            with wave.open(str(clip_path), "wb") as clip:
                clip.setnchannels(1)
                clip.setsampwidth(2)
                clip.setframerate(16000)
                clip.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            quality = wake_calibration._wake_clip_quality(clip_path)
        self.assertTrue(quality["valid"])
        self.assertEqual(quality["duration_seconds"], 0.1)

    def test_architecture_marks_step_three_complete(self):
        self.assertIn("canonical modularization phase completed in v0.13.42", ARCHITECTURE)
        self.assertIn("chat streaming state machine and HTTP/voice route orchestration", ARCHITECTURE)


if __name__ == "__main__":
    unittest.main()
