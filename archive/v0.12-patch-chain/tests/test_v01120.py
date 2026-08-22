from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_github_chat_shared_fix_v01120.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_v01120_github_new_chat_and_shared_files_fix():
    assert 'application/json, text/event-stream' in PATCH
    assert 'GITHUB_MCP_URL="https://api.githubcopilot.com/mcp/"' in PATCH
    assert '_mcp_response_json' in PATCH
    assert '_plugin_url_key' in PATCH
    assert 'body: JSON.stringify({session_id: sessionId})' in PATCH
    assert 'Add to Shared Files' in PATCH
    assert 'Uploaded to Shared Files' in PATCH
    assert 'Destination: Shared Files' in PATCH
    assert 'apply_github_chat_shared_fix_v01120.py' in DOCKER
    assert 'validate_inline_js.py ./app/static/index.html' in DOCKER
