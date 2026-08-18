import ast
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PATCH_PATH = ROOT / "jarvis/apply_ha_history_timeline_v01276.py"
PATCH = PATCH_PATH.read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def _history_namespace() -> dict[str, Any]:
    tree = ast.parse(PATCH)
    value = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "history_backend" for target in node.targets):
            value = ast.literal_eval(node.value)
            break
    assert value
    namespace: dict[str, Any] = {
        "Any": Any, "re": re,
        "ensure_read_allowed": lambda entity_id: None,
        "SUPERVISOR_TOKEN": "test", "HA_API_BASE": "http://example.invalid/api",
    }
    exec(value, namespace)
    return namespace


def test_history_limits_policy_and_deduplication():
    history = _history_namespace()
    assert history["_ha_history_entities"](["sensor.a", "SENSOR.A", "binary_sensor.door"]) == ["sensor.a", "binary_sensor.door"]
    try:
        history["_ha_history_entities"]([f"sensor.item_{index}" for index in range(9)])
    except ValueError as exc:
        assert "limited to 8" in str(exc)
    else:
        raise AssertionError("Expected the entity limit to be enforced")


def test_history_summary_and_downsampling_are_deterministic():
    history = _history_namespace()
    points = [
        {"state": str(value), "last_changed": f"2026-08-18T10:{index:02d}:00+00:00"}
        for index, value in enumerate([20, 20.1, 20.2, 20.3, 35])
    ]
    summary = history["_ha_history_summary"](
        "sensor.workshop_temperature", points,
        {"friendly_name": "Workshop temperature", "attributes": {"unit_of_measurement": "°C"}},
    )
    assert summary["numeric"] is True
    assert summary["trend"] == "rising"
    assert summary["maximum"] == 35
    assert summary["possible_anomaly_count"] == 1
    sampled = history["_ha_history_downsample"](points, 3)
    assert len(sampled) == 3
    assert sampled[0] == points[0] and sampled[-1] == points[-1]


def test_history_tools_interface_diagnostics_and_routing_are_wired():
    for marker in (
        '"name": "get_home_assistant_history"', '"name": "correlate_home_assistant_timeline"',
        '"name": "search_home_assistant_logbook"', '@app.get("/api/ha/timeline")',
        "is_home_assistant_history_intent", "Home Assistant History API",
        'data-entity-view="history"', 'id="ha-timeline-events"', 'id="zbrano-v01276-ha-history"',
    ):
        assert marker in PATCH


def test_v01276_release_alignment():
    assert 'version: "0.12.76"' in CONFIG
    assert MANIFEST["version"] == "0.12.76"
    assert "COPY apply_ha_history_timeline_v01276.py" in DOCKER
    assert "python3 ./apply_ha_history_timeline_v01276.py" in DOCKER
    assert DOCKER.index("apply_compact_header_v01275.py") < DOCKER.index("apply_ha_history_timeline_v01276.py")
