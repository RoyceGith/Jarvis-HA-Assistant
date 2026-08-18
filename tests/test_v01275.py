from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis" / "apply_navigation_icons_v01275.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis" / "Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis" / "config.yaml").read_text(encoding="utf-8")
MANIFEST = (ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8")


def test_primary_navigation_order():
    expected = '<button id="files-tab">Shared Files</button>\n    <button id="automations-tab">Automations</button>\n    <button id="entities-tab">Entities</button>\n    <button id="plugins-tab">Plugins</button>'
    assert expected in PATCH


def test_calendar_and_settings_are_accessible_icon_tabs():
    assert 'id="calendar-tab" class="primary-icon-tab" aria-label="Calendar" title="Calendar"' in PATCH
    assert 'id="settings-tab" class="primary-icon-tab" aria-label="Settings" title="Settings"' in PATCH
    assert "nav .primary-icon-tab svg" in PATCH


def test_v01275_release_alignment():
    assert 'version: "0.12.73"' in CONFIG
    assert '"version": "0.12.73"' in MANIFEST
    assert "COPY apply_navigation_icons_v01275.py" in DOCKER
    assert "python3 ./apply_navigation_icons_v01275.py" in DOCKER
    assert DOCKER.index("apply_visual_calendar_v01274.py") < DOCKER.index("apply_navigation_icons_v01275.py")
